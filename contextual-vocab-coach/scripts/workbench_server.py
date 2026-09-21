#!/usr/bin/env python3
"""Serve the local Contextual Vocab Coach workbench and JSON API.

The server binds to loopback only. It reuses vocab_store.py so decisions made
in the visual workbench and decisions made through the CLI share one source of
truth.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import vocab_store as store


SKILL_DIR = Path(__file__).resolve().parents[1]
CLIENT_DIR = SKILL_DIR / "workbench" / "dist" / "client"
SAMPLE_PACK = SKILL_DIR / "examples" / "sample-pack.json"
MODE_LABELS = {
    "production": "主动表达",
    "recognition": "理解优先",
    "listening": "听力辨认",
}
STATE_LOCK = threading.RLock()
MAX_BODY_BYTES = 64 * 1024


def initialize_store(path: Path, *, demo: bool = False) -> None:
    """Create the store when absent and optionally seed the bundled demo."""
    with STATE_LOCK:
        changed = False
        if path.exists():
            state = store.load_state(path)
        else:
            now = store.iso_now()
            state = store.empty_state(now)
            store.add_event(state, now, "store_initialized")
            changed = True
        now = store.iso_now()
        if store.ensure_starter_lexicon(state, now) is not None:
            changed = True
        if demo and not state["candidates"]:
            pack = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))
            store.apply_pack(state, pack, now)
            changed = True
        if changed:
            store.save_state(path, state)


def workbench_state(path: Path) -> dict[str, Any]:
    """Translate the durable store schema into the compact UI view model."""
    with STATE_LOCK:
        state = store.load_state(path)
        status = store.status_payload(state, store.iso_now())

    goal = status.get("active_goal")
    sources = sorted(state["sources"].values(), key=lambda item: item["label"].casefold())
    # Python's sort is stable, so equal-priority items keep the order in which
    # the coach proposed them instead of jumping around alphabetically.
    candidates = sorted(state["candidates"].values(), key=lambda item: -item["priority"])

    source_labels = {source["id"]: source["label"] for source in sources}
    candidate_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        primary_mode = candidate["target_modes"][0]
        primary_source = candidate["source_ids"][0] if candidate["source_ids"] else None
        candidate_rows.append(
            {
                "id": candidate["id"],
                "term": candidate["term"],
                "meaning": candidate["meaning"],
                "rationale": candidate["rationale"],
                "sourceLabel": source_labels.get(primary_source, "已删除的来源"),
                "sourceTime": "最近导入",
                "mode": primary_mode,
                "modeLabel": MODE_LABELS.get(primary_mode, primary_mode),
                "status": candidate["status"],
                "anchor": candidate.get("suggested_anchor", ""),
            }
        )

    contextual_sources = [source for source in sources if source.get("kind") != "bundled_lexicon"]
    active_source_summaries = [source.get("summary", "") for source in contextual_sources if source["status"] == "active"]
    summary = next((value for value in active_source_summaries if value), "尚未导入授权上下文。")
    focus_points = [
        point
        for source in contextual_sources
        if source["status"] == "active"
        for point in source.get("focus_points", [])
    ][:3]
    if not focus_points:
        focus_points = [candidate["rationale"] for candidate in candidates[:3]]
    if not focus_points:
        focus_points = ["先在 Codex 中确认学习目标并导入一份授权上下文"]

    return {
        "connected": True,
        "goal": {
            "statement": goal["statement"] if goal else "尚未设置学习目标",
            "successDefinition": goal["success_definition"] if goal else "先和 Codex 说明你近期需要完成的真实任务",
        },
        "summary": summary,
        "focusPoints": focus_points,
        "dueCount": status["due_count"],
        "library": store.lexicon_payload(state, limit=1000),
        "candidates": candidate_rows,
        "sources": [
            {
                "id": source["id"],
                "label": source["label"],
                "kind": source["kind"],
                "status": source["status"],
                "summary": source.get("summary", ""),
                "isBundled": source.get("kind") == "bundled_lexicon",
            }
            for source in sources
        ],
    }


def apply_decision(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    item_id = str(payload.get("item_id", ""))
    decision = str(payload.get("decision", ""))
    if decision not in store.VALID_DECISIONS - {"proposed"}:
        raise store.StoreError("decision must be known, not_now, test, or learning")
    with STATE_LOCK:
        store.command_decide(argparse.Namespace(item=item_id, decision=decision), path, store.iso_now())
    return workbench_state(path)


def apply_review(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    item_id = str(payload.get("item_id", ""))
    mode = str(payload.get("mode", ""))
    feedback = str(payload.get("feedback", ""))
    if mode not in store.VALID_MODES:
        raise store.StoreError(f"unsupported review mode: {mode}")
    if feedback not in store.VALID_FEEDBACK:
        raise store.StoreError(f"unsupported review feedback: {feedback}")
    args = argparse.Namespace(
        item=item_id,
        mode=mode,
        feedback=feedback,
        response_ms=None,
        strategy=str(payload.get("strategy", "workbench-active-recall")),
        personalized=bool(payload.get("personalized", True)),
        transfer_test=False,
        context_note="",
    )
    with STATE_LOCK:
        store.command_review(args, path, store.iso_now())
    return workbench_state(path)


def apply_source_status(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    source_id = str(payload.get("source_id", ""))
    status = str(payload.get("status", ""))
    if status not in store.VALID_SOURCE_STATUS:
        raise store.StoreError("status must be active or paused")
    with STATE_LOCK:
        store.command_source_status(
            argparse.Namespace(source_id=source_id, status=status), path, store.iso_now()
        )
    return workbench_state(path)


def apply_library_decision(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    entry_id = str(payload.get("entry_id", ""))
    decision = str(payload.get("decision", "learning"))
    with STATE_LOCK:
        state = store.load_state(path)
        store.add_lexicon_entry(state, entry_id, decision, store.iso_now())
        errors = store.state_errors(state)
        if errors:
            raise store.StoreError("Library decision produced an invalid state: " + "; ".join(errors))
        store.save_state(path, state)
    return workbench_state(path)


def make_handler(
    state_path: Path,
    client_dir: Path = CLIENT_DIR,
    qa_output: Path | None = None,
) -> type[SimpleHTTPRequestHandler]:
    class WorkbenchHandler(SimpleHTTPRequestHandler):
        server_version = "ContextualVocabWorkbench/1.0"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(client_dir), **kwargs)

        def end_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'")
            super().end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/state":
                self._send_json(workbench_state(state_path))
                return
            if path.startswith("/api/"):
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            if path == "/" or (not (client_dir / path.lstrip("/")).is_file() and "." not in Path(path).name):
                self.path = "/index.html"
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path == "/api/qa-screenshot" and qa_output is not None:
                self._save_qa_screenshot(qa_output)
                return
            routes = {
                "/api/decision": apply_decision,
                "/api/review": apply_review,
                "/api/source-status": apply_source_status,
                "/api/library-decision": apply_library_decision,
            }
            action = routes.get(urlparse(self.path).path)
            if action is None:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                self._send_json(action(state_path, payload))
            except (store.StoreError, ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def _save_qa_screenshot(self, output: Path) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json({"error": "invalid Content-Length"}, HTTPStatus.BAD_REQUEST)
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            if content_type not in {"image/png", "image/jpeg"} or not 1 <= length <= 20 * 1024 * 1024:
                self._send_json({"error": "expected a PNG or JPEG up to 20 MiB"}, HTTPStatus.BAD_REQUEST)
                return
            body = self.rfile.read(length)
            valid = body.startswith(b"\x89PNG\r\n\x1a\n") or body.startswith(b"\xff\xd8\xff")
            if not valid:
                self._send_json({"error": "invalid image body"}, HTTPStatus.BAD_REQUEST)
                return
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(body)
            self._send_json({"saved": str(output), "bytes": len(body)})

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("request body must be between 1 byte and 64 KiB")
            if "application/json" not in self.headers.get("Content-Type", ""):
                raise ValueError("Content-Type must be application/json")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[workbench] {self.address_string()} {format % args}")

    return WorkbenchHandler


def create_server(
    state_path: Path,
    port: int,
    client_dir: Path = CLIENT_DIR,
    qa_output: Path | None = None,
) -> ThreadingHTTPServer:
    if not (client_dir / "index.html").is_file():
        raise store.StoreError(
            f"Workbench build not found at {client_dir}. Run `npm ci && npm run build` in workbench/."
        )
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(state_path, client_dir, qa_output))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Contextual Vocab Coach workbench")
    parser.add_argument("--store", help="State file or directory (defaults to the normal local store)")
    parser.add_argument("--port", type=int, default=4174, help="Loopback port (default: 4174)")
    parser.add_argument("--demo", action="store_true", help="Use bundled sample content without touching the normal store")
    parser.add_argument("--qa-output", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    demo_temp: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.demo and not args.store:
            demo_temp = tempfile.TemporaryDirectory(prefix="contextual-vocab-workbench-")
            state_path = Path(demo_temp.name) / "state.json"
        else:
            state_path = store.resolve_store_path(args.store)
        initialize_store(state_path, demo=args.demo)
        server = create_server(state_path, args.port, qa_output=args.qa_output)
        print(f"Contextual Vocab Coach workbench: http://127.0.0.1:{args.port}/")
        print(f"Learning store: {state_path}")
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (OSError, store.StoreError) as exc:
        print(f"Cannot start workbench: {exc}")
        return 2
    finally:
        if demo_temp is not None:
            demo_temp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
