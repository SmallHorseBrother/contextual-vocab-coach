#!/usr/bin/env python3
"""Build a compact, offline English-Chinese reservoir from ECDICT.

The input is intentionally not checked in. The generated selection and the
upstream MIT notice are distributed with the skill. Run with an ECDICT CSV
downloaded from the pinned source documented in README.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORD = re.compile(r"[a-z][a-z-]{1,25}\Z")
HAN = re.compile(r"[\u3400-\u9fff]")
POS = re.compile(r"^(?:n|v|vi|vt|adj|adv|a|prep|pron|conj|interj|aux|num|art)\.\s*", re.I)
COMMON_OVERRIDES = {
    "the": "这；那（定冠词）", "be": "是；存在", "can": "能；可以", "will": "会；将要",
    "would": "会；愿意", "could": "能够；可以", "a": "一个（不定冠词）",
    "it": "它", "that": "那；那个", "this": "这；这个", "his": "他的", "her": "她的；她",
    "as": "作为；如同", "what": "什么", "one": "一；一个", "may": "可能；可以",
    "must": "必须", "should": "应该", "shall": "将；应当", "might": "可能",
}


def translation(raw: str) -> str:
    for line in raw.replace("\\r", "\n").replace("\\n", "\n").splitlines():
        line = line.strip()
        if not line or line.startswith("["):
            continue
        line = POS.sub("", line)
        fragments = [part.strip(" .;；，,") for part in re.split(r"[；;,，]", line)]
        chosen = [part for part in fragments if HAN.search(part) and len(part) <= 20][:2]
        if chosen:
            return "；".join(chosen)[:50]
    return ""


def build(source: Path, count: int = 3200) -> dict:
    starter = json.loads((ROOT / "data" / "starter-lexicon.json").read_text(encoding="utf-8"))
    existing = {row["term"].casefold() for row in starter["entries"]}
    ranked: list[tuple[int, int, str, str]] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            word = row["word"].strip()
            if not WORD.fullmatch(word) or word in existing or "-" in word:
                continue
            try:
                frq, bnc = int(row["frq"]), int(row["bnc"])
            except (TypeError, ValueError):
                continue
            if not 1 <= frq <= 25000:
                continue
            meaning = COMMON_OVERRIDES.get(word) or translation(row["translation"])
            if not meaning:
                continue
            ranked.append((frq, bnc if bnc > 0 else 999999, word, meaning))
    ranked.sort()
    entries = []
    seen: set[str] = set()
    for frq, _bnc, word, meaning in ranked:
        if word in seen:
            continue
        seen.add(word)
        position = len(entries) + 1
        ident = "ecd_" + hashlib.sha256(word.encode("utf-8")).hexdigest()[:12]
        entries.append({
            "id": ident, "term": word, "meaning": meaning, "kind": "word",
            "level": "A1" if position <= 500 else "A2" if position <= 1700 else "B1",
            "scenario_ids": ["core-expanded"], "target_modes": ["recognition", "production"],
            "frequency_rank": frq,
        })
        if len(entries) == count:
            break
    if len(entries) < count:
        raise ValueError(f"Only {len(entries)} usable entries; expected {count}")
    return {
        "version": 1,
        "title": "高频英语扩展词库",
        "description": "按语料词频筛选的英汉词；词义和级别仅供推荐与核对。",
        "language_pair": "en-zh-CN",
        "source": "ECDICT (MIT), https://github.com/skywind3000/ECDICT",
        "scenarios": [{"id": "core-expanded", "label": "通用高频英语", "description": "为较大词表档位提供细化的通用词"}],
        "entries": entries,
        "entry_count": len(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True, help="ECDICT CSV downloaded locally")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "expanded-lexicon.json")
    args = parser.parse_args()
    payload = build(args.source)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {payload['entry_count']} additional words to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
