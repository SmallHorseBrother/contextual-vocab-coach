#!/usr/bin/env python3
"""Serve the local Contextual Vocab Coach workbench and JSON API.

The server binds to loopback only. It reuses vocab_store.py so decisions made
in the visual workbench and decisions made through the CLI share one source of
truth.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import vocab_store as store
import codex_context
import knowledge_graph


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


def personal_vocabulary_payload(
    state: dict[str, Any],
    context_index: dict[str, Any],
    library: dict[str, Any],
) -> dict[str, Any]:
    """Merge the broad starter reservoir and scanned contextual expressions."""
    topic_labels = {topic["id"]: topic["label"] for topic in codex_context.TOPICS}
    matches = {row["entryId"]: row for row in context_index.get("lexiconMatches", [])}
    source_labels = {row["id"]: row["label"] for row in state["sources"].values()}
    entries: dict[tuple[str, str], dict[str, Any]] = {}

    for row in library.get("entries", []):
        match = matches.get(row["id"], {})
        context_ids = list(match.get("topicIds", []))
        key = (store.normalize(row["term"]), store.normalize(row["meaning"]))
        entries[key] = {
            "id": row["id"],
            "lexiconEntryId": row["id"],
            "candidateId": row.get("candidate_id"),
            "term": row["term"],
            "meaning": row["meaning"],
            "kind": row["kind"],
            "level": row["level"],
            "scenarioIds": list(row.get("scenario_ids", [])),
            "scenarioLabels": list(row.get("scenario_labels", [])),
            "contextIds": context_ids,
            "primaryContextId": context_ids[0] if context_ids else None,
            "contextLabels": [topic_labels[item] for item in context_ids if item in topic_labels],
            "taskCount": int(match.get("taskCount", 0)),
            "recentTitles": list(match.get("recentTitles", [])),
            "lastSeenAt": match.get("lastSeenAt", ""),
            "sourceType": "observed" if match else "foundation",
            "sourceLabel": "Codex 历史中出现" if match else "基础生活英语",
            "rationale": (
                f"在 {match.get('taskCount', 0)} 个 Codex 任务中出现"
                if match else "基础工作与生活表达，已纳入个人词表"
            ),
            "status": row["status"],
            "targetModes": list(row.get("target_modes", [])),
        }

    for candidate in state["candidates"].values():
        source_ids = candidate.get("source_ids", [])
        context_ids = list(dict.fromkeys(
            [candidate.get("topic_id")] if candidate.get("topic_id") else []
        ))
        key = (store.normalize(candidate["term"]), store.normalize(candidate["meaning"]))
        existing = entries.get(key)
        contextual = {
            "id": candidate["id"],
            "lexiconEntryId": candidate.get("lexicon_entry_id"),
            "candidateId": candidate["id"],
            "term": candidate["term"],
            "meaning": candidate["meaning"],
            "kind": candidate["kind"],
            "level": existing.get("level", "") if existing else "",
            "scenarioIds": existing.get("scenarioIds", []) if existing else [],
            "scenarioLabels": existing.get("scenarioLabels", []) if existing else [],
            "contextIds": list(dict.fromkeys([*(existing.get("contextIds", []) if existing else []), *context_ids])),
            "primaryContextId": candidate.get("topic_id"),
            "taskCount": existing.get("taskCount", 0) if existing else 0,
            "recentTitles": existing.get("recentTitles", []) if existing else [],
            "lastSeenAt": existing.get("lastSeenAt", "") if existing else "",
            "sourceType": "contextual",
            "sourceLabel": source_labels.get(source_ids[0], "Codex 历史") if source_ids else "Codex 历史",
            "rationale": candidate["rationale"],
            "status": candidate["status"],
            "targetModes": list(candidate.get("target_modes", [])),
        }
        contextual["contextLabels"] = [
            topic_labels[item] for item in contextual["contextIds"] if item in topic_labels
        ]
        entries[key] = contextual

    status_order = {"learning": 0, "test": 1, "proposed": 2, "available": 3, "known": 4, "not_now": 5}
    source_order = {"contextual": 0, "observed": 1, "foundation": 2}
    rows = sorted(
        entries.values(),
        key=lambda row: (
            status_order.get(row["status"], 9),
            source_order.get(row["sourceType"], 9),
            -row["taskCount"],
            row["term"].casefold(),
        ),
    )
    return {
        "title": "我的英语词表",
        "description": "首次扫描形成静态快照；更新时优先处理最新任务并扩充词表。",
        "entryCount": len(rows),
        "uniqueTermCount": len({store.normalize(row["term"]) for row in rows}),
        "contextualCount": sum(1 for row in rows if row["sourceType"] == "contextual"),
        "observedCount": sum(1 for row in rows if row["sourceType"] == "observed"),
        "foundationCount": sum(1 for row in rows if row["sourceType"] == "foundation"),
        "contexts": [
            {"id": row["id"], "label": row["label"], "wordCount": row.get("wordCount", row.get("candidateCount", 0))}
            for row in context_index.get("topics", [])
        ],
        "levels": library.get("levels", []),
        "entries": rows,
        "updatedAt": context_index.get("indexedAt"),
        "coverage": context_index.get("coverage", {}),
    }


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
    context_index = state.get("context_index", {})
    active_topic_id = context_index.get("activeTopicId")

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
                "topicId": candidate.get("topic_id"),
            }
        )

    candidate_by_id = {candidate["id"]: candidate for candidate in candidates}
    review_queue: list[dict[str, Any]] = []
    for due in status["due"]:
        candidate = candidate_by_id.get(due["item_id"], {})
        review_queue.append(
            {
                "id": f"{due['item_id']}:{due['mode']}",
                "itemId": due["item_id"],
                "term": due["term"],
                "meaning": due["meaning"],
                "mode": due["mode"],
                "modeLabel": MODE_LABELS.get(due["mode"], due["mode"]),
                "anchor": candidate.get("suggested_anchor", ""),
                "dueAt": due["due_at"],
                "status": "due",
            }
        )

    contextual_sources = [source for source in sources if source.get("kind") != "bundled_lexicon"]
    active_topic = next(
        (topic for topic in context_index.get("topics", []) if topic.get("id") == active_topic_id),
        None,
    )
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
        focus_points = ["扫描或选择一个上下文，让候选表达贴近日常任务"]
    if active_topic:
        summary = active_topic.get("summary", summary)
        focus_points = active_topic.get("recentTitles", focus_points)[:3]

    library = store.lexicon_payload(state, limit=2000)
    personal_vocabulary = personal_vocabulary_payload(state, context_index, library)
    with STATE_LOCK:
        graph_state = store.load_state(path)
        if knowledge_graph.sync_graph(graph_state, personal_vocabulary["entries"], context_index, store.iso_now()):
            store.save_state(path, graph_state)
    graph_payload = knowledge_graph.payload(graph_state, personal_vocabulary["entries"])

    return {
        "connected": True,
        "goal": {
            "statement": goal["statement"] if goal else codex_context.LEARNING_DIRECTION,
            "successDefinition": goal["success_definition"] if goal else codex_context.LEARNING_SUCCESS,
        },
        "summary": summary,
        "focusPoints": focus_points,
        "contextIndex": context_index,
        "dueCount": status["due_count"],
        "reviewQueue": review_queue,
        "library": library,
        "personalVocabulary": personal_vocabulary,
        "knowledgeGraph": graph_payload,
        "candidates": candidate_rows,
        "sources": [
            {
                "id": source["id"],
                "label": source["label"],
                "kind": source["kind"],
                "status": source["status"],
                "summary": source.get("summary", ""),
                "isBundled": source.get("kind") == "bundled_lexicon",
                "topicId": source.get("topic_id"),
                "taskCount": source.get("task_count"),
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
    response_ms = payload.get("response_ms")
    if response_ms is not None:
        if not isinstance(response_ms, int) or isinstance(response_ms, bool) or response_ms < 0:
            raise store.StoreError("response_ms must be a non-negative integer or null")
    args = argparse.Namespace(
        item=item_id,
        mode=mode,
        feedback=feedback,
        response_ms=response_ms,
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


def apply_context_topic(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    topic_id = str(payload.get("topic_id", ""))
    with STATE_LOCK:
        codex_context.select_topic(path, topic_id)
    return workbench_state(path)


def apply_graph_relation(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    with STATE_LOCK:
        state = store.load_state(path)
        knowledge_graph.change_relation(
            state,
            str(payload.get("edge_id", "")),
            str(payload.get("action", "")),
            payload.get("type"),
            store.iso_now(),
        )
        store.save_state(path, state)
    return workbench_state(path)


def apply_graph_seen(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    node_ids = payload.get("node_ids")
    if node_ids is not None and (not isinstance(node_ids, list) or not all(isinstance(ident, str) for ident in node_ids)):
        raise store.StoreError("node_ids 必须是字符串列表")
    with STATE_LOCK:
        state = store.load_state(path)
        knowledge_graph.mark_seen(state, node_ids, store.iso_now())
        store.save_state(path, state)
    return workbench_state(path)


def apply_graph_add(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    term = str(payload.get("term", "")).strip()
    meaning = str(payload.get("meaning", "")).strip()
    requested_topic = str(payload.get("topic_id", "")).strip()
    if not (2 <= len(term) <= 80 and re.search(r"[A-Za-z]", term)):
        raise store.StoreError("英文表达需要包含字母，长度为 2–80 个字符")
    if not 1 <= len(meaning) <= 80:
        raise store.StoreError("中文含义长度为 1–80 个字符")
    with STATE_LOCK:
        state = store.load_state(path)
        valid_topics = set(codex_context.TOPIC_BY_ID)
        if requested_topic and requested_topic not in valid_topics:
            raise store.StoreError("未知的任务领域")
        topic_id = requested_topic or codex_context.classify(f"{term} {meaning}")[0]
        if topic_id not in valid_topics:
            topic_id = "general" if "general" in valid_topics else None
        item_id = store.stable_id("item", term, meaning)
        if item_id not in state["candidates"]:
            now = store.iso_now()
            source_id = "learner-added-expressions"
            state["sources"].setdefault(source_id, {
                "id": source_id, "label": "我添加的表达", "kind": "learner_entry",
                "locator": "local workbench", "authorized": True, "retain_raw": False,
                "summary": "由学习者在本机工作台主动添加的英语表达。", "status": "active",
                "added_at": now, "updated_at": now,
            })
            goal_id = state["profile"].get("active_goal_id")
            state["candidates"][item_id] = {
                "id": item_id, "term": term, "meaning": meaning,
                "kind": "word" if len(term.split()) == 1 else "phrase",
                "rationale": "你在工作台主动添加了这个表达，可在图谱中查看系统找到的联系。",
                "target_modes": ["production", "recognition"], "source_ids": [source_id],
                "goal_ids": [goal_id] if goal_id else [], "priority": 4,
                "evidence_summary": "learner-added expression", "suggested_anchor": "在你熟悉的任务中自然使用这个表达。",
                "contrast": "", "status": "proposed", "topic_id": topic_id,
                "created_at": now, "updated_at": now,
            }
            state["updated_at"] = now
            store.add_event(state, now, "graph_expression_added", item_id=item_id)
            errors = store.state_errors(state)
            if errors:
                raise store.StoreError("New expression produced an invalid state: " + "; ".join(errors))
            store.save_state(path, state)
    return workbench_state(path)


def make_handler(
    state_path: Path,
    client_dir: Path = CLIENT_DIR,
    qa_output: Path | None = None,
    codex_home: Path | None = None,
    context_depth: int = -1,
    demo_mode: bool = False,
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
                self._send_json(self._decorate(workbench_state(state_path)))
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
                "/api/context-topic": apply_context_topic,
                "/api/graph/relation": apply_graph_relation,
                "/api/graph/seen": apply_graph_seen,
                "/api/graph/add": apply_graph_add,
            }
            request_path = urlparse(self.path).path
            if request_path == "/api/context-scan":
                try:
                    self._read_json()
                    if demo_mode:
                        raise store.StoreError("演示模式不会读取真实 Codex 历史；请启动真实工作台后扫描。")
                    with STATE_LOCK:
                        codex_context.scan_into_store(
                            state_path,
                            codex_home=codex_home,
                            deep_limit=context_depth,
                        )
                    self._send_json(self._decorate(workbench_state(state_path)))
                except (OSError, store.StoreError, ValueError, json.JSONDecodeError) as exc:
                    self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            action = routes.get(request_path)
            if action is None:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                self._send_json(self._decorate(action(state_path, payload)))
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

        def _decorate(self, payload: dict[str, Any]) -> dict[str, Any]:
            return {
                **payload,
                "runtime": {
                    "mode": "demo" if demo_mode else "live",
                    "contextScanEnabled": not demo_mode,
                },
            }

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[workbench] {self.address_string()} {format % args}")

    return WorkbenchHandler


def create_server(
    state_path: Path,
    port: int,
    client_dir: Path = CLIENT_DIR,
    qa_output: Path | None = None,
    codex_home: Path | None = None,
    context_depth: int = -1,
    demo_mode: bool = False,
) -> ThreadingHTTPServer:
    if not (client_dir / "index.html").is_file():
        raise store.StoreError(
            f"Workbench build not found at {client_dir}. Run `npm ci && npm run build` in workbench/."
        )
    return ThreadingHTTPServer(
        ("127.0.0.1", port),
        make_handler(
            state_path,
            client_dir,
            qa_output,
            codex_home=codex_home,
            context_depth=context_depth,
            demo_mode=demo_mode,
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Contextual Vocab Coach workbench")
    parser.add_argument("--store", help="State file or directory (defaults to the normal local store)")
    parser.add_argument("--port", type=int, default=4174, help="Loopback port (default: 4174)")
    parser.add_argument("--demo", action="store_true", help="Use bundled sample content without touching the normal store")
    parser.add_argument("--no-context-scan", action="store_true", help="Skip the automatic local Codex history scan")
    parser.add_argument("--codex-home", type=Path, help="Codex data directory (defaults to CODEX_HOME or ~/.codex)")
    parser.add_argument("--context-depth", type=int, default=-1, help="Tasks to inspect beyond title metadata; -1 scans all")
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
        if not args.demo and not args.no_context_scan:
            context_index = codex_context.scan_into_store(
                state_path,
                codex_home=args.codex_home,
                deep_limit=args.context_depth,
            )
            coverage = context_index["coverage"]
            print(
                "Codex context: "
                f"{coverage['discoveredTaskCount']} tasks indexed, "
                f"{coverage['deepAnalyzedTaskCount']} fully scanned"
            )
        server = create_server(
            state_path,
            args.port,
            qa_output=args.qa_output,
            codex_home=args.codex_home,
            context_depth=args.context_depth,
            demo_mode=args.demo,
        )
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
