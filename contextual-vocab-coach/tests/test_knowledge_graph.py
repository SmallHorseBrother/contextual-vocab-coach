"""Meaningful graph invariants: provenance, freshness, and human decisions."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import knowledge_graph  # noqa: E402
import vocab_store as store  # noqa: E402
import workbench_server  # noqa: E402


def row(term, meaning, *, status="proposed"):
    return {
        "term": term, "meaning": meaning, "status": status,
        "sourceType": "contextual", "taskCount": 0,
        "contextIds": ["engineering-ops"], "primaryContextId": "engineering-ops",
        "contextLabels": ["工程开发与基础设施"], "scenarioIds": [], "scenarioLabels": [],
    }


class KnowledgeGraphTests(unittest.TestCase):
    def test_new_word_becomes_seen_without_changing_learning_status(self):
        state = store.empty_state("2026-09-24T00:00:00Z")
        index = {"indexedAt": "2026-09-24T00:00:00Z", "tasks": []}
        old = [row("deployment pipeline", "部署流水线", status="learning"), row("root cause", "根本原因")]
        knowledge_graph.sync_graph(state, old, index, "2026-09-24T00:00:00Z")
        self.assertEqual(knowledge_graph.payload(state, old)["unseenCount"], 0)

        expanded = [*old, row("continuous delivery", "持续交付")]
        knowledge_graph.sync_graph(state, expanded, index, "2026-09-24T01:00:00Z")
        graph = knowledge_graph.payload(state, expanded)
        fresh = next(node for node in graph["nodes"] if node["term"] == "continuous delivery")
        self.assertTrue(fresh["isNew"])
        self.assertEqual(fresh["status"], "proposed")
        suggestions = [edge for edge in graph["edges"] if fresh["id"] in (edge["source"], edge["target"]) and edge["status"] == "suggested"]
        self.assertTrue(suggestions)
        knowledge_graph.change_relation(state, suggestions[0]["id"], "accept", None, "2026-09-24T01:05:00Z")
        self.assertEqual(state["knowledge_graph"]["edges"][suggestions[0]["id"]]["status"], "confirmed")
        knowledge_graph.mark_seen(state, [fresh["id"]], "2026-09-24T01:06:00Z")
        after = knowledge_graph.payload(state, expanded)
        self.assertEqual(after["unseenCount"], 0)
        self.assertEqual(next(node for node in after["nodes"] if node["id"] == fresh["id"])["status"], "proposed")
        knowledge_graph.sync_graph(state, expanded, index, "2026-09-24T02:00:00Z")
        self.assertEqual(state["knowledge_graph"]["edges"][suggestions[0]["id"]]["status"], "confirmed")

    def test_workbench_adds_new_expression_without_scheduling_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store.save_state(path, store.empty_state("2026-09-24T00:00:00Z"))
            workbench_server.workbench_state(path)
            result = workbench_server.apply_graph_add(path, {"term": "continuous delivery", "meaning": "持续交付"})
            self.assertEqual(result["knowledgeGraph"]["unseenCount"], 1)
            added = next(node for node in result["knowledgeGraph"]["nodes"] if node["term"] == "continuous delivery")
            self.assertEqual(added["status"], "proposed")
            self.assertEqual(result["dueCount"], 0)
            self.assertEqual(len(store.load_state(path)["learning_items"]), 0)

    def test_incremental_add_does_not_expand_unrelated_old_pairs(self):
        state = store.empty_state("2026-09-24T00:00:00Z")
        index = {"indexedAt": "2026-09-24T00:00:00Z", "tasks": []}
        baseline = [row("deployment pipeline", "部署流水线"), row("root cause", "根本原因"), row("temporary workaround", "临时解决办法")]
        knowledge_graph.sync_graph(state, baseline, index, "2026-09-24T00:00:00Z")
        old_edges = set(state["knowledge_graph"]["edges"])
        old_ids = {knowledge_graph.node_id(entry) for entry in baseline}
        added_row = row("continuous delivery", "持续交付")
        knowledge_graph.sync_graph(state, [*baseline, added_row], index, "2026-09-24T01:00:00Z")
        new_edges = [edge for ident, edge in state["knowledge_graph"]["edges"].items() if ident not in old_edges]
        self.assertTrue(new_edges)
        self.assertTrue(all(knowledge_graph.node_id(added_row) in {edge["source"], edge["target"]} for edge in new_edges))
        self.assertTrue(old_ids <= set(state["knowledge_graph"]["nodes"]))

    def test_automatic_topic_for_delivery_phrase(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store.save_state(path, store.empty_state("2026-09-24T00:00:00Z"))
            workbench_server.workbench_state(path)
            result = workbench_server.apply_graph_add(path, {"term": "continuous delivery", "meaning": "持续交付"})
            added = next(node for node in result["knowledgeGraph"]["nodes"] if node["term"] == "continuous delivery")
            self.assertEqual(added["primaryContextId"], "engineering-ops")


if __name__ == "__main__":
    unittest.main()
