#!/usr/bin/env python3
"""Build a transparent, local-only context index from Codex task history.

The scanner intentionally separates complete task-metadata coverage from bounded
message inspection.  It indexes every task title available in
``session_index.jsonl`` and every rollout identifier found on disk, then reads a
small head/tail window from the most recent rollouts.  Raw conversation text is
never written to the vocabulary store.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import vocab_store as store


ROLLOUT_ID = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.IGNORECASE)
SEGMENT_BYTES = 384 * 1024


TOPICS: tuple[dict[str, Any], ...] = (
    {
        "id": "embodied-ai",
        "label": "具身智能与机器人",
        "goal": "用英语讲清具身智能比赛与机器人方案",
        "success": "能介绍比赛任务、感知与抓取方案、实验结果和下一步改进",
        "keywords": (
            "具身", "机器人", "机械臂", "抓取", "夹爪", "灵巧", "操作", "强化学习",
            "仿真", "小球", "开箱", "有盖", "无盖", "x2", "grasp", "robot", "manipulation",
            "embodied", "sim-to-real", "competition", "大赛", "比赛",
        ),
        "vocabulary": (
            ("embodied intelligence", "具身智能", "phrase", "解释比赛所属的技术方向"),
            ("robotic manipulation", "机器人操作；机械臂操作", "phrase", "描述机械臂完成抓取和放置任务"),
            ("grasping strategy", "抓取策略", "collocation", "说明系统如何选择抓取点和动作"),
            ("end effector", "末端执行器", "phrase", "介绍夹爪等机械臂末端部件"),
            ("sim-to-real transfer", "从仿真到现实的迁移", "phrase", "讨论仿真训练如何迁移到真实机器人"),
            ("failure recovery", "失败恢复", "collocation", "解释抓取失败后如何自动重试或调整"),
            ("task completion rate", "任务完成率", "collocation", "用可量化指标汇报比赛表现"),
            ("under real-world constraints", "在真实世界约束下", "sentence_frame", "强调噪声、遮挡和硬件限制"),
        ),
    },
    {
        "id": "food-health",
        "label": "FoodLink 与健康饮食产品",
        "goal": "用英语介绍健康饮食产品与核心能力",
        "success": "能清晰说明用户问题、识别能力、健康建议和产品价值",
        "keywords": (
            "foodlink", "食探", "食物", "饮食", "营养", "过敏原", "葡萄", "热量", "卡路里",
            "健康", "膳食", "餐", "运动消耗", "food", "nutrition", "diet", "allergen", "calorie", "portion",
        ),
        "vocabulary": (
            ("dietary preferences", "饮食偏好", "phrase", "说明个性化饮食建议的输入"),
            ("allergen screening", "过敏原筛查", "collocation", "介绍产品的安全筛查能力"),
            ("estimate portion sizes", "估算食物分量", "phrase", "解释图像识别后的分量估计"),
            ("nutritional intake", "营养摄入", "collocation", "描述用户需要理解和管理的数据"),
            ("personalized recommendation", "个性化建议", "collocation", "说明产品如何针对不同用户给出方案"),
            ("energy expenditure", "能量消耗", "collocation", "连接运动消耗与饮食建议"),
            ("food recognition pipeline", "食物识别流程", "phrase", "介绍从图片到识别结果的技术链路"),
            ("make healthier choices", "做出更健康的选择", "phrase", "概括产品给用户带来的结果"),
        ),
    },
    {
        "id": "ai-research",
        "label": "AI 研究、论文与模型评测",
        "goal": "用英语讨论 AI 论文、模型和实验结论",
        "success": "能概括研究问题、实验设置、指标、局限和结论",
        "keywords": (
            "论文", "acl", "模型", "评测", "seed", "训练", "推理", "数据集", "微调", "大模型",
            "paper", "model", "benchmark", "evaluation", "inference", "dataset", "fine-tun", "llm",
        ),
        "vocabulary": (
            ("evaluation benchmark", "评测基准", "collocation", "说明不同模型如何被统一比较"),
            ("experimental setup", "实验设置", "collocation", "介绍数据、模型和测试条件"),
            ("ablation study", "消融实验", "collocation", "解释各组件对结果的贡献"),
            ("baseline model", "基线模型", "collocation", "描述实验中的比较对象"),
            ("performance gap", "性能差距", "collocation", "比较不同模型或设置的结果"),
            ("generalization ability", "泛化能力", "collocation", "讨论模型在新数据上的表现"),
            ("the results suggest that", "结果表明……", "sentence_frame", "自然引出实验结论"),
        ),
    },
    {
        "id": "product-building",
        "label": "产品构建与创业",
        "goal": "用英语讨论产品需求、路线图与用户价值",
        "success": "能说明用户问题、功能优先级、验证方法和商业价值",
        "keywords": (
            "产品", "需求", "用户", "路线图", "创业", "商业", "市场", "功能", "体验", "原型",
            "product", "roadmap", "user", "market", "startup", "feature", "prototype", "需求分析",
        ),
        "vocabulary": (
            ("user pain point", "用户痛点", "collocation", "明确产品正在解决的问题"),
            ("value proposition", "价值主张", "collocation", "概括产品为什么值得使用"),
            ("prioritize features", "确定功能优先级", "phrase", "讨论有限时间内先做什么"),
            ("validate the assumption", "验证假设", "phrase", "说明如何用用户反馈降低不确定性"),
            ("minimum viable product", "最小可行产品", "phrase", "界定首个可验证版本"),
            ("product-market fit", "产品市场匹配", "phrase", "讨论产品与真实需求的匹配程度"),
            ("iterate based on feedback", "根据反馈迭代", "phrase", "描述持续改进产品的过程"),
        ),
    },
    {
        "id": "content-creation",
        "label": "内容创作与传播",
        "goal": "用英语策划、制作并传播内容",
        "success": "能讨论选题、脚本、视觉素材、剪辑和发布策略",
        "keywords": (
            "视频", "小红书", "自媒体", "素材", "脚本", "剪映", "字幕", "推广", "ppt", "演示文稿",
            "content", "video", "caption", "subtitle", "presentation", "social media", "剪辑",
        ),
        "vocabulary": (
            ("content angle", "内容切入角度", "collocation", "讨论一条内容从什么角度展开"),
            ("target audience", "目标受众", "collocation", "明确内容主要讲给谁听"),
            ("key takeaway", "核心收获；关键信息", "collocation", "概括观众看完后应记住什么"),
            ("visual storytelling", "视觉叙事", "collocation", "说明画面如何帮助表达观点"),
            ("call to action", "行动号召", "phrase", "设计内容结尾希望观众采取的行动"),
            ("audience retention", "观众留存", "collocation", "讨论内容节奏与观看完成度"),
        ),
    },
    {
        "id": "engineering-ops",
        "label": "工程开发与基础设施",
        "goal": "用英语排查工程问题并解释技术方案",
        "success": "能描述现象、定位原因、比较方案并汇报修复结果",
        "keywords": (
            "ssh", "服务器", "部署", "脚本", "github", "接口", "api", "排查", "迁移", "修复", "调试",
            "代码", "仓库", "server", "deploy", "debug", "repository", "pipeline", "连接",
        ),
        "vocabulary": (
            ("root cause", "根本原因", "collocation", "概括问题真正发生在哪里"),
            ("reproduce the issue", "复现问题", "phrase", "说明定位故障的第一步"),
            ("deployment pipeline", "部署流水线", "collocation", "介绍代码从提交到上线的流程"),
            ("backward compatibility", "向后兼容性", "collocation", "评估修改对旧版本的影响"),
            ("temporary workaround", "临时解决办法", "collocation", "区分应急方案与最终修复"),
            ("roll back the change", "回滚更改", "phrase", "描述出现风险时的恢复手段"),
            ("the fix has been verified", "修复已经验证", "sentence_frame", "清楚汇报问题已经解决"),
        ),
    },
    {
        "id": "english-learning",
        "label": "英语学习系统",
        "goal": "用英语讨论语言学习方法与记忆设计",
        "success": "能说明上下文学习、主动回忆和间隔复习的设计逻辑",
        "keywords": (
            "英语", "单词", "词汇", "背单词", "学习 skill", "学习系统", "上下文驱动", "vocab",
            "上下文扫描", "english", "language learning", "flashcard", "spaced repetition", "contextual",
        ),
        "vocabulary": (
            ("active recall", "主动回忆", "collocation", "解释为什么先尝试回忆再看答案"),
            ("spaced repetition", "间隔重复", "collocation", "说明复习时间如何安排"),
            ("context-dependent memory", "情境依赖记忆", "phrase", "讨论上下文对记忆提取的影响"),
            ("productive vocabulary", "产出型词汇", "collocation", "区分能看懂与能主动使用"),
            ("retrieval practice", "提取练习", "collocation", "描述通过测试强化记忆的方法"),
            ("transfer to a new context", "迁移到新情境", "phrase", "检验是否真正掌握而非只记住例句"),
        ),
    },
    {
        "id": "general",
        "label": "其他工作与生活",
        "goal": "积累跨任务可复用的英语表达",
        "success": "能在新的工作与生活任务中自然使用通用表达",
        "keywords": (),
        "vocabulary": (
            ("clarify the goal", "澄清目标", "phrase", "在新任务开始时对齐预期"),
            ("break it down", "把它拆解开", "phrase", "把复杂任务分成可执行步骤"),
            ("make progress", "取得进展", "phrase", "汇报任务正在向前推进"),
            ("follow up on", "跟进……", "phrase", "继续处理尚未完成的事项"),
            ("from a practical perspective", "从实际角度看", "sentence_frame", "引出务实的判断或建议"),
        ),
    },
)

TOPIC_BY_ID = {topic["id"]: topic for topic in TOPICS}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def _parse_timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def read_session_index(codex_home: Path) -> dict[str, dict[str, Any]]:
    path = codex_home / "session_index.jsonl"
    records: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return records
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            task_id = str(row.get("id", "")).strip()
            title = str(row.get("thread_name", "")).strip()
            if not task_id:
                continue
            incoming = {"id": task_id, "title": title or "未命名任务", "updatedAt": _parse_timestamp(row.get("updated_at"))}
            previous = records.get(task_id)
            if previous is None or incoming["updatedAt"] >= previous["updatedAt"]:
                records[task_id] = incoming
    return records


def discover_rollouts(codex_home: Path) -> dict[str, Path]:
    rollouts: dict[str, Path] = {}
    for folder_name in ("sessions", "archived_sessions"):
        folder = codex_home / folder_name
        if not folder.is_dir():
            continue
        for path in folder.rglob("*.jsonl"):
            match = ROLLOUT_ID.search(path.name)
            if match is None:
                continue
            task_id = match.group(1).lower()
            previous = rollouts.get(task_id)
            if previous is None or path.stat().st_mtime >= previous.stat().st_mtime:
                rollouts[task_id] = path
    return rollouts


def _complete_lines(segment: bytes, *, drop_first: bool, drop_last: bool) -> list[bytes]:
    lines = segment.splitlines()
    if drop_first and lines:
        lines = lines[1:]
    if drop_last and lines:
        lines = lines[:-1]
    return lines


def read_recent_user_text(path: Path) -> tuple[str, int]:
    """Read bounded head/tail windows and return user text without persisting it."""
    size = path.stat().st_size
    with path.open("rb") as handle:
        head = handle.read(SEGMENT_BYTES)
        tail = b""
        if size > SEGMENT_BYTES:
            handle.seek(max(0, size - SEGMENT_BYTES))
            tail = handle.read(SEGMENT_BYTES)
    raw_lines = _complete_lines(head, drop_first=False, drop_last=size > SEGMENT_BYTES)
    if tail:
        raw_lines.extend(_complete_lines(tail, drop_first=True, drop_last=False))

    texts: list[str] = []
    message_count = 0
    seen: set[str] = set()
    for raw in raw_lines:
        try:
            row = json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        payload = row.get("payload", {})
        if row.get("type") != "response_item" or payload.get("type") != "message" or payload.get("role") != "user":
            continue
        chunks: list[str] = []
        for part in payload.get("content", []):
            if not isinstance(part, dict):
                continue
            value = part.get("text") or part.get("input_text")
            if isinstance(value, str):
                chunks.append(value)
        text = " ".join(chunks).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        message_count += 1
        # Ambient state and environment blocks are implementation noise, not user intent.
        text = re.sub(r"<in-app-browser-context[\s\S]*?</in-app-browser-context>", " ", text)
        text = re.sub(r"<environment_context>[\s\S]*?</environment_context>", " ", text)
        texts.append(text[:6000])
    return "\n".join(texts), message_count


def classify(text: str, *, title: str = "") -> tuple[str, int]:
    haystack = text.casefold()
    title_text = title.casefold()
    scores: list[tuple[int, int, str]] = []
    for order, topic in enumerate(TOPICS[:-1]):
        score = sum(
            (3 if len(keyword) >= 4 else 2)
            + ((3 if len(keyword) >= 4 else 2) * 100 if keyword.casefold() in title_text else 0)
            for keyword in topic["keywords"]
            if keyword.casefold() in haystack or keyword.casefold() in title_text
        )
        scores.append((score, -order, topic["id"]))
    score, _, topic_id = max(scores, default=(0, 0, "general"))
    return (topic_id if score else "general", score)


def _sort_key(record: dict[str, Any]) -> tuple[str, str]:
    return (record.get("updatedAt", ""), record.get("id", ""))


def build_context_index(codex_home: Path, *, deep_limit: int = 120) -> dict[str, Any]:
    indexed = read_session_index(codex_home)
    rollouts = discover_rollouts(codex_home)
    all_ids = set(indexed) | set(rollouts)
    records: list[dict[str, Any]] = []
    for task_id in all_ids:
        base = indexed.get(task_id, {"id": task_id, "title": "未命名历史任务", "updatedAt": ""})
        records.append({
            **base,
            "hasRollout": task_id in rollouts,
            "deepAnalyzed": False,
            "messageCount": None,
            "topicId": "general",
            "topicLabel": TOPIC_BY_ID["general"]["label"],
            "score": 0,
        })
    records.sort(key=_sort_key, reverse=True)

    deep_ids = {
        record["id"]
        for record in [row for row in records if row["hasRollout"]][: max(0, deep_limit)]
    }
    read_failures = 0
    for record in records:
        content = ""
        if record["id"] in deep_ids:
            try:
                content, message_count = read_recent_user_text(rollouts[record["id"]])
                record["deepAnalyzed"] = True
                record["messageCount"] = message_count
            except OSError:
                read_failures += 1
        topic_id, score = classify(content, title=record["title"])
        record["topicId"] = topic_id
        record["topicLabel"] = TOPIC_BY_ID[topic_id]["label"]
        record["score"] = score

    topic_rows: list[dict[str, Any]] = []
    for topic in TOPICS:
        matches = [record for record in records if record["topicId"] == topic["id"]]
        if not matches:
            continue
        matches.sort(key=_sort_key, reverse=True)
        topic_rows.append({
            "id": topic["id"],
            "label": topic["label"],
            "goal": topic["goal"],
            "successDefinition": topic["success"],
            "summary": f"从 {len(matches)} 个 Codex 任务中识别出的主题，最近包括：{'、'.join(row['title'] for row in matches[:3])}。",
            "taskCount": len(matches),
            "deepAnalyzedCount": sum(1 for row in matches if row["deepAnalyzed"]),
            "lastActiveAt": matches[0]["updatedAt"],
            "recentTitles": [row["title"] for row in matches[:5]],
            "candidateCount": len(topic["vocabulary"]),
        })
    topic_rows.sort(key=lambda row: (row["lastActiveAt"], row["taskCount"]), reverse=True)
    active_topic = next((topic["id"] for topic in topic_rows if topic["id"] != "general"), topic_rows[0]["id"] if topic_rows else None)
    timestamps = [record["updatedAt"] for record in records if record["updatedAt"]]
    return {
        "version": 1,
        "indexedAt": utc_now(),
        "activeTopicId": active_topic,
        "coverage": {
            "mode": "aggressive-local",
            "discoveredTaskCount": len(all_ids),
            "titledTaskCount": len(indexed),
            "rolloutTaskCount": len(rollouts),
            "deepAnalyzedTaskCount": sum(1 for record in records if record["deepAnalyzed"]),
            "messageCount": sum(record["messageCount"] or 0 for record in records),
            "metadataCoveragePercent": round((len(indexed) / len(all_ids) * 100), 1) if all_ids else 0,
            "readFailures": read_failures,
            "earliestTaskAt": min(timestamps) if timestamps else "",
            "latestTaskAt": max(timestamps) if timestamps else "",
            "scope": "本机 Codex 活跃与已归档任务；全量任务元数据 + 最近任务有限深读",
            "rawContentStored": False,
        },
        "topics": topic_rows,
        "tasks": records,
    }


def _source_id(topic_id: str) -> str:
    return f"codex-topic-{topic_id}"


def apply_context_index(state: dict[str, Any], context_index: dict[str, Any], now: str) -> None:
    previous = state.get("context_index", {})
    previous_active = previous.get("activeTopicId")
    valid_topic_ids = {topic["id"] for topic in context_index["topics"]}
    if previous_active in valid_topic_ids:
        context_index["activeTopicId"] = previous_active

    for topic_row in context_index["topics"]:
        topic = TOPIC_BY_ID[topic_row["id"]]
        source_id = _source_id(topic["id"])
        existing_source = state["sources"].get(source_id, {})
        state["sources"][source_id] = {
            "id": source_id,
            "label": topic["label"],
            "kind": "codex_history_cluster",
            "locator": "local Codex task history",
            "fingerprint": f"context-index-v1:{topic_row['taskCount']}:{topic_row['lastActiveAt']}",
            "authorized": True,
            "retain_raw": False,
            "summary": topic_row["summary"],
            "focus_points": list(topic_row["recentTitles"][:3]),
            "status": existing_source.get("status", "active"),
            "topic_id": topic["id"],
            "task_count": topic_row["taskCount"],
            "added_at": existing_source.get("added_at", now),
            "updated_at": now,
        }
        goal_id = store.stable_id("goal", topic["goal"])
        existing_goal = state["goals"].get(goal_id, {})
        state["goals"][goal_id] = {
            "id": goal_id,
            "statement": topic["goal"],
            "success_definition": topic["success"],
            "focus_modes": ["production", "recognition"],
            "confirmed": False,
            "status": "inactive",
            "topic_id": topic["id"],
            "created_at": existing_goal.get("created_at", now),
            "updated_at": now,
        }
        for position, (term, meaning, kind, rationale) in enumerate(topic["vocabulary"]):
            item_id = store.stable_id("item", term, meaning)
            existing = state["candidates"].get(item_id)
            candidate = {
                "id": item_id,
                "term": term,
                "meaning": meaning,
                "kind": kind,
                "rationale": f"{rationale}；来自“{topic['label']}”任务簇",
                "target_modes": ["production", "recognition"],
                "source_ids": [source_id],
                "goal_ids": [goal_id],
                "priority": 5 if position < 3 else 4,
                "evidence_summary": f"local Codex topic cluster with {topic_row['taskCount']} tasks",
                "suggested_anchor": f"结合你最近的“{topic_row['recentTitles'][0]}”任务自然使用这个表达。",
                "contrast": "",
                "status": existing.get("status", "proposed") if existing else "proposed",
                "topic_id": topic["id"],
                "created_at": existing.get("created_at", now) if existing else now,
                "updated_at": now,
            }
            state["candidates"][item_id] = candidate

    active_topic_id = context_index.get("activeTopicId")
    active_topic = TOPIC_BY_ID.get(active_topic_id or "")
    if active_topic:
        active_goal_id = store.stable_id("goal", active_topic["goal"])
        for goal in state["goals"].values():
            goal["status"] = "active" if goal["id"] == active_goal_id else "inactive"
        state["profile"]["active_goal_id"] = active_goal_id
    state["context_index"] = context_index
    state["updated_at"] = now
    store.add_event(
        state,
        now,
        "codex_context_scanned",
        discovered_tasks=context_index["coverage"]["discoveredTaskCount"],
        deep_analyzed_tasks=context_index["coverage"]["deepAnalyzedTaskCount"],
        topics=len(context_index["topics"]),
    )


def scan_into_store(state_path: Path, *, codex_home: Path | None = None, deep_limit: int = 120) -> dict[str, Any]:
    root = (codex_home or default_codex_home()).expanduser().resolve()
    if not state_path.exists():
        state = store.empty_state(utc_now())
        store.ensure_starter_lexicon(state, utc_now())
    else:
        state = store.load_state(state_path)
    now = store.iso_now()
    context_index = build_context_index(root, deep_limit=deep_limit)
    apply_context_index(state, context_index, now)
    errors = store.state_errors(state)
    if errors:
        raise store.StoreError("Context scan produced an invalid state: " + "; ".join(errors))
    store.save_state(state_path, state)
    return context_index


def select_topic(state_path: Path, topic_id: str) -> None:
    state = store.load_state(state_path)
    context_index = state.get("context_index", {})
    valid = {topic["id"] for topic in context_index.get("topics", [])}
    if topic_id not in valid:
        raise store.StoreError(f"Unknown context topic: {topic_id}")
    topic = TOPIC_BY_ID[topic_id]
    goal_id = store.stable_id("goal", topic["goal"])
    context_index["activeTopicId"] = topic_id
    for goal in state["goals"].values():
        goal["status"] = "active" if goal["id"] == goal_id else "inactive"
    state["profile"]["active_goal_id"] = goal_id
    now = store.iso_now()
    state["updated_at"] = now
    store.add_event(state, now, "context_topic_selected", topic_id=topic_id)
    store.save_state(state_path, state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", help="Vocabulary store path")
    parser.add_argument("--codex-home", help="Codex data directory")
    parser.add_argument("--deep-limit", type=int, default=120, help="Recent tasks to inspect with bounded head/tail reads")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("scan", help="Scan local Codex history and update the vocabulary store")
    select = subparsers.add_parser("select", help="Select an indexed topic as the active learning context")
    select.add_argument("--topic", required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    state_path = store.resolve_store_path(args.store)
    try:
        if args.command == "scan":
            result = scan_into_store(
                state_path,
                codex_home=Path(args.codex_home) if args.codex_home else None,
                deep_limit=max(0, args.deep_limit),
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            select_topic(state_path, args.topic)
            print(json.dumps({"topic_id": args.topic, "selected": True}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, store.StoreError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
