from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "contextual-vocab-coach" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("codex_context", SCRIPTS / "codex_context.py")
assert SPEC and SPEC.loader
context = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(context)


class CodexContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        root = Path(self.tempdir.name)
        self.codex_home = root / ".codex"
        self.sessions = self.codex_home / "sessions" / "2026" / "09" / "23"
        self.sessions.mkdir(parents=True)
        self.store_path = root / "store" / "state.json"
        state = context.store.empty_state("2026-09-23T00:00:00Z")
        context.store.save_state(self.store_path, state)

        self.ids = {
            "robot": "11111111-1111-1111-1111-111111111111",
            "food": "22222222-2222-2222-2222-222222222222",
            "english": "33333333-3333-3333-3333-333333333333",
            "untitled": "44444444-4444-4444-4444-444444444444",
        }
        rows = [
            {"id": self.ids["robot"], "thread_name": "具身智能比赛机械臂抓取", "updated_at": "2026-09-23T03:00:00Z"},
            {"id": self.ids["food"], "thread_name": "FoodLink 过敏原筛选", "updated_at": "2026-09-23T02:00:00Z"},
            {"id": self.ids["english"], "thread_name": "构建上下文英语学习 Skill", "updated_at": "2026-09-23T01:00:00Z"},
        ]
        (self.codex_home / "session_index.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
        for name, task_id in self.ids.items():
            path = self.sessions / f"rollout-2026-09-23T00-00-00-{task_id}.jsonl"
            message = {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": f"{name} user context"}],
                },
            }
            path.write_text(json.dumps(message, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_scan_covers_all_tasks_and_builds_separate_topic_candidates(self) -> None:
        result = context.scan_into_store(self.store_path, codex_home=self.codex_home, deep_limit=3)

        self.assertEqual(result["coverage"]["discoveredTaskCount"], 4)
        self.assertEqual(result["coverage"]["titledTaskCount"], 3)
        self.assertEqual(result["coverage"]["deepAnalyzedTaskCount"], 3)
        self.assertFalse(result["coverage"]["rawContentStored"])
        topics = {topic["id"] for topic in result["topics"]}
        self.assertTrue({"embodied-ai", "food-health", "english-learning", "general"} <= topics)

        state = context.store.load_state(self.store_path)
        active_goal = state["goals"][state["profile"]["active_goal_id"]]
        self.assertEqual(active_goal["statement"], context.LEARNING_DIRECTION)
        self.assertTrue(active_goal["confirmed"])
        candidate_topics = {candidate.get("topic_id") for candidate in state["candidates"].values()}
        self.assertTrue({"embodied-ai", "food-health", "english-learning"} <= candidate_topics)
        serialized = json.dumps(state, ensure_ascii=False)
        self.assertNotIn("robot user context", serialized)
        self.assertEqual(
            context.classify("debug api server", title="清华 FoodLink 项目 PPT")[0],
            "food-health",
        )

    def test_rescan_preserves_decisions_and_topic_selection(self) -> None:
        context.scan_into_store(self.store_path, codex_home=self.codex_home, deep_limit=2)
        state = context.store.load_state(self.store_path)
        goal_id_before_topic_switch = state["profile"]["active_goal_id"]
        robot_candidate = next(
            candidate for candidate in state["candidates"].values() if candidate.get("topic_id") == "embodied-ai"
        )
        context.store.command_decide(
            type("Args", (), {"item": robot_candidate["id"], "decision": "known"})(),
            self.store_path,
            "2026-09-23T04:00:00Z",
        )

        context.scan_into_store(self.store_path, codex_home=self.codex_home, deep_limit=2)
        state = context.store.load_state(self.store_path)
        self.assertEqual(state["candidates"][robot_candidate["id"]]["status"], "known")

        context.select_topic(self.store_path, "embodied-ai")
        selected = context.store.load_state(self.store_path)
        self.assertEqual(selected["context_index"]["activeTopicId"], "embodied-ai")
        active_goal = selected["goals"][selected["profile"]["active_goal_id"]]
        self.assertEqual(selected["profile"]["active_goal_id"], goal_id_before_topic_switch)
        self.assertEqual(active_goal["statement"], context.LEARNING_DIRECTION)

    def test_full_scan_caches_every_rollout_and_reuses_unchanged_results(self) -> None:
        untitled_path = next(self.sessions.glob(f"*{self.ids['untitled']}.jsonl"))
        long_message = {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "x" * 140_000 + " goal"}],
            },
        }
        untitled_path.write_text(json.dumps(long_message) + "\n", encoding="utf-8")
        first = context.scan_into_store(self.store_path, codex_home=self.codex_home, deep_limit=-1)

        self.assertEqual(first["coverage"]["deepAnalyzedTaskCount"], 4)
        self.assertEqual(first["coverage"]["fullContentScannedTaskCount"], 4)
        self.assertEqual(first["coverage"]["newOrChangedTaskCount"], 4)
        self.assertEqual(first["coverage"]["reusedContentTaskCount"], 0)
        self.assertGreater(first["coverage"]["bytesReadThisScan"], 140_000)
        self.assertTrue(all("rolloutFingerprint" in task for task in first["tasks"] if task["hasRollout"]))
        untitled_task = next(task for task in first["tasks"] if task["id"] == self.ids["untitled"])
        goal_entry = next(row for row in context.STARTER_LEXICON_ENTRIES if row["term"] == "goal")
        self.assertIn(goal_entry["id"], untitled_task["lexiconEntryIds"])

        second = context.scan_into_store(self.store_path, codex_home=self.codex_home, deep_limit=-1)

        self.assertEqual(second["coverage"]["deepAnalyzedTaskCount"], 4)
        self.assertEqual(second["coverage"]["newOrChangedTaskCount"], 0)
        self.assertEqual(second["coverage"]["reusedContentTaskCount"], 4)
        self.assertEqual(second["coverage"]["bytesReadThisScan"], 0)


if __name__ == "__main__":
    unittest.main()
