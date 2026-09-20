from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "contextual-vocab-coach" / "scripts" / "vocab_store.py"
SPEC = importlib.util.spec_from_file_location("vocab_store", MODULE_PATH)
assert SPEC and SPEC.loader
store = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(store)


def sample_pack() -> dict:
    return json.loads(
        (ROOT / "contextual-vocab-coach" / "examples" / "sample-pack.json").read_text(encoding="utf-8")
    )


class VocabStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.path = Path(self.tempdir.name) / "state.json"
        self.t0 = "2026-09-21T12:00:00Z"
        state = store.empty_state(self.t0)
        store.save_state(self.path, state)

    def apply_sample(self, now: str = "2026-09-21T12:01:00Z") -> dict:
        state = store.load_state(self.path)
        store.apply_pack(state, sample_pack(), now)
        store.save_state(self.path, state)
        return state

    def test_reimport_preserves_decision_and_review_history(self) -> None:
        self.apply_sample()
        args = argparse.Namespace(item="estimate portion sizes", decision="learning")
        store.command_decide(args, self.path, "2026-09-21T12:02:00Z")
        review_args = argparse.Namespace(
            item="estimate portion sizes",
            mode="production",
            feedback="good",
            response_ms=4200,
            strategy="personal-scene",
            personalized=True,
            transfer_test=False,
            context_note="first attempt",
        )
        store.command_review(review_args, self.path, "2026-09-21T12:03:00Z")

        state = store.load_state(self.path)
        store.apply_pack(state, sample_pack(), "2026-09-21T13:00:00Z")
        store.save_state(self.path, state)
        reloaded = store.load_state(self.path)
        item_id, candidate = store.resolve_item(reloaded, "estimate portion sizes")

        self.assertEqual(candidate["status"], "learning")
        self.assertEqual(len(reloaded["reviews"]), 1)
        self.assertEqual(reloaded["learning_items"][item_id]["tracks"]["production"]["repetitions"], 1)

    def test_known_and_not_now_are_not_overwritten_by_context_refresh(self) -> None:
        self.apply_sample()
        store.command_decide(
            argparse.Namespace(item="dietary preferences", decision="known"),
            self.path,
            "2026-09-21T12:02:00Z",
        )
        store.command_decide(
            argparse.Namespace(item="prioritize", decision="not_now"),
            self.path,
            "2026-09-21T12:03:00Z",
        )
        state = store.load_state(self.path)
        store.apply_pack(state, sample_pack(), "2026-09-22T12:00:00Z")

        self.assertEqual(store.resolve_item(state, "dietary preferences")[1]["status"], "known")
        self.assertEqual(store.resolve_item(state, "prioritize")[1]["status"], "not_now")

    def test_review_modes_have_independent_schedules(self) -> None:
        self.apply_sample()
        store.command_decide(
            argparse.Namespace(item="estimate portion sizes", decision="learning"),
            self.path,
            "2026-09-21T12:02:00Z",
        )
        state_before = store.load_state(self.path)
        item_id, _ = store.resolve_item(state_before, "estimate portion sizes")
        recognition_due = state_before["learning_items"][item_id]["tracks"]["recognition"]["due_at"]
        review_args = argparse.Namespace(
            item=item_id,
            mode="production",
            feedback="easy",
            response_ms=900,
            strategy="contrast",
            personalized=True,
            transfer_test=True,
            context_note="new audience",
        )
        store.command_review(review_args, self.path, "2026-09-21T12:03:00Z")
        state_after = store.load_state(self.path)
        tracks = state_after["learning_items"][item_id]["tracks"]

        self.assertEqual(tracks["recognition"]["due_at"], recognition_due)
        self.assertNotEqual(tracks["production"]["due_at"], recognition_due)
        self.assertTrue(state_after["reviews"][0]["transfer_test"])

    def test_metadata_deletion_preserves_explicit_learning_but_removes_source_context(self) -> None:
        self.apply_sample()
        store.command_decide(
            argparse.Namespace(item="estimate portion sizes", decision="learning"),
            self.path,
            "2026-09-21T12:02:00Z",
        )
        args = argparse.Namespace(source_id="demo-context", mode="metadata")
        result = store.command_source_delete(args, self.path, "2026-09-21T12:04:00Z")
        state = store.load_state(self.path)
        item_id, candidate = store.resolve_item(state, "estimate portion sizes")

        self.assertEqual(result["removed_learning_items"], [])
        self.assertIn(item_id, state["learning_items"])
        self.assertEqual(candidate["source_ids"], [])
        self.assertEqual(state["learning_items"][item_id]["personal_anchor"], "")
        self.assertNotIn("demo-context", state["sources"])
        self.assertNotIn("prioritize", [item["term"] for item in state["candidates"].values()])

    def test_purge_removes_source_only_items_and_reviews(self) -> None:
        self.apply_sample()
        store.command_decide(
            argparse.Namespace(item="estimate portion sizes", decision="learning"),
            self.path,
            "2026-09-21T12:02:00Z",
        )
        review_args = argparse.Namespace(
            item="estimate portion sizes",
            mode="production",
            feedback="hard",
            response_ms=8000,
            strategy="personal-scene",
            personalized=True,
            transfer_test=False,
            context_note="",
        )
        store.command_review(review_args, self.path, "2026-09-21T12:03:00Z")
        result = store.command_source_delete(
            argparse.Namespace(source_id="demo-context", mode="purge"),
            self.path,
            "2026-09-21T12:04:00Z",
        )
        state = store.load_state(self.path)

        self.assertTrue(result["removed_learning_items"])
        self.assertEqual(state["candidates"], {})
        self.assertEqual(state["learning_items"], {})
        self.assertEqual(state["reviews"], [])

    def test_pack_requires_explicit_source_authorization(self) -> None:
        pack = copy.deepcopy(sample_pack())
        pack["sources"][0]["authorized"] = False
        with self.assertRaisesRegex(store.StoreError, "not explicitly authorized"):
            store.apply_pack(store.load_state(self.path), pack, "2026-09-21T12:01:00Z")

    def test_markdown_status_is_a_learning_record_not_a_brain_claim(self) -> None:
        state = self.apply_sample()
        payload = store.status_payload(state, "2026-09-21T12:02:00Z")
        rendered = store.render_markdown(payload)
        self.assertIn("Vocabulary learning status", rendered)
        self.assertIn("Active goal", rendered)
        self.assertIn("Task-to-vocabulary mastery", rendered)
        self.assertIn("estimate portion sizes", rendered)
        self.assertNotIn("brain", rendered.casefold())


if __name__ == "__main__":
    unittest.main()
