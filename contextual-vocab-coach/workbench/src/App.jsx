import { useEffect, useMemo, useState } from "react";
import {
  Archive,
  BookOpenText,
  CaretDown,
  ChatCenteredDots,
  Check,
  ClockCounterClockwise,
  Database,
  House,
  Lightbulb,
  ListChecks,
  Pause,
  Play,
  ShareNetwork,
  SpeakerHigh,
  Sparkle,
  Target,
} from "@phosphor-icons/react";
import { MOCK_STATE, STATUS_LABELS } from "./mockData.js";
import { decideCandidate, fetchWorkbenchState, recordReview, setSourceStatus } from "./api.js";

const NAV_ITEMS = [
  { id: "today", label: "Today", icon: House },
  { id: "inbox", label: "Candidate Inbox", icon: Archive },
  { id: "review", label: "Review", icon: ClockCounterClockwise },
  { id: "map", label: "Memory Map", icon: ShareNetwork },
  { id: "sources", label: "Sources", icon: Database },
];

const DECISIONS = [
  { id: "known", label: "已会" },
  { id: "not_now", label: "暂不学" },
  { id: "test", label: "先测试" },
  { id: "learning", label: "加入学习" },
];

function useWorkbenchState() {
  const [data, setData] = useState(() => {
    const stored = window.localStorage.getItem("contextual-vocab-demo-state");
    if (!stored) return MOCK_STATE;
    try {
      return { ...MOCK_STATE, ...JSON.parse(stored), connected: false };
    } catch {
      return MOCK_STATE;
    }
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetchWorkbenchState()
      .then((remote) => {
        if (active && remote) setData({ ...remote, connected: true });
      })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  const updateLocal = (next) => {
    setData(next);
    if (!next.connected) window.localStorage.setItem("contextual-vocab-demo-state", JSON.stringify(next));
  };

  return { data, updateLocal, loading };
}

function NavRail({ activeView, onNavigate, dueCount }) {
  return (
    <aside className="nav-rail">
      <div className="brand-block">
        <div className="brand-name">Codex Sidecar</div>
        <p>让真实对话，成为你的英语</p>
      </div>
      <nav aria-label="主要导航">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button aria-label={label} className={`nav-item ${activeView === id ? "is-active" : ""}`} key={id} onClick={() => onNavigate(id)} type="button">
            <Icon size={24} weight={activeView === id ? "bold" : "regular"} />
            <span>{label}</span>
            {id === "review" && dueCount > 0 ? <b>{dueCount}</b> : null}
          </button>
        ))}
      </nav>
      <p className="local-note">本地优先 · 你的学习数据<br />只保存在此设备</p>
    </aside>
  );
}

function GoalHeader({ goal, sourceLabel }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="goal-header">
      <div className="goal-switcher">
        <span className="eyebrow">当前学习目标</span>
        <button aria-expanded={menuOpen} className="goal-title" type="button" aria-label="查看学习目标" onClick={() => setMenuOpen((value) => !value)}>
          {goal?.statement || "尚未设置学习目标"}
          <CaretDown size={24} weight="bold" />
        </button>
        <p>来自：{sourceLabel || "尚未选择来源"}</p>
        {menuOpen ? <div className="goal-menu"><strong>{goal?.statement || "尚未设置学习目标"}</strong><span>{goal?.successDefinition || "请先在 Codex 中确认一个真实任务。"}</span><small>如需更换目标，请在 Codex 对话中告诉我。</small></div> : null}
      </div>
      <div className="goal-promise">
        <Sparkle size={22} weight="duotone" />
        <span>从真实对话中，<br />收集值得学习的英语。</span>
      </div>
    </header>
  );
}

function CandidateActions({ candidate, pending, onDecision }) {
  return (
    <div className="candidate-actions" aria-label={`${candidate.term} 的学习决定`}>
      {DECISIONS.map((decision) => (
        <button
          className={`decision-button decision-${decision.id} ${candidate.status === decision.id ? "is-selected" : ""}`}
          disabled={pending}
          key={decision.id}
          onClick={() => onDecision(candidate.id, decision.id)}
          type="button"
        >
          {candidate.status === decision.id && decision.id !== "learning" ? <Check size={15} weight="bold" /> : null}
          {decision.label}
        </button>
      ))}
    </div>
  );
}

