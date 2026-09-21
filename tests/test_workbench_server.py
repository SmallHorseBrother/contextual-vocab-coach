from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import unittest
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
        server_module.initialize_store(self.state_path, demo=True)
        self.server = server_module.create_server(self.state_path, 0, self.client_dir)
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

    def test_state_exposes_seeded_candidates_without_raw_context(self) -> None:
        status, payload = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(payload["goal"]["statement"], "用英语介绍我的产品")
        self.assertEqual(len(payload["candidates"]), 5)
        self.assertEqual(payload["focusPoints"][0], "介绍产品的核心功能和使用场景")
        self.assertNotIn("locator", payload["sources"][0])
        self.assertTrue(payload["connected"])

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

        status, reviewed = self.request(
            "/api/review",
            {"item_id": item["id"], "mode": item["mode"], "feedback": "good"},
        )
        self.assertEqual(status, 200)
        # The sample item has separate production and recognition tracks. The
        # reviewed track is scheduled while the other track remains due.
        self.assertEqual(reviewed["dueCount"], 1)
        state = server_module.store.load_state(self.state_path)
        self.assertEqual(len(state["reviews"]), 1)

    def test_source_can_be_paused_and_invalid_input_is_rejected(self) -> None:
        status, payload = self.request(
            "/api/source-status", {"source_id": "demo-context", "status": "paused"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["sources"][0]["status"], "paused")

        status, error = self.request(
            "/api/decision", {"item_id": payload["candidates"][0]["id"], "decision": "delete"}
        )
        self.assertEqual(status, 400)
        self.assertIn("decision", error["error"])


if __name__ == "__main__":
    unittest.main()
