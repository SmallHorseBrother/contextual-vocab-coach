"""No-Codex context intake and controllable vocabulary inventory."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import context_intake  # noqa: E402
import vocab_store as store  # noqa: E402
import workbench_server  # noqa: E402


class ContextIntakeTests(unittest.TestCase):
    def test_append_without_codex_preserves_only_derived_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            workbench_server.initialize_store(path)
            first = workbench_server.workbench_state(path)
            self.assertEqual(first["personalVocabulary"]["entryCount"], 500)
            self.assertGreaterEqual(first["personalVocabulary"]["availableCount"], 3700)
            self.assertEqual(first["personalContext"]["totalSegments"], 0)

            secret = "我周末做饭和购物，也会做一个健康饮食产品，想介绍设计思路和用户体验。"
            imported = workbench_server.apply_personal_context(path, {"label": "我的生活", "text": secret})
            self.assertEqual(imported["contextImport"]["segmentCount"], 1)
            self.assertGreater(imported["contextImport"]["matchedCount"], 0)
            self.assertGreater(imported["personalVocabulary"]["personalCount"], 0)
            self.assertTrue(imported["personalVocabulary"]["updatedAt"])
            self.assertEqual(imported["reviewQueue"], [])
            self.assertNotIn(secret, path.read_text(encoding="utf-8"))
            self.assertFalse(imported["personalContext"]["rawContentStored"])

            more = "我还参加机器人比赛，研究机械臂抓取和传感器，也要记录实验结果。"
            appended = workbench_server.apply_personal_context(path, {"label": "我的生活", "text": more})
            self.assertEqual(appended["contextImport"]["segmentCount"], 2)
            self.assertEqual(len(appended["personalContext"]["sources"]), 1)
            self.assertNotIn(more, path.read_text(encoding="utf-8"))

    def test_scale_switch_is_exact_and_does_not_schedule_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            workbench_server.initialize_store(path)
            for amount in (1000, 2500, 500):
                payload = workbench_server.apply_vocabulary_target(path, {"target": amount})
                self.assertEqual(payload["personalVocabulary"]["targetSize"], amount)
                self.assertEqual(payload["personalVocabulary"]["entryCount"], amount)
                self.assertEqual(payload["reviewQueue"], [])
            with self.assertRaises(store.StoreError):
                workbench_server.apply_vocabulary_target(path, {"target": 750})
            self.assertEqual(context_intake.target_size(store.load_state(path)), 500)

    def test_deleting_manual_source_removes_derived_links(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            workbench_server.initialize_store(path)
            imported = workbench_server.apply_personal_context(path, {
                "label": "我的周末", "text": "我周末做饭和购物，去公园散步，还想用英语介绍自己的生活习惯。",
            })
            source_id = imported["contextImport"]["sourceId"]
            self.assertEqual(imported["personalContext"]["totalSegments"], 1)
            store.command_source_delete(
                type("Options", (), {"source_id": source_id, "mode": "metadata"})(),
                path, store.iso_now(),
            )
            after = workbench_server.workbench_state(path)
            self.assertEqual(after["personalContext"]["totalSegments"], 0)
            self.assertEqual(after["personalVocabulary"]["personalCount"], 0)


if __name__ == "__main__":
    unittest.main()
