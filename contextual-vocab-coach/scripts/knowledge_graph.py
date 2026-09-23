"""Persistent, evidence-labelled relationships for the personal vocabulary map.

The local graph deliberately uses only derived vocabulary metadata and task IDs.
It never persists conversation text or claims that topical proximity is synonymy.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

import vocab_store as store


GRAPH_VERSION = 1
RELATION_TYPES = {"same_scene", "component", "similar", "collocation", "contrast", "prerequisite"}
STOPWORDS = {"a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with", "you", "your"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def node_id(row: dict[str, Any]) -> str:
    return store.stable_id("graph", row["term"], row["meaning"])


def _tokens(value: str) -> set[str]:
    return {token for token in TOKEN_PATTERN.findall(store.normalize(value)) if len(token) > 2 and token not in STOPWORDS}


def _signature(rows: list[dict[str, Any]], context_index: dict[str, Any]) -> str:
    facts = [
        (node_id(row), row.get("taskCount", 0), sorted(row.get("contextIds", [])), sorted(row.get("scenarioIds", [])))
        for row in rows
    ]
    task_facts = [
        (task.get("id"), task.get("rolloutFingerprint"), task.get("topicId"))
        for task in context_index.get("tasks", [])
    ]
    encoded = json.dumps((sorted(facts), sorted(task_facts)), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _co_tasks(rows: list[dict[str, Any]], context_index: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    by_lexicon_id = {row.get("lexiconEntryId"): node_id(row) for row in rows if row.get("lexiconEntryId")}
    result: dict[tuple[str, str], list[str]] = defaultdict(list)
    for task in context_index.get("tasks", []):
        ids = sorted({by_lexicon_id[entry] for entry in task.get("lexiconEntryIds", []) if entry in by_lexicon_id})
        # Very broad messages should not make every mentioned word a close neighbour.
        if len(ids) > 24:
            continue
        for index, left in enumerate(ids):
            for right in ids[index + 1:]:
                pair = (left, right)
                if len(result[pair]) < 3:
                    result[pair].append(task.get("title") or "一项 Codex 任务")
    return result


def _candidate_pairs(rows: list[dict[str, Any]], co_tasks: dict[tuple[str, str], list[str]]) -> set[tuple[str, str]]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    topic_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ident = node_id(row)
        for token in _tokens(row["term"]):
            groups[("term", token)].append(ident)
        for topic in row.get("contextIds", []):
            groups[("topic", topic)].append(ident)
            topic_rows[topic].append(row)
        for scenario in row.get("scenarioIds", []):
            groups[("scenario", scenario)].append(ident)
        groups[("meaning", store.normalize(row["meaning"]))].append(ident)
    pairs = set(co_tasks)
    for (kind, _), ids in groups.items():
        # A generic token or scenario is not useful evidence for every pair.
        if len(ids) > (100 if kind == "topic" else 75):
            continue
        for index, left in enumerate(ids):
            for right in ids[index + 1:]:
                if left != right:
                    pairs.add(tuple(sorted((left, right))))
    # A populous task domain can exceed the generic group cap. Still connect
    # its curated expressions to one another and to its strongest observed words.
    for members in topic_rows.values():
        contextual = [row for row in members if row.get("sourceType") == "contextual"]
        observed = sorted(
            (row for row in members if row.get("sourceType") == "observed"),
            key=lambda row: (-row.get("taskCount", 0), row["term"]),
        )[:25]
        for row in contextual:
            for peer in [*contextual, *observed]:
                if node_id(row) != node_id(peer):
                    pairs.add(tuple(sorted((node_id(row), node_id(peer)))))
    return pairs


def _infer(left: dict[str, Any], right: dict[str, Any], titles: list[str]) -> dict[str, Any] | None:
    left_term = store.normalize(left["term"])
    right_term = store.normalize(right["term"])
    shared_words = _tokens(left_term) & _tokens(right_term)
    left_topics = {left["primaryContextId"]} if left.get("sourceType") == "contextual" and left.get("primaryContextId") else set(left.get("contextIds", []))
    right_topics = {right["primaryContextId"]} if right.get("sourceType") == "contextual" and right.get("primaryContextId") else set(right.get("contextIds", []))
    shared_topics = left_topics & right_topics
    shared_scenarios = set(left.get("scenarioIds", [])) & set(right.get("scenarioIds", []))
    if store.normalize(left["meaning"]) == store.normalize(right["meaning"]) and left_term != right_term:
        return {"type": "similar", "confidence": 0.94, "reason": "两个表达在词表中标注了相同的中文含义。", "evidence": left["meaning"]}
    if left_term != right_term and (re.search(rf"\b{re.escape(left_term)}\b", right_term) or re.search(rf"\b{re.escape(right_term)}\b", left_term)):
        return {"type": "component", "confidence": 0.89, "reason": "一个表达完整出现在另一个表达中，可以一起记住它的用法。", "evidence": f"{left['term']} · {right['term']}"}
    if titles and len(titles) >= 2:
        return {"type": "same_scene", "confidence": 0.86, "reason": "这两个表达在多项相同任务的用户消息中出现。", "evidence": "、".join(titles[:2])}
    if shared_words and shared_topics:
        return {"type": "same_scene", "confidence": 0.82, "reason": "两个表达共享英文关键词，并标注了同一领域；这是场景线索，不等于同义。", "evidence": f"共同词：{', '.join(sorted(shared_words))}；相关领域：{', '.join(sorted(shared_topics))}"}
    if titles:
        return {"type": "same_scene", "confidence": 0.76, "reason": "两个表达曾在同一项任务的用户消息中出现；这说明使用场景相关，不代表词义相同。", "evidence": titles[0]}
    if shared_words and shared_scenarios:
        return {"type": "collocation", "confidence": 0.69, "reason": "两个表达共享英文关键词，也用于同一生活场景。", "evidence": f"共同词：{', '.join(sorted(shared_words))}"}
    if shared_topics and left.get("sourceType") == "contextual" and right.get("sourceType") == "contextual":
        labels = sorted(set(left.get("contextLabels", [])) & set(right.get("contextLabels", [])))
        return {"type": "same_scene", "confidence": 0.61, "reason": "两个表达属于同一任务领域；这是待核对的场景联系。", "evidence": "、".join(labels) or "相同任务领域"}
    if shared_scenarios:
        labels = sorted(set(left.get("scenarioLabels", [])) & set(right.get("scenarioLabels", [])))
        return {"type": "same_scene", "confidence": 0.57, "reason": "两个表达属于同一生活场景；这是待核对的场景联系。", "evidence": "、".join(labels) or "相同生活场景"}
    return None


def sync_graph(state: dict[str, Any], rows: list[dict[str, Any]], context_index: dict[str, Any], now: str) -> bool:
    """Incrementally add nodes and inferred edges; preserve human decisions."""
    graph = state.get("knowledge_graph")
    initial = not isinstance(graph, dict) or graph.get("version") != GRAPH_VERSION
    if initial:
        graph = {"version": GRAPH_VERSION, "nodes": {}, "edges": {}, "unseen_ids": [], "last_added_ids": [], "last_scan_at": "", "signature": ""}
    signature = _signature(rows, context_index)
    if graph.get("signature") == signature:
        return False

    row_by_id = {node_id(row): row for row in rows}
    existing_ids = set(graph["nodes"])
    current_ids = set(row_by_id)
    for removed_id in existing_ids - current_ids:
        graph["nodes"].pop(removed_id, None)
    graph["unseen_ids"] = [ident for ident in graph["unseen_ids"] if ident in current_ids]
    graph["edges"] = {
        ident: edge for ident, edge in graph["edges"].items()
        if edge["source"] in current_ids and edge["target"] in current_ids
    }
    added = sorted(current_ids - existing_ids)
    for ident in added:
        graph["nodes"][ident] = {"first_seen_at": now}
    if not initial:
        graph["unseen_ids"] = list(dict.fromkeys([*graph["unseen_ids"], *added]))
    graph["last_added_ids"] = [] if initial else added

    co_tasks = _co_tasks(rows, context_index)
    inferred: list[dict[str, Any]] = []
    for left_id, right_id in _candidate_pairs(rows, co_tasks):
        # An incremental update should attach its new nodes, not revisit every
        # previously rejected pair and silently double the whole graph.
        if not initial and not ({left_id, right_id} & set(added)):
            continue
        edge_id = store.stable_id("relation", left_id, right_id)
        if edge_id in graph["edges"]:
            continue
        proposal = _infer(row_by_id[left_id], row_by_id[right_id], co_tasks.get((left_id, right_id), []))
        if proposal:
            inferred.append({"id": edge_id, "source": left_id, "target": right_id, **proposal})
    neighbour_options: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in inferred:
        neighbour_options[edge["source"]].append(edge)
        neighbour_options[edge["target"]].append(edge)
    chosen: set[str] = set()
    for ident, options in neighbour_options.items():
        options.sort(key=lambda edge: (-edge["confidence"], edge["id"]))
        limit = 6 if row_by_id[ident].get("sourceType") == "contextual" else 4
        chosen.update(edge["id"] for edge in options[:limit])
    new_suggestion_count: dict[str, int] = defaultdict(int)
    for edge in sorted((edge for edge in inferred if edge["id"] in chosen), key=lambda item: (-item["confidence"], item["id"])):
        left, right = edge["source"], edge["target"]
        new_endpoints = [ident for ident in (left, right) if ident in added]
        if edge["confidence"] >= 0.84:
            edge["status"] = "confirmed"
        elif not initial and new_endpoints and all(new_suggestion_count[ident] < 3 for ident in new_endpoints):
            edge["status"] = "suggested"
            for ident in new_endpoints:
                new_suggestion_count[ident] += 1
        else:
            edge["status"] = "inferred"
        edge["created_at"] = now
        graph["edges"][edge["id"]] = edge

    graph["last_scan_at"] = context_index.get("indexedAt") or now
    graph["signature"] = signature
    state["knowledge_graph"] = graph
    state["updated_at"] = now
    return True


def payload(state: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    graph = state.get("knowledge_graph", {})
    unseen = set(graph.get("unseen_ids", []))
    nodes = []
    for row in rows:
        ident = node_id(row)
        nodes.append({
            "id": ident, "term": row["term"], "meaning": row["meaning"],
            "status": row["status"], "sourceType": row["sourceType"],
            "taskCount": row.get("taskCount", 0), "contextIds": row.get("contextIds", []),
            "primaryContextId": row.get("primaryContextId"),
            "contextLabels": row.get("contextLabels", []), "scenarioIds": row.get("scenarioIds", []),
            "scenarioLabels": row.get("scenarioLabels", []), "recentTitles": row.get("recentTitles", []),
            "isNew": ident in unseen,
            "firstSeenAt": graph.get("nodes", {}).get(ident, {}).get("first_seen_at"),
        })
    current = {node["id"] for node in nodes}
    edges = [edge for edge in graph.get("edges", {}).values() if edge["source"] in current and edge["target"] in current]
    return {
        "nodes": nodes, "edges": edges, "unseenCount": len(unseen),
        "lastAddedCount": len(graph.get("last_added_ids", [])),
        "lastAddedIds": graph.get("last_added_ids", []),
        "lastScanAt": graph.get("last_scan_at"),
        "suggestedCount": sum(edge["status"] == "suggested" for edge in edges),
    }


def change_relation(state: dict[str, Any], edge_id: str, action: str, relation_type: str | None, now: str) -> None:
    graph = state.get("knowledge_graph", {})
    edge = graph.get("edges", {}).get(edge_id)
    if not edge:
        raise store.StoreError("未知的词汇关系")
    if action not in {"accept", "ignore", "change_type"}:
        raise store.StoreError("不支持的关系操作")
    if action == "change_type" and relation_type not in RELATION_TYPES:
        raise store.StoreError("不支持的关系类型")
    if action == "change_type":
        edge["type"] = relation_type
        edge["status"] = "confirmed"
        edge["reason"] = "关系类型由学习者调整。"
        edge["confidence"] = 1.0
    else:
        edge["status"] = "confirmed" if action == "accept" else "ignored"
    edge["decided_at"] = now
    state["updated_at"] = now


def mark_seen(state: dict[str, Any], node_ids: list[str] | None, now: str) -> None:
    graph = state.get("knowledge_graph", {})
    unseen = set(graph.get("unseen_ids", []))
    if node_ids is None:
        unseen.clear()
    else:
        unseen -= set(node_ids)
    graph["unseen_ids"] = sorted(unseen)
    state["updated_at"] = now
