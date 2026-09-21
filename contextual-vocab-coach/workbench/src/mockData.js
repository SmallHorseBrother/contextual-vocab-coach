export const STATUS_LABELS = {
  again: "再来一次",
  hard: "困难",
  good: "掌握",
  easy: "轻松",
};

export const MOCK_STATE = {
  connected: false,
  goal: {
    statement: "用英语介绍我的产品",
    successDefinition: "不逐句翻译，完成一段两分钟的产品介绍",
  },
  summary: "你正在与团队讨论一款面向全球用户的健康饮食产品，涉及功能设计、目标用户、产品价值和市场策略。我从这段对话中提取了 5 个在你当前目标下最有学习价值的英语表达。",
  focusPoints: [
    "介绍产品的核心功能和使用场景",
    "说明如何根据饮食偏好提供个性化建议",
    "讨论产品的长期价值和功能优先级",
  ],
  dueCount: 0,
  candidates: [
    { id: "demo-estimate", term: "estimate portion sizes", meaning: "估算食物的分量大小", rationale: "你在讨论产品的饮食建议功能时提到这个场景，未来需要向用户解释如何使用。", sourceLabel: "当前项目讨论", sourceTime: "刚刚", mode: "production", modeLabel: "主动表达", status: "proposed", anchor: "介绍产品如何分析一张真实的餐食照片。" },
    { id: "demo-dietary", term: "dietary preferences", meaning: "饮食偏好；饮食习惯", rationale: "你多次提到根据用户的饮食偏好提供个性化方案，这是产品的核心功能之一。", sourceLabel: "当前项目讨论", sourceTime: "刚刚", mode: "production", modeLabel: "主动表达", status: "proposed", anchor: "对比两个用户不同的饮食需求。" },
    { id: "demo-prioritize", term: "prioritize", meaning: "优先考虑；把……放在优先位置", rationale: "你在讨论产品路线图时提到需要优先考虑高频用户需求，并在英文讨论中多次使用。", sourceLabel: "当前项目讨论", sourceTime: "刚刚", mode: "production", modeLabel: "主动表达", status: "proposed", anchor: "向团队解释为什么先开发一个小功能。" },
    { id: "demo-seamless", term: "seamless experience", meaning: "无缝的体验；流畅的使用体验", rationale: "你希望在产品介绍中突出简单、顺畅的使用体验，这个表达在对话中被多次提及。", sourceLabel: "当前项目讨论", sourceTime: "刚刚", mode: "production", modeLabel: "主动表达", status: "proposed", anchor: "描述用户拍照后立即得到结果的过程。" },
    { id: "demo-long-run", term: "in the long run", meaning: "从长远来看；长期而言", rationale: "你在讨论产品价值时提到它能在长期内帮助用户养成更健康的饮食习惯。", sourceLabel: "当前项目讨论", sourceTime: "刚刚", mode: "recognition", modeLabel: "理解优先", status: "proposed", anchor: "说明产品长期带来的用户价值。" },
  ],
  sources: [
    { id: "current-project-chat", label: "当前项目讨论", kind: "current_conversation", status: "active", summary: "关于健康饮食产品功能、用户价值与路线图的授权对话摘要。" },
  ],
};
