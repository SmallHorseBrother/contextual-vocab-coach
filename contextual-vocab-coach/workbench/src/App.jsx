import { useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  BookOpenText,
  Books,
  CaretDown,
  ChatCenteredDots,
  Check,
  CheckCircle,
  ClockCounterClockwise,
  Database,
  House,
  Lightbulb,
  ListChecks,
  MagnifyingGlass,
  Pause,
  Play,
  Plus,
  ShareNetwork,
  SpeakerHigh,
  Sparkle,
  Target,
  WarningCircle,
} from "@phosphor-icons/react";
import { MOCK_STATE } from "./mockData.js";
import { addLibraryEntry, decideCandidate, fetchWorkbenchState, recordReview, scanCodexContext, selectContextTopic, setSourceStatus } from "./api.js";
import { FEEDBACK_CONFIRMATIONS, FEEDBACK_ORDER, getSessionPrompt, nextSessionStep } from "./sessionFlow.js";

const NAV_ITEMS = [
  { id: "today", label: "Today", icon: House },
  { id: "inbox", label: "Candidate Inbox", icon: Archive },
  { id: "library", label: "Word Library", icon: Books },
  { id: "review", label: "Review", icon: ClockCounterClockwise },
  { id: "map", label: "Memory Map", icon: ShareNetwork },
  { id: "context", label: "Context Map", icon: MagnifyingGlass },
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
        {menuOpen ? <div className="goal-menu"><strong>{goal?.statement || "尚未设置学习目标"}</strong><span>{goal?.successDefinition || "请先在 Codex 中确认一个真实任务。"}</span><small>可在 Context Map 中切换任务主题。</small></div> : null}
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

const LIBRARY_STATUS_LABELS = {
  available: "加入学习",
  learning: "正在学习",
  test: "等待短测",
  known: "已经会了",
  not_now: "近期不用",
  proposed: "候选表达",
};

function LibraryView({ library, pendingId, onAdd, onSpeak }) {
  const [query, setQuery] = useState("");
  const [scenario, setScenario] = useState("");
  const [level, setLevel] = useState("");
  const entries = library?.entries || [];
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const filtered = entries.filter((entry) => {
    if (scenario && !entry.scenario_ids.includes(scenario)) return false;
    if (level && entry.level !== level) return false;
    if (!normalizedQuery) return true;
    return [entry.term, entry.meaning, ...(entry.scenario_labels || [])].join(" ").toLocaleLowerCase().includes(normalizedQuery);
  });
  const visible = filtered.slice(0, 80);

  return (
    <section className="library-view" aria-labelledby="library-heading">
      <div className="library-hero">
        <div><span className="eyebrow">生活英语储备池</span><h2 id="library-heading">{library?.entryCount || 0} 个基础词与场景表达</h2><p>这里是完整储备库；候选收件箱仍只挑 5–8 个最适合你当前目标的内容。</p></div>
        <div className="library-stat"><strong>{library?.scenarios?.length || 0}</strong><span>生活场景</span></div>
      </div>
      <div className="library-controls">
        <label className="library-search"><MagnifyingGlass size={19} /><input aria-label="搜索词库" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索英文、中文或场景…" /></label>
        <select aria-label="按生活场景筛选" value={scenario} onChange={(event) => setScenario(event.target.value)}><option value="">全部场景</option>{(library?.scenarios || []).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
        <select aria-label="按难度筛选" value={level} onChange={(event) => setLevel(event.target.value)}><option value="">全部难度</option>{(library?.levels || []).map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </div>
      <div className="library-result-line"><span>找到 {filtered.length} 项</span><small>当前最多显示 80 项，请用搜索或筛选快速缩小范围。</small></div>
      <div className="library-grid">
        {visible.map((entry) => {
          const available = entry.status === "available";
          return <article className="library-card" key={entry.id}>
            <div className="library-copy">
              <div className="library-term"><strong>{entry.term}</strong><button className="speak-button" onClick={() => onSpeak(entry.term)} type="button" aria-label={`朗读 ${entry.term}`}><SpeakerHigh size={18} /></button></div>
              <p>{entry.meaning}</p>
              <div className="library-tags"><span className={`level-tag level-${entry.level.toLowerCase()}`}>{entry.level}</span>{(entry.scenario_labels || []).map((label) => <span key={label}>{label}</span>)}</div>
            </div>
            <button className={`library-add ${available ? "" : "is-added"}`} disabled={!available || pendingId === entry.id} onClick={() => onAdd(entry)} type="button">{available ? <Plus size={17} weight="bold" /> : <Check size={17} weight="bold" />}{LIBRARY_STATUS_LABELS[entry.status] || entry.status}</button>
          </article>;
        })}
      </div>
      {!visible.length ? <div className="library-empty">没有匹配项。换一个中文、英文或生活场景试试。</div> : null}
    </section>
  );
}

function AssistantRail({ data, onStartLearning }) {
  const selectedCount = data.candidates.filter((item) => ["learning", "test"].includes(item.status)).length;
  return (
    <aside className="assistant-rail">
      <header><h2>Codex 助手</h2><p>基于本机 Codex 任务索引</p></header>
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

function LearningSession({ sessionItems, onExit, onReview, onSpeak, returnLabel }) {
  const [items] = useState(() => sessionItems.map((item) => ({ ...item })));
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [revealed, setRevealed] = useState(false);
  const [pendingFeedback, setPendingFeedback] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [results, setResults] = useState([]);
  const [finished, setFinished] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const sessionRef = useRef(null);
  const questionStartedAt = useRef(Date.now());
  const current = items[index];

  useEffect(() => {
    sessionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [index, finished, retryCount]);

  if (!current) return <EmptyPanel icon={BookOpenText} title="没有等待复习的内容" body="当前没有到期项目。可以回到词库加入内容，或从候选收件箱选择表达。" actionLabel={`返回${returnLabel}`} onAction={onExit} />;

  const rate = async (feedback) => {
    if (pendingFeedback) return;
    setPendingFeedback(feedback);
    setError("");
    const responseMs = Math.max(0, Date.now() - questionStartedAt.current);
    const saved = await onReview(current.itemId || current.id, current.mode || "production", feedback, responseMs);
    if (!saved) {
      setError("这次结果没有保存成功。你的答案还在，可以直接重试。");
      setPendingFeedback(null);
      return;
    }
    const result = { itemId: current.itemId || current.id, mode: current.mode || "production", term: current.term, feedback };
    setResults((value) => [...value, result]);
    const step = nextSessionStep(feedback, index, items.length);
    setPendingFeedback(null);
    if (step.kind === "complete") {
      setFinished(true);
      return;
    }
    setAnswer("");
    setRevealed(false);
    questionStartedAt.current = Date.now();
    if (step.kind === "retry") {
      setNotice(`已记录“${current.term}”：再来一次。答案已收起，请重新回忆。`);
      setRetryCount((value) => value + 1);
      return;
    }
    setNotice(`已记录“${current.term}”：${FEEDBACK_CONFIRMATIONS[feedback]}。继续下一题。`);
    setIndex(step.nextIndex);
  };

  if (finished) {
    const completed = results.filter((result) => result.feedback !== "again");
    const completedItems = new Set(completed.map((result) => `${result.itemId}:${result.mode}`)).size;
    return (
      <section className="session-view session-complete" ref={sessionRef} aria-live="polite">
        <CheckCircle size={48} weight="duotone" />
        <span className="eyebrow">本轮完成</span>
        <h2>这次练习已经记录</h2>
        <p>完成 {completedItems} 个练习项目，共记录 {results.length} 次真实回忆。复习时间已经更新。</p>
        <div className="session-result-summary">
          {FEEDBACK_ORDER.map((feedback) => {
            const count = results.filter((result) => result.feedback === feedback).length;
            return count ? <span key={feedback}>{FEEDBACK_CONFIRMATIONS[feedback]} · {count}</span> : null;
          })}
        </div>
        <button className="session-submit" onClick={onExit} type="button">返回{returnLabel}</button>
      </section>
    );
  }

  const prompt = getSessionPrompt(current);

  return (
    <section className="session-view" ref={sessionRef}>
      <button className="back-link" onClick={onExit} type="button">← 结束并返回{returnLabel}</button>
      <div className="session-progress"><span style={{ width: `${((index + 1) / items.length) * 100}%` }} /></div>
      {notice ? <div className="session-notice" role="status"><CheckCircle size={20} weight="fill" />{notice}</div> : null}
      <span className="eyebrow">{prompt.modeLabel} · {index + 1} / {items.length}</span>
      <h2>{prompt.title}</h2>
      <p className="session-context">练习场景：{current.anchor || "在你的产品介绍中自然使用这个表达。"}</p>
      {current.mode === "listening" ? <button className="session-listen" onClick={() => onSpeak(current.term)} type="button"><SpeakerHigh size={20} />播放英文</button> : null}
      <textarea aria-label="你的回答" value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder={prompt.placeholder} rows={6} />
      {!revealed ? <button className="session-submit" disabled={!answer.trim()} onClick={() => { setNotice(""); setRevealed(true); }} type="button">提交答案</button> : (
        <div className="session-feedback">
          <p>{prompt.referenceLabel}：<strong>{prompt.reference}</strong></p>
          <p>根据刚才的实际回忆情况选择；点击后会立即保存并继续。</p>
          {error ? <div className="session-error" role="alert"><WarningCircle size={20} weight="fill" />{error}</div> : null}
          <div className="feedback-actions">{FEEDBACK_ORDER.map((feedback) => <button disabled={Boolean(pendingFeedback)} key={feedback} onClick={() => rate(feedback)} type="button">{pendingFeedback === feedback ? "记录中…" : FEEDBACK_CONFIRMATIONS[feedback]}</button>)}</div>
        </div>
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

function formatScanTime(value) {
  if (!value) return "尚未扫描";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

function ContextView({ contextIndex, pending, error, onScan, onSelectTopic, scanEnabled }) {
  const coverage = contextIndex?.coverage || {};
  const topics = contextIndex?.topics || [];
  const tasks = contextIndex?.tasks || [];
  const activeTopicId = contextIndex?.activeTopicId;
  const [taskFilter, setTaskFilter] = useState("all");
  const visibleTasks = tasks.filter((task) => taskFilter === "all" || task.topicId === taskFilter).slice(0, 80);

  return (
    <section className="context-view" aria-labelledby="context-heading">
      <div className="context-hero">
        <div>
          <span className="eyebrow">本机 Codex 上下文索引</span>
          <h2 id="context-heading">不只看当前对话，看见你的完整任务版图</h2>
          <p>任务标题与时间做全量索引；最近任务做有限深读。原始对话不写入词汇库，覆盖情况在这里透明展示。</p>
        </div>
        <button className="context-scan-button" disabled={pending || !scanEnabled} onClick={onScan} type="button">
          <ClockCounterClockwise size={20} weight="bold" />
          {pending ? "正在扫描…" : scanEnabled ? "重新扫描 Codex" : "演示模式不可扫描"}
        </button>
      </div>
      {error ? <div className="context-error" role="alert"><WarningCircle size={20} weight="fill" />{error}</div> : null}
      <div className="coverage-strip">
        <div><strong>{coverage.discoveredTaskCount || 0}</strong><span>发现的唯一任务</span></div>
        <div><strong>{coverage.titledTaskCount || 0}</strong><span>已建立标题索引</span></div>
        <div><strong>{coverage.deepAnalyzedTaskCount || 0}</strong><span>最近任务有限深读</span></div>
        <div><strong>{topics.length}</strong><span>识别出的主题簇</span></div>
      </div>
      <div className="coverage-note">
        <CheckCircle size={19} weight="duotone" />
        <span>{coverage.scope || "等待首次扫描"} · 元数据覆盖 {coverage.metadataCoveragePercent || 0}% · 原文持久化：{coverage.rawContentStored ? "是" : "否"} · 更新于 {formatScanTime(contextIndex?.indexedAt)}</span>
      </div>
      <div className="context-section-heading">
        <div><h3>主题工作区</h3><p>选择一个主题，候选词汇和学习目标会立即切换；不同领域不会混成一张词表。</p></div>
      </div>
      <div className="topic-grid">
        {topics.map((topic) => (
          <button className={`topic-card ${topic.id === activeTopicId ? "is-active" : ""}`} key={topic.id} onClick={() => onSelectTopic(topic.id)} type="button">
            <span className="topic-card-top"><strong>{topic.label}</strong><b>{topic.taskCount} 个任务</b></span>
            <p>{topic.goal}</p>
            <span className="topic-meta">深读 {topic.deepAnalyzedCount} · 候选 {topic.candidateCount} · 最近 {formatScanTime(topic.lastActiveAt)}</span>
            <span className="topic-examples">{(topic.recentTitles || []).slice(0, 3).join(" · ")}</span>
          </button>
        ))}
      </div>
      <div className="context-section-heading task-heading">
        <div><h3>扫描到的任务</h3><p>显示最近 80 项；可按主题核对哪些任务被归到哪里。</p></div>
        <select aria-label="按主题筛选任务" value={taskFilter} onChange={(event) => setTaskFilter(event.target.value)}>
          <option value="all">全部主题</option>
          {topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.label}</option>)}
        </select>
      </div>
      <div className="task-index-table" role="table" aria-label="Codex 任务索引">
        {visibleTasks.map((task) => (
          <div className="task-index-row" key={task.id} role="row">
            <span className={`deep-dot ${task.deepAnalyzed ? "is-deep" : ""}`} title={task.deepAnalyzed ? "已有限深读" : "仅元数据"} />
            <strong>{task.title}</strong>
            <span>{task.topicLabel}</span>
            <small>{formatScanTime(task.updatedAt)}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

export function App() {
  const { data, updateLocal, loading } = useWorkbenchState();
  const [activeView, setActiveView] = useState("inbox");
  const [sessionOpen, setSessionOpen] = useState(false);
  const [pendingId, setPendingId] = useState(null);
  const [pendingLibraryId, setPendingLibraryId] = useState(null);
  const [contextPending, setContextPending] = useState(false);
  const [contextError, setContextError] = useState("");
  const activeTopicId = data.contextIndex?.activeTopicId;
  const activeTopic = data.contextIndex?.topics?.find((topic) => topic.id === activeTopicId);
  const scopedCandidates = data.candidates.filter((candidate) => !activeTopicId || !candidate.topicId || candidate.topicId === activeTopicId);
  const sourceLabel = data.sources.find((source) => source.status === "active" && source.topicId === activeTopicId)?.label || data.sources.find((source) => source.status === "active" && !source.isBundled)?.label || data.sources.find((source) => source.status === "active")?.label || data.sources[0]?.label;
  const dueCount = useMemo(() => data.dueCount ?? data.candidates.filter((item) => item.status === "learning").length, [data]);

  const handleDecision = async (itemId, decision) => {
    setPendingId(itemId);
    const optimistic = { ...data, candidates: data.candidates.map((candidate) => candidate.id === itemId ? { ...candidate, status: decision } : candidate) };
    updateLocal(optimistic);
    const remote = await decideCandidate(itemId, decision);
    if (remote) updateLocal({ ...remote, connected: true });
    setPendingId(null);
  };

  const handleReview = async (itemId, mode, feedback, responseMs) => {
    const remote = await recordReview(itemId, mode, feedback, responseMs);
    if (!remote) return false;
    updateLocal({ ...remote, connected: true });
    return true;
  };

  const handleSourceToggle = async (source) => {
    const status = source.status === "active" ? "paused" : "active";
    updateLocal({ ...data, sources: data.sources.map((item) => item.id === source.id ? { ...item, status } : item) });
    const remote = await setSourceStatus(source.id, status);
    if (remote) updateLocal({ ...remote, connected: true });
  };

  const handleLibraryAdd = async (entry) => {
    setPendingLibraryId(entry.id);
    const localCandidate = { id: entry.id, term: entry.term, meaning: entry.meaning, rationale: `你从“${entry.scenario_labels.join("、")}”基础词库主动加入`, sourceLabel: "内置生活英语词库", sourceTime: "刚刚", mode: entry.target_modes[0], modeLabel: entry.target_modes[0] === "recognition" ? "理解优先" : "主动表达", status: "learning", anchor: `在“${entry.scenario_labels.join("、")}”场景中自然使用这个表达。` };
    const optimistic = { ...data, library: { ...data.library, entries: data.library.entries.map((item) => item.id === entry.id ? { ...item, status: "learning" } : item) }, candidates: data.candidates.some((item) => item.term === entry.term && item.meaning === entry.meaning) ? data.candidates : [...data.candidates, localCandidate] };
    updateLocal(optimistic);
    const remote = await addLibraryEntry(entry.id);
    if (remote) updateLocal({ ...remote, connected: true });
    setPendingLibraryId(null);
  };

  const handleContextScan = async () => {
    setContextPending(true);
    setContextError("");
    const remote = await scanCodexContext();
    if (remote) updateLocal({ ...remote, connected: true });
    else setContextError("扫描没有完成。请确认当前运行的是真实工作台，并稍后重试。");
    setContextPending(false);
  };

  const handleTopicSelect = async (topicId) => {
    setContextError("");
    const optimistic = { ...data, contextIndex: { ...data.contextIndex, activeTopicId: topicId } };
    updateLocal(optimistic);
    const remote = await selectContextTopic(topicId);
    if (remote) updateLocal({ ...remote, connected: true });
    else {
      updateLocal(data);
      setContextError("主题切换没有保存成功，请重试。");
    }
  };

  const speak = (term) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(term); utterance.lang = "en-US"; window.speechSynthesis.speak(utterance);
  };

  const navigate = (view) => { setSessionOpen(false); setActiveView(view); };
  const selectedItems = scopedCandidates.filter((item) => ["learning", "test"].includes(item.status));
  const sessionItems = activeView === "review"
    ? (data.reviewQueue || [])
    : (selectedItems.length ? selectedItems : scopedCandidates.slice(0, 3));
  const returnLabel = { today: "今日学习", inbox: "候选收件箱", library: "词库", review: "复习", map: "掌握地图", context: "上下文地图", sources: "来源管理" }[activeView] || "工作台";
  const scopedData = { ...data, candidates: scopedCandidates };
  let content;
  if (sessionOpen) content = <LearningSession sessionItems={sessionItems} onExit={() => setSessionOpen(false)} onReview={handleReview} onSpeak={speak} returnLabel={returnLabel} />;
  else if (activeView === "inbox") content = <CandidateInbox data={scopedData} pendingId={pendingId} onDecision={handleDecision} onSpeak={speak} />;
  else if (activeView === "library") content = <LibraryView library={data.library} pendingId={pendingLibraryId} onAdd={handleLibraryAdd} onSpeak={speak} />;
  else if (activeView === "today") content = <EmptyPanel icon={Target} title="今天最值得学的英语" body={`围绕“${data.goal?.statement || "当前目标"}”，先完成到期复习，再加入少量新表达。`} actionLabel="开始今天的学习" onAction={() => setSessionOpen(true)} />;
  else if (activeView === "review") content = <EmptyPanel icon={ListChecks} title={`${dueCount} 项等待复习`} body={dueCount ? "复习会更换措辞或使用场景，检查你是否真正能够迁移使用。" : "今天没有到期项目。新内容只会在你明确加入后进入学习计划。"} actionLabel={dueCount ? "开始复习" : null} onAction={() => setSessionOpen(true)} />;
  else if (activeView === "map") content = <MasteryView candidates={data.candidates} />;
  else if (activeView === "context") content = <ContextView contextIndex={data.contextIndex} pending={contextPending} error={contextError} onScan={handleContextScan} onSelectTopic={handleTopicSelect} scanEnabled={data.runtime?.contextScanEnabled !== false} />;
  else content = <SourcesView sources={data.sources} onToggle={handleSourceToggle} />;

  return (
    <div className={`workbench-shell ${loading ? "is-loading" : ""}`}>
      <NavRail activeView={activeView} onNavigate={navigate} dueCount={dueCount} />
      <main className="workspace-main">
        {data.runtime?.mode === "demo" || !data.connected ? <div className="demo-banner"><WarningCircle size={18} weight="fill" />当前显示演示数据，不代表已扫描你的 Codex 历史。</div> : null}
        <GoalHeader goal={data.goal} sourceLabel={sourceLabel} /><div className="workspace-content">{content}</div>
      </main>
      <AssistantRail data={{ ...scopedData, summary: activeTopic?.summary || data.summary, focusPoints: activeTopic?.recentTitles?.slice(0, 3) || data.focusPoints }} onStartLearning={() => setSessionOpen(true)} />
    </div>
  );
}
