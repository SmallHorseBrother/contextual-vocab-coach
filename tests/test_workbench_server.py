from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "contextual-vocab-coach" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("workbench_server", SCRIPTS / "workbench_server.py")
assert SPEC and SPEC.loader
server_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server_module)


class WorkbenchServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.state_path = root / "state.json"
        self.client_dir = root / "client"
        self.client_dir.mkdir()
        (self.client_dir / "index.html").write_text("<!doctype html><title>Workbench</title>", encoding="utf-8")
        self.codex_home = root / ".codex"
        session_dir = self.codex_home / "sessions" / "2026" / "09" / "23"
        session_dir.mkdir(parents=True)
        task_id = "55555555-5555-5555-5555-555555555555"
        (self.codex_home / "session_index.jsonl").write_text(
            json.dumps({"id": task_id, "thread_name": "具身智能比赛机械臂抓取", "updated_at": "2026-09-23T03:00:00Z"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (session_dir / f"rollout-2026-09-23T03-00-00-{task_id}.jsonl").write_text(
            json.dumps({"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "参加具身智能机器人比赛"}]}}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        server_module.initialize_store(self.state_path, demo=True)
        self.server = server_module.create_server(self.state_path, 0, self.client_dir, codex_home=self.codex_home, context_depth=5)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def request(self, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"} if data is not None else {},
            method="POST" if data is not None else "GET",
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def raw_request(self, method: str, path: str, headers: dict[str, str], body: bytes = b"") -> tuple[int, bytes]:
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        self.addCleanup(connection.close)
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for name, value in {**headers, "Content-Length": str(len(body))}.items():
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        return response.status, response.read()

    def test_rejects_foreign_host_header_to_block_dns_rebinding(self) -> None:
        port = self.server.server_port
        status, body = self.raw_request("GET", "/api/state", {"Host": f"attacker.example:{port}"})

        self.assertEqual(status, 403)
        self.assertNotIn(b"candidates", body)
        for host in (f"127.0.0.1:{port}", f"localhost:{port}"):
            status, _ = self.raw_request("GET", "/api/state", {"Host": host})
            self.assertEqual(status, 200, host)

    def test_rejects_cross_origin_writes(self) -> None:
        port = self.server.server_port
        body = json.dumps({"source_id": "demo-context", "status": "paused"}).encode("utf-8")
        headers = {"Host": f"127.0.0.1:{port}", "Content-Type": "application/json"}

        status, _ = self.raw_request("POST", "/api/source-status", {**headers, "Origin": "https://attacker.example"}, body)
        self.assertEqual(status, 403)
        _, state = self.request("/api/state")
        self.assertEqual(next(row for row in state["sources"] if row["id"] == "demo-context")["status"], "active")

        status, _ = self.raw_request("POST", "/api/source-status", {**headers, "Origin": f"http://127.0.0.1:{port}"}, body)
        self.assertEqual(status, 200)

    def test_rejects_cors_safelisted_content_type_that_mentions_json(self) -> None:
        # Browsers send "text/plain; application/json" cross-site without a
        # preflight, so a substring check on the header is not a CSRF defence.
        port = self.server.server_port
        body = json.dumps({"source_id": "demo-context", "status": "paused"}).encode("utf-8")
        status, _ = self.raw_request(
            "POST",
            "/api/source-status",
            {"Host": f"127.0.0.1:{port}", "Content-Type": "text/plain; application/json"},
            body,
        )

        self.assertEqual(status, 400)
        _, state = self.request("/api/state")
        self.assertEqual(next(row for row in state["sources"] if row["id"] == "demo-context")["status"], "active")

    def test_state_exposes_seeded_candidates_without_raw_context(self) -> None:
        status, payload = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(payload["goal"]["statement"], server_module.codex_context.LEARNING_DIRECTION)
        self.assertEqual(len(payload["candidates"]), 5)
        self.assertEqual(payload["focusPoints"][0], "介绍产品的核心功能和使用场景")
        self.assertNotIn("locator", payload["sources"][0])
        self.assertTrue(payload["connected"])
        self.assertEqual(payload["library"]["entryCount"], 3740)
        # The full lexicon is not resent on every request; the vocabulary view carries the ranked rows.
        self.assertNotIn("entries", payload["library"])
        self.assertEqual(len(payload["personalVocabulary"]["entries"]), 500)
        self.assertEqual(len(payload["library"]["scenarios"]), 19)
        self.assertEqual(payload["personalVocabulary"]["entryCount"], 500)
        self.assertGreaterEqual(payload["personalVocabulary"]["uniqueTermCount"], 490)
        self.assertEqual(payload["personalVocabulary"]["title"], "我的英语词表")
        self.assertEqual(payload["reviewQueue"], [])

    def test_decision_and_review_share_durable_store(self) -> None:
        _, initial = self.request("/api/state")
        item = initial["candidates"][0]
        status, decided = self.request(
            "/api/decision", {"item_id": item["id"], "decision": "learning"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            next(candidate for candidate in decided["candidates"] if candidate["id"] == item["id"])["status"],
            "learning",
        )
        self.assertEqual(len(decided["reviewQueue"]), 2)
        self.assertEqual({row["mode"] for row in decided["reviewQueue"]}, {"recognition", "production"})

        status, reviewed = self.request(
            "/api/review",
            {"item_id": item["id"], "mode": item["mode"], "feedback": "good", "response_ms": 1250},
        )
        self.assertEqual(status, 200)
        # The sample item has separate production and recognition tracks. The
        # reviewed track is scheduled while the other track remains due.
        self.assertEqual(reviewed["dueCount"], 1)
        self.assertEqual(len(reviewed["reviewQueue"]), 1)
        self.assertNotEqual(reviewed["reviewQueue"][0]["mode"], item["mode"])
        state = server_module.store.load_state(self.state_path)
        self.assertEqual(len(state["reviews"]), 1)
        self.assertEqual(state["reviews"][0]["response_ms"], 1250)

    def test_source_can_be_paused_and_invalid_input_is_rejected(self) -> None:
        status, payload = self.request(
            "/api/source-status", {"source_id": "demo-context", "status": "paused"}
        )
        self.assertEqual(status, 200)
        demo_source = next(source for source in payload["sources"] if source["id"] == "demo-context")
        self.assertEqual(demo_source["status"], "paused")

        status, error = self.request(
            "/api/decision", {"item_id": payload["candidates"][0]["id"], "decision": "delete"}
        )
        self.assertEqual(status, 400)
        self.assertIn("decision", error["error"])

    def test_library_entry_can_be_added_to_learning(self) -> None:
        _, initial = self.request("/api/state")
        hello = next(entry for entry in initial["personalVocabulary"]["entries"] if entry["term"] == "hello")

        status, updated = self.request(
            "/api/library-decision", {"entry_id": hello["lexiconEntryId"], "decision": "learning"}
        )

        self.assertEqual(status, 200)
        updated_hello = next(
            entry for entry in updated["personalVocabulary"]["entries"]
            if entry["lexiconEntryId"] == hello["lexiconEntryId"]
        )
        self.assertEqual(updated_hello["status"], "learning")
        self.assertIn("hello", [candidate["term"] for candidate in updated["candidates"]])
        self.assertEqual(updated["dueCount"], 2)
        self.assertEqual({row["mode"] for row in updated["reviewQueue"]}, {"recognition", "production"})

    def test_review_rejects_invalid_response_time(self) -> None:
        _, initial = self.request("/api/state")
        item = initial["candidates"][0]
        self.request("/api/decision", {"item_id": item["id"], "decision": "learning"})

        status, error = self.request(
            "/api/review",
            {"item_id": item["id"], "mode": item["mode"], "feedback": "good", "response_ms": -1},
        )

        self.assertEqual(status, 400)
        self.assertIn("response_ms", error["error"])

    def test_context_scan_and_topic_selection_are_available_from_workbench(self) -> None:
        status, scanned = self.request("/api/context-scan", {})

        self.assertEqual(status, 200)
        self.assertEqual(scanned["contextIndex"]["coverage"]["discoveredTaskCount"], 1)
        self.assertEqual(scanned["contextIndex"]["coverage"]["deepAnalyzedTaskCount"], 1)
        self.assertIn("embodied-ai", {topic["id"] for topic in scanned["contextIndex"]["topics"]})
        # The per-task index stays on disk; responses carry coverage and topics only.
        self.assertNotIn("tasks", scanned["contextIndex"])
        self.assertNotIn("lexiconMatches", scanned["contextIndex"])
        self.assertEqual(len(server_module.store.load_state(self.state_path)["context_index"]["tasks"]), 1)
        learning_direction = scanned["goal"]["statement"]

        status, selected = self.request("/api/context-topic", {"topic_id": "embodied-ai"})
        self.assertEqual(status, 200)
        self.assertEqual(selected["contextIndex"]["activeTopicId"], "embodied-ai")
        self.assertEqual(selected["goal"]["statement"], learning_direction)
        self.assertEqual(selected["goal"]["statement"], server_module.codex_context.LEARNING_DIRECTION)


if __name__ == "__main__":
    unittest.main()