function CandidateInbox({ data, pendingId, onDecision, onSpeak }) {
  return (
    <section className="inbox-view" aria-labelledby="candidate-heading">
      <div className="candidate-summary">
        <h2 id="candidate-heading">共 {data.candidates.length} 条推荐表达</h2>
        <p>逐一判断，选择最适合你的下一步。</p>
      </div>
      <div className="candidate-table" role="table" aria-label="推荐表达">
        <div className="candidate-table-head" role="row">
          <span aria-hidden="true" /><span>表达</span><span>中文意思</span><span>为什么现在学</span><span>来源</span><span>建议模式</span><span>操作</span>
        </div>
        <div className="candidate-table-body">
          {data.candidates.map((candidate, index) => (
            <article className={`candidate-row status-${candidate.status}`} key={candidate.id} role="row">
              <span className="row-index">{index + 1}</span>
              <div className="term-cell">
                <strong>{candidate.term}</strong>
                <button className="speak-button" onClick={() => onSpeak(candidate.term)} type="button" aria-label={`朗读 ${candidate.term}`}>
                  <SpeakerHigh size={19} weight="regular" />
                </button>
              </div>
              <p className="meaning-cell">{candidate.meaning}</p>
              <p className="reason-cell">{candidate.rationale}</p>
              <div className="source-cell"><span>{candidate.sourceLabel}</span><small>{candidate.sourceTime || "刚刚"}</small></div>
              <div className="mode-cell"><span className={`mode-pill mode-${candidate.mode}`}>{candidate.modeLabel}</span></div>
              <CandidateActions candidate={candidate} pending={pendingId === candidate.id} onDecision={onDecision} />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function AssistantRail({ data, onStartLearning }) {
  const selectedCount = data.candidates.filter((item) => ["learning", "test"].includes(item.status)).length;
  return (
    <aside className="assistant-rail">
      <header><h2>Codex 助手</h2><p>基于你授权的对话内容</p></header>
      <section className="assistant-summary">
        <div className="assistant-section-title"><ChatCenteredDots size={23} weight="duotone" /><strong>本次提取的对话摘要</strong></div>
        <p>{data.summary}</p>
        <div className="summary-divider" />
        <h3>关注点</h3>
        <ul>{data.focusPoints.map((point) => <li key={point}>{point}</li>)}</ul>
      </section>
      <button className="start-learning" onClick={onStartLearning} type="button"><Play size={24} weight="fill" />开始 10 分钟学习</button>
      <p className="start-note">{selectedCount > 0 ? `已选择 ${selectedCount} 条表达，将优先生成练习` : "先做判断，再生成贴合你的学习内容"}</p>
      <section className="tip-panel">
        <div className="assistant-section-title"><Lightbulb size={23} weight="duotone" /><strong>小贴士</strong></div>
        <p>先快速判断，不用纠结。把精力放在真正对你现在有帮助的表达上。</p>
      </section>
    </aside>
  );
}

function EmptyPanel({ icon: Icon, title, body, actionLabel, onAction }) {
  return (
    <section className="simple-panel"><Icon size={38} weight="duotone" /><h2>{title}</h2><p>{body}</p>{actionLabel ? <button className="primary-inline" onClick={onAction} type="button">{actionLabel}</button> : null}</section>
  );
}

function LearningSession({ candidates, onBack, onReview }) {
  const queue = candidates.filter((item) => ["learning", "test"].includes(item.status));
  const items = queue.length ? queue : candidates.slice(0, 3);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [revealed, setRevealed] = useState(false);
  const current = items[index];

  if (!current) return <EmptyPanel icon={BookOpenText} title="还没有学习内容" body="先从候选收件箱中选择几条值得学的表达。" actionLabel="返回候选收件箱" onAction={onBack} />;

  const rate = async (feedback) => {
    await onReview(current.id, current.mode || "production", feedback);
    setAnswer(""); setRevealed(false); setIndex((value) => (value + 1) % items.length);
  };

  return (
    <section className="session-view">
      <button className="back-link" onClick={onBack} type="button">← 返回候选收件箱</button>
      <div className="session-progress"><span style={{ width: `${((index + 1) / items.length) * 100}%` }} /></div>
      <span className="eyebrow">主动表达 · {index + 1} / {items.length}</span>
      <h2>请用英文表达：{current.meaning}</h2>
      <p className="session-context">练习场景：{current.anchor || "在你的产品介绍中自然使用这个表达。"}</p>
      <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="在这里输入你的英文表达…" rows={6} />
      {!revealed ? <button className="session-submit" disabled={!answer.trim()} onClick={() => setRevealed(true)} type="button">提交答案</button> : (
        <div className="session-feedback"><p>参考表达：<strong>{current.term}</strong></p><p>根据刚才的实际回忆情况选择：</p><div>{["again", "hard", "good", "easy"].map((feedback) => <button key={feedback} onClick={() => rate(feedback)} type="button">{STATUS_LABELS[feedback]}</button>)}</div></div>
      )}
    </section>
  );
}

function MasteryView({ candidates }) {
  const groups = [{ status: "learning", label: "正在学习" }, { status: "test", label: "等待短测" }, { status: "known", label: "已经会了" }, { status: "proposed", label: "候选表达" }, { status: "not_now", label: "近期不用" }];
  return (
    <section className="list-view">
      <div className="list-view-heading"><ShareNetwork size={30} weight="duotone" /><div><h2>任务—词汇掌握地图</h2><p>这是学习记录，不是对大脑的扫描。</p></div></div>
      {groups.map((group) => {
        const items = candidates.filter((item) => item.status === group.status);
        if (!items.length) return null;
        return <div className="mastery-group" key={group.status}><h3>{group.label}</h3>{items.map((item) => <div className="mastery-row" key={item.id}><span className={`status-dot dot-${group.status}`} /><strong>{item.term}</strong><span>{item.meaning}</span><small>{item.modeLabel}</small></div>)}</div>;
      })}
    </section>
  );
}

function SourcesView({ sources, onToggle }) {
  return (
    <section className="list-view">
      <div className="list-view-heading"><Database size={30} weight="duotone" /><div><h2>授权来源</h2><p>查看、暂停或恢复参与候选生成的上下文。</p></div></div>
      <div className="source-list">{sources.map((source) => <div className="source-row" key={source.id}><div><strong>{source.label}</strong><p>{source.summary || source.kind}</p></div><button className={source.status === "active" ? "source-active" : ""} onClick={() => onToggle(source)} type="button">{source.status === "active" ? <><Pause size={18} /> 暂停</> : <><Play size={18} /> 恢复</>}</button></div>)}</div>
    </section>
  );
}

export function App() {
  const { data, updateLocal, loading } = useWorkbenchState();
  const [activeView, setActiveView] = useState("inbox");
  const [sessionOpen, setSessionOpen] = useState(false);
  const [pendingId, setPendingId] = useState(null);
  const sourceLabel = data.sources.find((source) => source.status === "active")?.label || data.sources[0]?.label;
  const dueCount = useMemo(() => data.dueCount ?? data.candidates.filter((item) => item.status === "learning").length, [data]);

  const handleDecision = async (itemId, decision) => {
    setPendingId(itemId);
    const optimistic = { ...data, candidates: data.candidates.map((candidate) => candidate.id === itemId ? { ...candidate, status: decision } : candidate) };
    updateLocal(optimistic);
    const remote = await decideCandidate(itemId, decision);
    if (remote) updateLocal({ ...remote, connected: true });
    setPendingId(null);
  };

  const handleReview = async (itemId, mode, feedback) => {
    const remote = await recordReview(itemId, mode, feedback);
    if (remote) updateLocal({ ...remote, connected: true });
  };

  const handleSourceToggle = async (source) => {
    const status = source.status === "active" ? "paused" : "active";
    updateLocal({ ...data, sources: data.sources.map((item) => item.id === source.id ? { ...item, status } : item) });
    const remote = await setSourceStatus(source.id, status);
    if (remote) updateLocal({ ...remote, connected: true });
  };

  const speak = (term) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(term); utterance.lang = "en-US"; window.speechSynthesis.speak(utterance);
  };

  const navigate = (view) => { setSessionOpen(false); setActiveView(view); };
  let content;
  if (sessionOpen) content = <LearningSession candidates={data.candidates} onBack={() => { setSessionOpen(false); setActiveView("inbox"); }} onReview={handleReview} />;
  else if (activeView === "inbox") content = <CandidateInbox data={data} pendingId={pendingId} onDecision={handleDecision} onSpeak={speak} />;
  else if (activeView === "today") content = <EmptyPanel icon={Target} title="今天最值得学的英语" body={`围绕“${data.goal?.statement || "当前目标"}”，先完成到期复习，再加入少量新表达。`} actionLabel="开始今天的学习" onAction={() => setSessionOpen(true)} />;
  else if (activeView === "review") content = <EmptyPanel icon={ListChecks} title={`${dueCount} 项等待复习`} body="复习会更换措辞或使用场景，检查你是否真正能够迁移使用。" actionLabel="开始复习" onAction={() => setSessionOpen(true)} />;
  else if (activeView === "map") content = <MasteryView candidates={data.candidates} />;
  else content = <SourcesView sources={data.sources} onToggle={handleSourceToggle} />;

  return (
    <div className={`workbench-shell ${loading ? "is-loading" : ""}`}>
      <NavRail activeView={activeView} onNavigate={navigate} dueCount={dueCount} />
      <main className="workspace-main"><GoalHeader goal={data.goal} sourceLabel={sourceLabel} /><div className="workspace-content">{content}</div></main>
      <AssistantRail data={data} onStartLearning={() => setSessionOpen(true)} />
    </div>
  );
}
