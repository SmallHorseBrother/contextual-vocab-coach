export const FEEDBACK_ORDER = ["again", "hard", "good", "easy"];

export const FEEDBACK_CONFIRMATIONS = {
  again: "再来一次",
  hard: "有点困难",
  good: "已经掌握",
  easy: "非常轻松",
};

export function getSessionPrompt(item) {
  if (item.mode === "recognition") {
    return {
      modeLabel: "理解辨认",
      title: `请解释这个英文表达：${item.term}`,
      placeholder: "写下你理解的中文意思…",
      referenceLabel: "参考意思",
      reference: item.meaning,
    };
  }
  if (item.mode === "listening") {
    return {
      modeLabel: "听音理解",
      title: "播放英文后，写下你听到的内容或意思",
      placeholder: "写下你听到的英文或理解的意思…",
      referenceLabel: "参考答案",
      reference: `${item.term} · ${item.meaning}`,
    };
  }
  return {
    modeLabel: "主动表达",
    title: `请用英文表达：${item.meaning}`,
    placeholder: "在这里输入你的英文表达…",
    referenceLabel: "参考表达",
    reference: item.term,
  };
}

export function nextSessionStep(feedback, index, total) {
  if (!FEEDBACK_ORDER.includes(feedback)) throw new Error(`Unsupported feedback: ${feedback}`);
  if (!Number.isInteger(index) || !Number.isInteger(total) || total < 1 || index < 0 || index >= total) {
    throw new Error("Invalid session position");
  }
  if (feedback === "again") return { kind: "retry", nextIndex: index };
  if (index + 1 < total) return { kind: "next", nextIndex: index + 1 };
  return { kind: "complete", nextIndex: index };
}
