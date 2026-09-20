#!/usr/bin/env python3
"""Local persistence and review scheduling for contextual-vocab-coach.

The language model decides what is relevant and designs the learning activity.
This module owns the deterministic parts: durable decisions, source lineage,
per-mode review tracks, privacy operations, and an SM-2-style baseline.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
VALID_MODES = {"recognition", "production", "listening"}
VALID_KINDS = {"word", "phrase", "collocation", "sentence_frame"}
VALID_DECISIONS = {"proposed", "test", "learning", "known", "not_now"}
VALID_FEEDBACK = {"again", "hard", "good", "easy"}
VALID_SOURCE_STATUS = {"active", "paused"}
FEEDBACK_QUALITY = {"again": 1, "hard": 3, "good": 4, "easy": 5}


class StoreError(RuntimeError):
    pass


def iso_now(value: str | None = None) -> str:
    if value:
        parsed = parse_time(value)
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StoreError(f"Invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"\s+", " ", value)


def stable_id(prefix: str, *parts: str) -> str:
    raw = "\0".join(normalize(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def default_store_path() -> Path:
    override = os.environ.get("CONTEXTUAL_VOCAB_HOME")
    if override:
        base = Path(override).expanduser()
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "contextual-vocab-coach"
    elif os.environ.get("XDG_DATA_HOME"):
        base = Path(os.environ["XDG_DATA_HOME"]) / "contextual-vocab-coach"
    else:
        base = Path.home() / ".local" / "share" / "contextual-vocab-coach"
    return base / "state.json"


def resolve_store_path(raw: str | None) -> Path:
    if not raw:
        return default_store_path()
    path = Path(raw).expanduser().resolve()
    if path.suffix.lower() != ".json":
        path = path / "state.json"
    return path


def empty_state(now: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "profile": {
            "active_goal_id": None,
            "familiar_contexts": [],
            "preferences": {"daily_minutes": 10, "explanation_language": "auto"},
            "exclusions": [],
        },
        "goals": {},
        "sources": {},
        "candidates": {},
        "learning_items": {},
        "reviews": [],
        "events": [],
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise StoreError(f"No learning store at {path}. Run `init` first.")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(f"Cannot read learning store at {path}: {exc}") from exc
    errors = state_errors(state)
    if errors:
        raise StoreError("Invalid learning store: " + "; ".join(errors))
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def add_event(state: dict[str, Any], now: str, event_type: str, **details: Any) -> None:
    state["events"].append({"at": now, "type": event_type, "details": details})
    if len(state["events"]) > 2000:
        state["events"] = state["events"][-2000:]


def require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StoreError(f"{name} must be a non-empty string")
    return value.strip()


def string_list(value: Any, name: str, *, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise StoreError(f"{name} must be a list of non-empty strings")
    result = list(dict.fromkeys(item.strip() for item in value))
    if allowed is not None:
        invalid = set(result) - allowed
        if invalid:
            raise StoreError(f"{name} contains unsupported values: {sorted(invalid)}")
    return result


def read_json_input(value: str) -> dict[str, Any]:
    try:
        if value == "-":
            payload = json.load(sys.stdin)
        else:
            payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StoreError(f"Cannot read JSON input {value}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StoreError("Pack must be a JSON object")
    return payload


def validate_pack(pack: dict[str, Any], state: dict[str, Any]) -> None:
    profile = pack.get("profile", {})
    if not isinstance(profile, dict):
        raise StoreError("profile must be an object")
    goal = profile.get("goal")
    if goal is not None:
        if not isinstance(goal, dict):
            raise StoreError("profile.goal must be an object")
        require_text(goal.get("statement"), "profile.goal.statement")
        require_text(goal.get("success_definition"), "profile.goal.success_definition")
        string_list(goal.get("focus_modes"), "profile.goal.focus_modes", allowed=VALID_MODES)
        if not isinstance(goal.get("confirmed"), bool):
            raise StoreError("profile.goal.confirmed must be true or false")

    contexts = profile.get("familiar_contexts", [])
    if not isinstance(contexts, list):
        raise StoreError("profile.familiar_contexts must be a list")
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            raise StoreError(f"profile.familiar_contexts[{index}] must be an object")
        require_text(context.get("label"), f"profile.familiar_contexts[{index}].label")
        if context.get("confidence") not in {"confirmed", "inferred"}:
            raise StoreError(f"profile.familiar_contexts[{index}].confidence must be confirmed or inferred")
        string_list(context.get("source_ids", []), f"profile.familiar_contexts[{index}].source_ids")

    if "preferences" in profile and not isinstance(profile["preferences"], dict):
        raise StoreError("profile.preferences must be an object")
    if "exclusions" in profile:
        string_list(profile["exclusions"], "profile.exclusions")

    sources = pack.get("sources", [])
    if not isinstance(sources, list):
        raise StoreError("sources must be a list")
    source_ids = set(state["sources"])
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise StoreError(f"sources[{index}] must be an object")
        source_id = require_text(source.get("source_id"), f"sources[{index}].source_id")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", source_id):
            raise StoreError(f"sources[{index}].source_id contains unsupported characters")
        require_text(source.get("label"), f"sources[{index}].label")
        require_text(source.get("kind"), f"sources[{index}].kind")
        if source.get("authorized") is not True:
            raise StoreError(f"sources[{index}] is not explicitly authorized")
        if source.get("retain_raw", False) not in {True, False}:
            raise StoreError(f"sources[{index}].retain_raw must be true or false")
        if source.get("status", "active") not in VALID_SOURCE_STATUS:
            raise StoreError(f"sources[{index}].status must be active or paused")
        source_ids.add(source_id)

    candidates = pack.get("candidates", [])
    if not isinstance(candidates, list):
        raise StoreError("candidates must be a list")
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise StoreError(f"candidates[{index}] must be an object")
        require_text(candidate.get("term"), f"candidates[{index}].term")
        require_text(candidate.get("meaning"), f"candidates[{index}].meaning")
        if candidate.get("kind") not in VALID_KINDS:
            raise StoreError(f"candidates[{index}].kind must be one of {sorted(VALID_KINDS)}")
        require_text(candidate.get("rationale"), f"candidates[{index}].rationale")
        modes = string_list(candidate.get("target_modes"), f"candidates[{index}].target_modes", allowed=VALID_MODES)
        if not modes:
            raise StoreError(f"candidates[{index}].target_modes cannot be empty")
        references = string_list(candidate.get("source_ids"), f"candidates[{index}].source_ids")
        if not references:
            raise StoreError(f"candidates[{index}].source_ids cannot be empty")
        unknown = set(references) - source_ids
        if unknown:
            raise StoreError(f"candidates[{index}] references unknown sources: {sorted(unknown)}")
        priority = candidate.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or not 1 <= priority <= 5:
            raise StoreError(f"candidates[{index}].priority must be an integer from 1 to 5")


def merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    return list(dict.fromkeys([*existing, *incoming]))


def apply_pack(state: dict[str, Any], pack: dict[str, Any], now: str) -> dict[str, int]:
    validate_pack(pack, state)
    profile = pack.get("profile", {})
    result = {"sources_added": 0, "sources_updated": 0, "candidates_added": 0, "candidates_updated": 0}

    for incoming in pack.get("sources", []):
        source_id = incoming["source_id"]
        existing = state["sources"].get(source_id)
        clean = {
            "id": source_id,
            "label": incoming["label"].strip(),
            "kind": incoming["kind"].strip(),
            "locator": str(incoming.get("locator", "")).strip(),
            "fingerprint": str(incoming.get("fingerprint", "")).strip(),
            "authorized": True,
            "retain_raw": bool(incoming.get("retain_raw", False)),
            "summary": str(incoming.get("summary", "")).strip(),
            "status": incoming.get("status", "active"),
            "added_at": now if existing is None else existing["added_at"],
            "updated_at": now,
        }
        if existing is None:
            state["sources"][source_id] = clean
            result["sources_added"] += 1
        else:
            # A context import cannot silently reactivate a source the learner paused.
            if existing.get("status") == "paused":
                clean["status"] = "paused"
            state["sources"][source_id] = clean
            result["sources_updated"] += 1

    goal = profile.get("goal")
    if goal:
        goal_id = stable_id("goal", goal["statement"])
        existing_goal = state["goals"].get(goal_id, {})
        state["goals"][goal_id] = {
            "id": goal_id,
            "statement": goal["statement"].strip(),
            "success_definition": goal["success_definition"].strip(),
            "focus_modes": list(dict.fromkeys(goal["focus_modes"])),
            "confirmed": bool(goal["confirmed"]),
            "status": "active",
            "created_at": existing_goal.get("created_at", now),
            "updated_at": now,
        }
        previous_goal_id = state["profile"].get("active_goal_id")
        if previous_goal_id and previous_goal_id != goal_id and previous_goal_id in state["goals"]:
            state["goals"][previous_goal_id]["status"] = "inactive"
        state["profile"]["active_goal_id"] = goal_id

    known_sources = set(state["sources"])
    contexts_by_key = {normalize(item["label"]): item for item in state["profile"]["familiar_contexts"]}
    for incoming in profile.get("familiar_contexts", []):
        unknown = set(incoming.get("source_ids", [])) - known_sources
        if unknown:
            raise StoreError(f"Familiar context references unknown sources: {sorted(unknown)}")
        key = normalize(incoming["label"])
        existing = contexts_by_key.get(key)
        if existing:
            existing["source_ids"] = merge_unique(existing.get("source_ids", []), incoming.get("source_ids", []))
            if incoming["confidence"] == "confirmed":
                existing["confidence"] = "confirmed"
            existing["updated_at"] = now
        else:
            item = {
                "label": incoming["label"].strip(),
                "confidence": incoming["confidence"],
                "source_ids": list(dict.fromkeys(incoming.get("source_ids", []))),
                "created_at": now,
                "updated_at": now,
            }
            state["profile"]["familiar_contexts"].append(item)
            contexts_by_key[key] = item

    if "preferences" in profile:
        state["profile"]["preferences"].update(profile["preferences"])
    if "exclusions" in profile:
        state["profile"]["exclusions"] = merge_unique(
            state["profile"].get("exclusions", []), profile["exclusions"]
        )

    active_goal_id = state["profile"].get("active_goal_id")
    for incoming in pack.get("candidates", []):
        active_sources = [
            source_id
            for source_id in incoming["source_ids"]
            if state["sources"].get(source_id, {}).get("status") == "active"
        ]
        if not active_sources:
            raise StoreError(f"Candidate {incoming['term']!r} has no active authorized source")
        item_id = stable_id("item", incoming["term"], incoming["meaning"])
        existing = state["candidates"].get(item_id)
        if existing is None:
            state["candidates"][item_id] = {
                "id": item_id,
                "term": incoming["term"].strip(),
                "meaning": incoming["meaning"].strip(),
                "kind": incoming["kind"],
                "rationale": incoming["rationale"].strip(),
                "target_modes": list(dict.fromkeys(incoming["target_modes"])),
                "source_ids": list(dict.fromkeys(incoming["source_ids"])),
                "goal_ids": [active_goal_id] if active_goal_id else [],
                "priority": incoming["priority"],
                "evidence_summary": str(incoming.get("evidence_summary", "")).strip(),
                "suggested_anchor": str(incoming.get("anchor", "")).strip(),
                "contrast": str(incoming.get("contrast", "")).strip(),
                "status": "proposed",
                "created_at": now,
                "updated_at": now,
            }
            result["candidates_added"] += 1
        else:
            existing["source_ids"] = merge_unique(existing["source_ids"], incoming["source_ids"])
            if active_goal_id:
                existing["goal_ids"] = merge_unique(existing["goal_ids"], [active_goal_id])
            existing["target_modes"] = merge_unique(existing["target_modes"], incoming["target_modes"])
            if existing["status"] in {"proposed", "test"}:
                existing["rationale"] = incoming["rationale"].strip()
                existing["priority"] = max(existing["priority"], incoming["priority"])
                existing["evidence_summary"] = str(incoming.get("evidence_summary", "")).strip()
                existing["suggested_anchor"] = str(incoming.get("anchor", "")).strip()
                existing["contrast"] = str(incoming.get("contrast", "")).strip()
            existing["updated_at"] = now
            result["candidates_updated"] += 1

    state["updated_at"] = now
    add_event(state, now, "pack_applied", **result)
    return result


def resolve_item(state: dict[str, Any], value: str) -> tuple[str, dict[str, Any]]:
    if value in state["candidates"]:
        return value, state["candidates"][value]
    matches = [
        (item_id, candidate)
        for item_id, candidate in state["candidates"].items()
        if normalize(candidate["term"]) == normalize(value)
    ]
    if not matches:
        raise StoreError(f"Unknown item: {value}")
    if len(matches) > 1:
        choices = ", ".join(item_id for item_id, _ in matches)
        raise StoreError(f"Multiple senses match {value!r}; use an item ID: {choices}")
    return matches[0]


def new_track(now: str) -> dict[str, Any]:
    return {
        "ease_factor": 2.5,
        "repetitions": 0,
        "interval_days": 0,
        "due_at": now,
        "last_review_at": None,
        "last_feedback": None,
        "last_response_ms": None,
        "lapses": 0,
    }


def ensure_learning_item(state: dict[str, Any], candidate: dict[str, Any], now: str) -> dict[str, Any]:
    item_id = candidate["id"]
    existing = state["learning_items"].get(item_id)
    if existing is not None:
        existing["status"] = "active"
        for mode in candidate["target_modes"]:
            existing["tracks"].setdefault(mode, new_track(now))
        return existing
    item = {
        "id": item_id,
        "term": candidate["term"],
        "meaning": candidate["meaning"],
        "kind": candidate["kind"],
        "goal_ids": list(candidate["goal_ids"]),
        "source_ids": list(candidate["source_ids"]),
        "personal_anchor": candidate.get("suggested_anchor", ""),
        "contrast": candidate.get("contrast", ""),
        "tracks": {mode: new_track(now) for mode in candidate["target_modes"]},
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    state["learning_items"][item_id] = item
    return item


def update_track(track: dict[str, Any], feedback: str, now: str, response_ms: int | None) -> None:
    quality = FEEDBACK_QUALITY[feedback]
    ease = float(track.get("ease_factor", 2.5))
    repetitions = int(track.get("repetitions", 0))
    previous_interval = int(track.get("interval_days", 0))

    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    if quality < 3:
        repetitions = 0
        interval = 1
        track["lapses"] = int(track.get("lapses", 0)) + 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = max(1, round(previous_interval * ease))
        if feedback == "hard" and previous_interval:
            interval = max(1, round(previous_interval * 1.2))
        elif feedback == "easy":
            interval = max(interval, round(max(1, previous_interval) * ease * 1.3))
        repetitions += 1

    now_dt = parse_time(now)
    track.update(
        {
            "ease_factor": round(ease, 4),
            "repetitions": repetitions,
            "interval_days": interval,
            "due_at": (now_dt + timedelta(days=interval)).isoformat().replace("+00:00", "Z"),
            "last_review_at": now,
            "last_feedback": feedback,
            "last_response_ms": response_ms,
        }
    )


def status_payload(state: dict[str, Any], now: str) -> dict[str, Any]:
    now_dt = parse_time(now)
    candidate_counts = {status: 0 for status in sorted(VALID_DECISIONS)}
    for candidate in state["candidates"].values():
        candidate_counts[candidate["status"]] += 1
    due_tracks: list[dict[str, Any]] = []
    for item in state["learning_items"].values():
        if item.get("status") != "active":
            continue
        for mode, track in item["tracks"].items():
            if parse_time(track["due_at"]) <= now_dt:
                due_tracks.append(
                    {"item_id": item["id"], "term": item["term"], "meaning": item["meaning"], "mode": mode, "due_at": track["due_at"]}
                )
    due_tracks.sort(key=lambda row: (row["due_at"], row["term"], row["mode"]))
    goal_id = state["profile"].get("active_goal_id")
    mastery_items: list[dict[str, Any]] = []
    for candidate in state["candidates"].values():
        learning = state["learning_items"].get(candidate["id"])
        mode_states: list[str] = []
        next_due: str | None = None
        last_feedback: str | None = None
        last_review_at: datetime | None = None
        if learning:
            for mode, track in learning["tracks"].items():
                is_due = learning.get("status") == "active" and parse_time(track["due_at"]) <= now_dt
                mode_states.append(f"{mode}:{'due' if is_due else 'scheduled'}")
                if next_due is None or parse_time(track["due_at"]) < parse_time(next_due):
                    next_due = track["due_at"]
                reviewed_at = parse_time(track["last_review_at"]) if track.get("last_review_at") else None
                if reviewed_at is not None and (last_review_at is None or reviewed_at > last_review_at):
                    last_review_at = reviewed_at
                    last_feedback = track.get("last_feedback")

        if candidate["status"] == "known":
            display_status = "known"
        elif candidate["status"] == "not_now":
            display_status = "not now"
        elif candidate["status"] == "test":
            display_status = "needs test"
        elif candidate["status"] == "proposed":
            display_status = "candidate"
        elif learning and any(state.endswith(":due") for state in mode_states):
            display_status = "due"
        elif last_feedback in {"good", "easy"}:
            display_status = "recently passed"
        else:
            display_status = "learning"

        mastery_items.append(
            {
                "item_id": candidate["id"],
                "term": candidate["term"],
                "meaning": candidate["meaning"],
                "status": display_status,
                "modes": mode_states or candidate["target_modes"],
                "next_due": next_due,
                "priority": candidate["priority"],
                "on_active_goal": bool(goal_id and goal_id in candidate.get("goal_ids", [])),
            }
        )
    mastery_items.sort(
        key=lambda row: (
            not row["on_active_goal"],
            {"due": 0, "needs test": 1, "learning": 2, "candidate": 3, "recently passed": 4, "known": 5, "not now": 6}.get(
                row["status"], 9
            ),
            -row["priority"],
            row["term"].casefold(),
        )
    )
    return {
        "schema_version": state["schema_version"],
        "updated_at": state["updated_at"],
        "active_goal": state["goals"].get(goal_id) if goal_id else None,
        "candidate_counts": candidate_counts,
        "learning_item_count": len(state["learning_items"]),
        "review_count": len(state["reviews"]),
        "due_count": len(due_tracks),
        "due": due_tracks,
        "mastery_items": mastery_items,
        "sources": [
            {key: source[key] for key in ("id", "label", "kind", "status", "updated_at")}
            for source in sorted(state["sources"].values(), key=lambda item: item["label"].casefold())
        ],
    }


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(payload: dict[str, Any]) -> str:
    goal = payload["active_goal"]
    lines = ["# Vocabulary learning status", ""]
    if goal:
        lines.extend(
            [
                f"**Active goal:** {goal['statement']}",
                "",
                f"**Success means:** {goal['success_definition']}",
                "",
            ]
        )
    else:
        lines.extend(["**Active goal:** Not set", ""])
    counts = payload["candidate_counts"]
    lines.extend(
        [
            f"Candidates: {counts['proposed']} proposed · {counts['test']} to test · {counts['learning']} learning · {counts['known']} known · {counts['not_now']} not now",
            "",
            f"Due now: {payload['due_count']} · Reviews recorded: {payload['review_count']}",
            "",
            "## Due items",
            "",
        ]
    )
    if payload["due"]:
        lines.extend(["| Item | Meaning | Mode | Due |", "|---|---|---|---|"])
        for row in payload["due"][:20]:
            lines.append(
                f"| {markdown_escape(row['term'])} | {markdown_escape(row['meaning'])} | {row['mode']} | {row['due_at']} |"
            )
    else:
        lines.append("Nothing is due.")
    lines.extend(["", "## Task-to-vocabulary mastery", ""])
    if payload["mastery_items"]:
        lines.extend(["| Expression | Meaning | Status | Modes / next due |", "|---|---|---|---|"])
        for row in payload["mastery_items"][:30]:
            modes = ", ".join(row["modes"])
            schedule = f"{modes} · {row['next_due']}" if row["next_due"] else modes
            lines.append(
                f"| {markdown_escape(row['term'])} | {markdown_escape(row['meaning'])} | {row['status']} | {markdown_escape(schedule)} |"
            )
    else:
        lines.append("No vocabulary items yet.")
    lines.extend(["", "## Sources", ""])
    if payload["sources"]:
        lines.extend(["| Source | Kind | Status |", "|---|---|---|"])
        for source in payload["sources"]:
            lines.append(f"| {markdown_escape(source['label'])} | {source['kind']} | {source['status']} |")
    else:
        lines.append("No sources stored.")
    return "\n".join(lines) + "\n"


def state_errors(state: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["root is not an object"]
    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("profile", "goals", "sources", "candidates", "learning_items"):
        if not isinstance(state.get(key), dict):
            errors.append(f"{key} must be an object")
    for key in ("reviews", "events"):
        if not isinstance(state.get(key), list):
            errors.append(f"{key} must be a list")
    if errors:
        return errors
    goal_id = state["profile"].get("active_goal_id")
    if goal_id is not None and goal_id not in state["goals"]:
        errors.append("active_goal_id does not exist")
    for source_id, source in state["sources"].items():
        if source.get("id") != source_id:
            errors.append(f"source key mismatch: {source_id}")
        if source.get("status") not in VALID_SOURCE_STATUS:
            errors.append(f"source {source_id} has invalid status")
    for item_id, candidate in state["candidates"].items():
        if candidate.get("id") != item_id:
            errors.append(f"candidate key mismatch: {item_id}")
        if candidate.get("status") not in VALID_DECISIONS:
            errors.append(f"candidate {item_id} has invalid status")
        unknown_sources = set(candidate.get("source_ids", [])) - set(state["sources"])
        if unknown_sources:
            errors.append(f"candidate {item_id} references missing sources {sorted(unknown_sources)}")
    for item_id, item in state["learning_items"].items():
        if item.get("id") != item_id:
            errors.append(f"learning item key mismatch: {item_id}")
        if not isinstance(item.get("tracks"), dict):
            errors.append(f"learning item {item_id} has invalid tracks")
            continue
        for mode, track in item["tracks"].items():
            if mode not in VALID_MODES:
                errors.append(f"learning item {item_id} has invalid mode {mode}")
            try:
                parse_time(track.get("due_at", ""))
            except StoreError:
                errors.append(f"learning item {item_id}/{mode} has invalid due_at")
    return errors


def command_init(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    if path.exists():
        state = load_state(path)
        return {"created": False, "store": str(path), "status": status_payload(state, now)}
    state = empty_state(now)
    if args.goal:
        focus_modes = args.focus_modes or ["recognition", "production"]
        goal_id = stable_id("goal", args.goal)
        state["goals"][goal_id] = {
            "id": goal_id,
            "statement": args.goal.strip(),
            "success_definition": (args.success_definition or args.goal).strip(),
            "focus_modes": focus_modes,
            "confirmed": bool(args.confirmed),
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        state["profile"]["active_goal_id"] = goal_id
    add_event(state, now, "store_initialized")
    save_state(path, state)
    return {"created": True, "store": str(path), "status": status_payload(state, now)}


def command_apply_pack(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    working = copy.deepcopy(state)
    pack = read_json_input(args.input)
    result = apply_pack(working, pack, now)
    errors = state_errors(working)
    if errors:
        raise StoreError("Pack produced an invalid state: " + "; ".join(errors))
    if not args.dry_run:
        save_state(path, working)
    return {"dry_run": bool(args.dry_run), "changes": result, "status": status_payload(working, now)}


def command_decide(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    item_id, candidate = resolve_item(state, args.item)
    decision = args.decision
    candidate["status"] = decision
    candidate["updated_at"] = now
    if decision in {"learning", "test"}:
        if decision == "learning":
            ensure_learning_item(state, candidate, now)
    elif item_id in state["learning_items"]:
        state["learning_items"][item_id]["status"] = "known" if decision == "known" else "paused"
        state["learning_items"][item_id]["updated_at"] = now
    state["updated_at"] = now
    add_event(state, now, "candidate_decided", item_id=item_id, decision=decision)
    save_state(path, state)
    return {"item_id": item_id, "term": candidate["term"], "decision": decision}


def command_due(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    payload = status_payload(state, now)
    diagnostics = [
        {
            "item_id": candidate["id"],
            "term": candidate["term"],
            "meaning": candidate["meaning"],
            "target_modes": candidate["target_modes"],
            "rationale": candidate["rationale"],
            "kind": "diagnostic",
        }
        for candidate in sorted(
            state["candidates"].values(), key=lambda item: (-item["priority"], item["term"].casefold())
        )
        if candidate["status"] == "test"
    ]
    due = [{**row, "kind": "review"} for row in payload["due"]]
    return {"now": now, "items": (due + diagnostics)[: args.limit], "total_due": len(due), "total_diagnostics": len(diagnostics)}


def command_review(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    item_id, candidate = resolve_item(state, args.item)
    if args.mode not in candidate["target_modes"]:
        candidate["target_modes"].append(args.mode)
    candidate["status"] = "learning"
    candidate["updated_at"] = now
    item = ensure_learning_item(state, candidate, now)
    track = item["tracks"].setdefault(args.mode, new_track(now))
    update_track(track, args.feedback, now, args.response_ms)
    item["updated_at"] = now
    review = {
        "id": stable_id("review", item_id, args.mode, now, str(len(state["reviews"]))),
        "item_id": item_id,
        "mode": args.mode,
        "feedback": args.feedback,
        "response_ms": args.response_ms,
        "strategy": args.strategy,
        "personalized": bool(args.personalized),
        "transfer_test": bool(args.transfer_test),
        "context_note": args.context_note or "",
        "reviewed_at": now,
        "scheduled_due_at": track["due_at"],
    }
    state["reviews"].append(review)
    state["updated_at"] = now
    add_event(state, now, "review_recorded", item_id=item_id, mode=args.mode, feedback=args.feedback)
    save_state(path, state)
    return {"review": review, "track": track}


def command_source_status(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    source = state["sources"].get(args.source_id)
    if source is None:
        raise StoreError(f"Unknown source: {args.source_id}")
    source["status"] = args.status
    source["updated_at"] = now
    state["updated_at"] = now
    add_event(state, now, "source_status_changed", source_id=args.source_id, status=args.status)
    save_state(path, state)
    return {"source_id": args.source_id, "status": args.status}


def command_source_delete(args: argparse.Namespace, path: Path, now: str) -> dict[str, Any]:
    state = load_state(path)
    if args.source_id not in state["sources"]:
        raise StoreError(f"Unknown source: {args.source_id}")
    del state["sources"][args.source_id]
    removed_candidates: list[str] = []
    removed_learning_items: list[str] = []

    filtered_contexts = []
    for context in state["profile"]["familiar_contexts"]:
        had_source = args.source_id in context.get("source_ids", [])
        context["source_ids"] = [source for source in context.get("source_ids", []) if source != args.source_id]
        if had_source and not context["source_ids"] and context.get("confidence") == "inferred":
            continue
        filtered_contexts.append(context)
    state["profile"]["familiar_contexts"] = filtered_contexts

    for item_id, candidate in list(state["candidates"].items()):
        had_source = args.source_id in candidate.get("source_ids", [])
        if not had_source:
            continue
        candidate["source_ids"] = [source for source in candidate["source_ids"] if source != args.source_id]
        candidate["suggested_anchor"] = ""
        candidate["evidence_summary"] = ""
        only_support_removed = not candidate["source_ids"]
        should_remove = only_support_removed and (
            args.mode == "purge" or candidate["status"] in {"proposed", "test", "not_now"}
        )
        if should_remove:
            removed_candidates.append(item_id)
            del state["candidates"][item_id]

    for item_id, item in list(state["learning_items"].items()):
        had_source = args.source_id in item.get("source_ids", [])
        if not had_source:
            continue
        item["source_ids"] = [source for source in item["source_ids"] if source != args.source_id]
        item["personal_anchor"] = ""
        if args.mode == "purge" and not item["source_ids"]:
            removed_learning_items.append(item_id)
            del state["learning_items"][item_id]

    removed_ids = set(removed_candidates) | set(removed_learning_items)
    if args.mode == "purge" and removed_ids:
        state["reviews"] = [review for review in state["reviews"] if review.get("item_id") not in removed_ids]

    state["updated_at"] = now
    add_event(
        state,
        now,
        "source_deleted",
        source_id=args.source_id,
        mode=args.mode,
        removed_candidates=removed_candidates,
        removed_learning_items=removed_learning_items,
    )
    errors = state_errors(state)
    if errors:
        raise StoreError("Source deletion produced invalid state: " + "; ".join(errors))
    save_state(path, state)
    return {
        "source_id": args.source_id,
        "mode": args.mode,
        "removed_candidates": removed_candidates,
        "removed_learning_items": removed_learning_items,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", help="State JSON file or directory")
    parser.add_argument("--now", help="Override current time with an ISO timestamp (useful for tests)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create a local learning store")
    init.add_argument("--goal")
    init.add_argument("--success-definition")
    init.add_argument("--focus-modes", nargs="+", choices=sorted(VALID_MODES))
    init.add_argument("--confirmed", action="store_true")

    apply_parser = subparsers.add_parser("apply-pack", help="Validate and merge a context/candidate pack")
    apply_parser.add_argument("--input", required=True, help="JSON path or - for stdin")
    apply_parser.add_argument("--dry-run", action="store_true")

    decide = subparsers.add_parser("decide", help="Record the learner's decision about a candidate")
    decide.add_argument("--item", required=True, help="Item ID or exact term")
    decide.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS - {"proposed"}))

    due = subparsers.add_parser("due", help="List due reviews and diagnostic candidates")
    due.add_argument("--limit", type=int, default=5)

    review = subparsers.add_parser("review", help="Record an observed retrieval result")
    review.add_argument("--item", required=True, help="Item ID or exact term")
    review.add_argument("--mode", required=True, choices=sorted(VALID_MODES))
    review.add_argument("--feedback", required=True, choices=sorted(VALID_FEEDBACK))
    review.add_argument("--response-ms", type=int)
    review.add_argument("--strategy", default="unspecified")
    review.add_argument("--personalized", action="store_true")
    review.add_argument("--transfer-test", action="store_true")
    review.add_argument("--context-note")

    status = subparsers.add_parser("status", help="Show the learning record")
    status.add_argument("--format", choices=("json", "markdown"), default="json")

    source_status = subparsers.add_parser("source-status", help="Pause or reactivate a source")
    source_status.add_argument("--source-id", required=True)
    source_status.add_argument("--status", required=True, choices=sorted(VALID_SOURCE_STATUS))

    source_delete = subparsers.add_parser("source-delete", help="Delete source metadata or purge its derived learning data")
    source_delete.add_argument("--source-id", required=True)
    source_delete.add_argument("--mode", required=True, choices=("metadata", "purge"))

    subparsers.add_parser("doctor", help="Validate state invariants")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = resolve_store_path(args.store)
    now = iso_now(args.now)
    try:
        if args.command == "init":
            output: Any = command_init(args, path, now)
        elif args.command == "apply-pack":
            output = command_apply_pack(args, path, now)
        elif args.command == "decide":
            output = command_decide(args, path, now)
        elif args.command == "due":
            output = command_due(args, path, now)
        elif args.command == "review":
            output = command_review(args, path, now)
        elif args.command == "status":
            state = load_state(path)
            payload = status_payload(state, now)
            if args.format == "markdown":
                sys.stdout.write(render_markdown(payload))
                return 0
            output = payload
        elif args.command == "source-status":
            output = command_source_status(args, path, now)
        elif args.command == "source-delete":
            output = command_source_delete(args, path, now)
        elif args.command == "doctor":
            state = load_state(path)
            errors = state_errors(state)
            output = {"ok": not errors, "store": str(path), "errors": errors}
            if errors:
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 1
        else:
            raise StoreError(f"Unsupported command: {args.command}")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except StoreError as exc:
        print(json.dumps({"error": str(exc), "store": str(path)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
