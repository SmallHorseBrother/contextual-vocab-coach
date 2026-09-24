"""Local intake for people who do not use Codex.

Only derived vocabulary IDs, topic IDs, counts, and timestamps are persisted;
the pasted or dictated source text is not written to disk.
"""

from __future__ import annotations

import re
from typing import Any

import codex_context
import vocab_store as store


TARGET_SIZES = (500, 1000, 2500)
ENGLISH_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
CHINESE = re.compile(r"[\u3400-\u9fff]")
SPLIT_MEANING = re.compile(r"[；;，,、/（）()…·]+")


def target_size(state: dict[str, Any]) -> int:
    chosen = state.get("profile", {}).get("vocabulary_target", 500)
    return chosen if chosen in TARGET_SIZES else 500


def set_target(state: dict[str, Any], amount: int, now: str) -> None:
    if amount not in TARGET_SIZES:
        raise store.StoreError("词表档位必须为 500、1000 或 2500")
    state["profile"]["vocabulary_target"] = amount
    state["updated_at"] = now
    store.add_event(state, now, "vocabulary_target_changed", target=amount)


def _matches(text: str, lexicon: dict[str, dict[str, Any]]) -> list[str]:
    folded = text.casefold()
    english = set(ENGLISH_WORD.findall(folded))
    hits = []
    for ident, row in lexicon.items():
        term = row["term"].casefold()
        if (term in english if " " not in term else bool(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", folded))):
            hits.append(ident)
            continue
        fragments = (part.strip() for part in SPLIT_MEANING.split(row["meaning"]))
        if any(2 <= len(part) <= 8 and CHINESE.search(part) and part in text for part in fragments):
            hits.append(ident)
    return hits


def _seed_topic_candidates(state: dict[str, Any], topic_id: str, source_id: str, now: str) -> None:
    if topic_id == "general":
        return
    topic = codex_context.TOPIC_BY_ID[topic_id]
    for index, (term, meaning, kind, rationale) in enumerate(topic["vocabulary"]):
        ident = store.stable_id("item", term, meaning)
        existing = state["candidates"].get(ident)
        if existing:
            existing["source_ids"] = list(dict.fromkeys([*existing["source_ids"], source_id]))
            continue
        state["candidates"][ident] = {
            "id": ident, "term": term, "meaning": meaning, "kind": kind,
            "rationale": f"{rationale}；与你导入的内容相关",
            "target_modes": ["production", "recognition"], "source_ids": [source_id],
            "goal_ids": [], "priority": 5 if index < 3 else 4,
            "evidence_summary": "user-provided context topic",
            "suggested_anchor": "在你刚刚描述的真实情境中自然使用这个表达。",
            "contrast": "", "status": "proposed", "topic_id": topic_id,
            "created_at": now, "updated_at": now,
        }


def append_context(state: dict[str, Any], *, label: str, text: str, now: str) -> dict[str, Any]:
    label = label.strip() or "我的工作与生活"
    text = text.strip()
    if not 2 <= len(label) <= 80:
        raise store.StoreError("上下文名称需要 2–80 个字符")
    if not 20 <= len(text) <= 12000:
        raise store.StoreError("每次输入 20–12000 个字符；可以分多次继续添加")
    source_id = store.stable_id("personal-context", label)
    topic_id, _ = codex_context.classify(text, title=label)
    hits = _matches(text, state["lexicon"])
    context_map = state.setdefault("personal_contexts", {})
    record = context_map.setdefault(source_id, {
        "id": source_id, "label": label, "created_at": now,
        "segments": [], "total_chars": 0, "last_added_at": now,
    })
    record["segments"].append({
        "at": now, "characters": len(text), "topic_id": topic_id,
        "lexicon_ids": hits,
    })
    record["total_chars"] += len(text)
    record["last_added_at"] = now
    topics = {segment["topic_id"] for segment in record["segments"]}
    existing_source = state["sources"].get(source_id, {})
    state["sources"][source_id] = {
        "id": source_id, "label": label, "kind": "user_supplied_context",
        "locator": "local workbench input", "authorized": True,
        "retain_raw": False, "status": existing_source.get("status", "active"),
        "summary": f"你已添加 {len(record['segments'])} 段内容；原文不保存。",
        "focus_points": [], "topic_ids": sorted(topics),
        "added_at": existing_source.get("added_at", now), "updated_at": now,
    }
    _seed_topic_candidates(state, topic_id, source_id, now)
    state["updated_at"] = now
    store.add_event(state, now, "personal_context_appended", source_id=source_id, chars=len(text), matched=len(hits))
    return {"sourceId": source_id, "topicId": topic_id, "matchedCount": len(hits), "segmentCount": len(record["segments"])}


def active_hit_counts(state: dict[str, Any]) -> tuple[dict[str, int], dict[str, int]]:
    lexicon_hits: dict[str, int] = {}
    topic_hits: dict[str, int] = {}
    for source_id, record in state.get("personal_contexts", {}).items():
        if state["sources"].get(source_id, {}).get("status") != "active":
            continue
        for segment in record.get("segments", []):
            topic_id = segment.get("topic_id", "general")
            topic_hits[topic_id] = topic_hits.get(topic_id, 0) + 1
            for ident in segment.get("lexicon_ids", []):
                lexicon_hits[ident] = lexicon_hits.get(ident, 0) + 1
    return lexicon_hits, topic_hits


def payload(state: dict[str, Any]) -> dict[str, Any]:
    lexicon_hits, topic_hits = active_hit_counts(state)
    sources = []
    for source_id, record in state.get("personal_contexts", {}).items():
        source = state["sources"].get(source_id, {})
        sources.append({
            "id": source_id, "label": record["label"], "status": source.get("status", "active"),
            "segmentCount": len(record.get("segments", [])), "characterCount": record.get("total_chars", 0),
            "lastAddedAt": record.get("last_added_at"),
            "topicLabels": sorted({codex_context.TOPIC_BY_ID.get(segment.get("topic_id"), codex_context.TOPIC_BY_ID["general"])["label"] for segment in record.get("segments", [])}),
            "matchedCount": len({ident for segment in record.get("segments", []) for ident in segment.get("lexicon_ids", [])}),
        })
    return {
        "targetSize": target_size(state), "targetOptions": list(TARGET_SIZES),
        "sources": sorted(sources, key=lambda row: row["lastAddedAt"] or "", reverse=True),
        "totalSegments": sum(row["segmentCount"] for row in sources),
        "matchedLexiconCount": len(lexicon_hits), "topicHits": topic_hits,
        "rawContentStored": False,
    }
