import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
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
import { addGraphExpression, addLibraryEntry, decideCandidate, fetchWorkbenchState, markGraphSeen, recordReview, scanCodexContext, setSourceStatus, updateGraphRelation } from "./api.js";
import { GraphInspector, GraphMap } from "./GraphMap.jsx";
import { FEEDBACK_CONFIRMATIONS, FEEDBACK_ORDER, getSessionPrompt, nextSessionStep } from "./sessionFlow.js";

const NAV_ITEMS = [
  { id: "today", label: "今日学习", icon: House },
  { id: "vocabulary", label: "我的词表", icon: Books },
  { id: "review", label: "复习", icon: ClockCounterClockwise },
  { id: "map", label: "词汇地图", icon: ShareNetwork },
  { id: "sources", label: "来源与扫描", icon: Database },
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

function GoalHeader({ goal, subtitle }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="goal-header">
      <div className="goal-switcher">
        <span className="eyebrow">长期学习方向</span>
        <button aria-expanded={menuOpen} className="goal-title" type="button" aria-label="查看学习方向" onClick={() => setMenuOpen((value) => !value)}>
          {goal?.statement || "把我日常正在做的事，用英语表达出来"}
          <CaretDown size={24} weight="bold" />
        </button>
        <p>{subtitle || "系统会自动从你的真实任务中整理词表"}</p>
        {menuOpen ? <div className="goal-menu"><strong>{goal?.statement || "把我日常正在做的事，用英语表达出来"}</strong><span>{goal?.successDefinition || "遇到熟悉场景时，能直接调用合适的英文表达。"}</span><small>上下文默认隐藏，只用于推荐、分类和来源追溯。</small></div> : null}
      </div>
      <div className="goal-promise">
        <Sparkle size={22} weight="duotone" />
        <span>从真实对话中，<br />收集值得学习的英语。</span>
      </div>
    </header>
  );
}

const LIBRARY_STATUS_LABELS = {
  available: "加入学习",
  learning: "正在学习",
  test: "等待短测",
  known: "已经会了",
  not_now: "近期不用",
  proposed: "加入学习",
};

function PersonalVocabularyView({ vocabulary, pendingId, pendingScan, scanNotice, scanError, onAdd, onSpeak, onScan, onShowScanDetails }) {
  const [query, setQuery] = useState("");
  const [context, setContext] = useState("");
  const [level, setLevel] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [visibleCount, setVisibleCount] = useState(120);
  const entries = vocabulary?.entries || [];
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const filtered = entries.filter((entry) => {
    if (context && !(entry.contextIds || []).includes(context)) return false;
    if (level && entry.level !== level) return false;
    if (sourceType && entry.sourceType !== sourceType) return false;
    if (!normalizedQuery) return true;
    return [entry.term, entry.meaning, ...(entry.scenarioLabels || []), ...(entry.contextLabels || [])].join(" ").toLocaleLowerCase().includes(normalizedQuery);
  });
  const visible = filtered.slice(0, visibleCount);

  return (
    <section className="library-view" aria-labelledby="vocabulary-heading">
      <div className="vocabulary-hero">
        <div><span className="eyebrow">自动整理 · 上下文默认隐藏</span><h2 id="vocabulary-heading">{vocabulary?.uniqueTermCount || 0} 个个人英语表达</h2><p>这是扫描后形成的完整静态词表。你不需要先选主题；搜索、学习即可，需要时再按上下文筛选或查看来源。</p></div>
        <button className="vocabulary-update" disabled={pendingScan} onClick={onScan} type="button"><ClockCounterClockwise size={20} weight="bold" />{pendingScan ? "正在扫描全部任务…" : "更新词表"}</button>
      </div>
      {scanNotice ? <div className="scan-notice" role="status"><CheckCircle size={19} weight="fill" />{scanNotice}</div> : null}
      {scanError ? <div className="context-error" role="alert"><WarningCircle size={20} weight="fill" />{scanError}</div> : null}
      <div className="vocabulary-stats">
        <div><strong>{vocabulary?.entryCount || 0}</strong><span>词义记录</span></div>
        <div><strong>{vocabulary?.contextualCount || 0}</strong><span>领域表达</span></div>
        <div><strong>{vocabulary?.observedCount || 0}</strong><span>历史中直接命中</span></div>
        <button onClick={onShowScanDetails} type="button">查看扫描与分类详情 →</button>
      </div>
      <div className="library-controls">
        <label className="library-search"><MagnifyingGlass size={19} /><input aria-label="搜索我的词表" value={query} onChange={(event) => { setQuery(event.target.value); setVisibleCount(120); }} placeholder="搜索英文或中文…" /></label>
        <select aria-label="按上下文筛选" value={context} onChange={(event) => { setContext(event.target.value); setVisibleCount(120); }}><option value="">全部上下文</option>{(vocabulary?.contexts || []).map((item) => <option key={item.id} value={item.id}>{item.label} · {item.wordCount}</option>)}</select>
        <select aria-label="按词表来源筛选" value={sourceType} onChange={(event) => { setSourceType(event.target.value); setVisibleCount(120); }}><option value="">全部来源</option><option value="contextual">领域表达</option><option value="observed">历史中出现</option><option value="foundation">基础表达</option></select>
        <select aria-label="按难度筛选" value={level} onChange={(event) => { setLevel(event.target.value); setVisibleCount(120); }}><option value="">全部难度</option>{(vocabulary?.levels || []).map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </div>
      <div className="library-result-line"><span>找到 {filtered.length} 项</span><small>{vocabulary?.updatedAt ? `词表更新于 ${formatScanTime(vocabulary.updatedAt)}` : "等待首次扫描"}</small></div>
      <div className="library-grid">
        {visible.map((entry) => {
          const available = entry.status === "available";
          return <article className="library-card" key={entry.id}>
            <div className="library-copy">
              <div className="library-term"><strong>{entry.term}</strong><button className="speak-button" onClick={() => onSpeak(entry.term)} type="button" aria-label={`朗读 ${entry.term}`}><SpeakerHigh size={18} /></button></div>
              <p>{entry.meaning}</p>
              <div className="library-tags">{entry.level ? <span className={`level-tag level-${entry.level.toLowerCase()}`}>{entry.level}</span> : null}<span>{entry.sourceType === "contextual" ? "领域表达" : entry.sourceType === "observed" ? `历史中出现 · ${entry.taskCount}` : "基础表达"}</span></div>
              {(entry.contextLabels || []).length || (entry.recentTitles || []).length ? <details className="word-source"><summary>查看来源</summary><p>{(entry.contextLabels || []).length ? `相关分类：${entry.contextLabels.join("、")}` : ""}{(entry.recentTitles || []).length ? ` · 最近任务：${entry.recentTitles.join("、")}` : ""}</p></details> : null}
            </div>
            <button className={`library-add ${available || entry.status === "proposed" ? "" : "is-added"}`} disabled={(!available && entry.status !== "proposed") || pendingId === entry.id} onClick={() => onAdd(entry)} type="button">{available || entry.status === "proposed" ? <Plus size={17} weight="bold" /> : <Check size={17} weight="bold" />}{LIBRARY_STATUS_LABELS[entry.status] || entry.status}</button>
          </article>;
        })}
      </div>
      {visible.length < filtered.length ? <button className="load-more" onClick={() => setVisibleCount((count) => count + 120)} type="button">再显示 {Math.min(120, filtered.length - visible.length)} 项</button> : null}
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

  if (!current) return <EmptyPanel icon={BookOpenText} title="没有等待复习的内容" body="当前没有到期项目。可以回到我的词表，选择想学的表达。" actionLabel={`返回${returnLabel}`} onAction={onExit} />;

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

const MAP_STATUS = [
  { status: "learning", label: "正在学习" },
  { status: "test", label: "等待短测" },
  { status: "known", label: "已经会了" },
  { status: "proposed", label: "待选择" },
  { status: "not_now", label: "近期不用" },
];

function MasteryView({ candidates, topics = [], coverage = {}, vocabularyCount = 0 }) {
  const topicById = new Map(topics.map((topic) => [topic.id, topic]));
  const topicIds = [...new Set(candidates.map((item) => item.topicId || "uncategorized"))];
  const mapTopics = topicIds.map((topicId) => {
    const topic = topicById.get(topicId);
    return {
      id: topicId,
      label: topic?.label || candidates.find((item) => (item.topicId || "uncategorized") === topicId)?.sourceLabel || "其他表达",
      focus: topic?.focus || "跨任务可复用的英语表达",
      taskCount: topic?.taskCount || 0,
      items: candidates.filter((item) => (item.topicId || "uncategorized") === topicId),
    };
  }).sort((left, right) => right.items.length - left.items.length || right.taskCount - left.taskCount);
  const discoveredTaskCount = coverage.deepAnalyzedTaskCount || coverage.discoveredTaskCount || 0;

  return (
    <section className="mastery-view" aria-labelledby="mastery-heading">
      <div className="list-view-heading"><ShareNetwork size={30} weight="duotone" /><div><span className="eyebrow">从真实任务到可用英语</span><h2 id="mastery-heading">我的词汇关系地图</h2><p>{vocabularyCount} 个个人表达保存在完整词表中；这里把与真实任务直接相关的 {candidates.length} 个重点表达按主题和学习状态连起来。</p></div></div>
      <div className="mastery-legend" aria-label="学习状态图例">
        {MAP_STATUS.map((item) => {
          const count = candidates.filter((candidate) => candidate.status === item.status).length;
          return <span className={`legend-${item.status}`} key={item.status}><i aria-hidden="true" />{item.label}<b>{count}</b></span>;
        })}
      </div>
      <div className="mastery-map">
        <div className="mastery-root-node">
          <ShareNetwork size={28} weight="duotone" aria-hidden="true" />
          <div><span>真实使用场景</span><strong>{discoveredTaskCount} 个 Codex 任务</strong><small>用户消息在本机扫描，原文不写入学习档案</small></div>
          <b>{mapTopics.length} 个主题路径</b>
        </div>
        <div className="mastery-topic-grid">
          {mapTopics.map((topic) => (
            <article className="mastery-topic-branch" key={topic.id}>
              <header className="mastery-topic-node">
                <div><span>主题节点</span><h3>{topic.label}</h3><p>{topic.focus}</p></div>
                <b>{topic.items.length} 个表达</b>
              </header>
              <div className="mastery-word-branches">
                {topic.items.map((item) => {
                  const status = MAP_STATUS.find((entry) => entry.status === item.status);
                  return (
                    <div className={`mastery-word-node status-${item.status}`} key={item.id}>
                      <i aria-hidden="true" />
                      <div><strong>{item.term}</strong><small>{item.meaning}</small></div>
                      <span>{status?.label || item.status}</span>
                    </div>
                  );
                })}
              </div>
              <footer>{topic.taskCount ? `${topic.taskCount} 个任务提供了这个主题的使用背景` : "来自已整理的学习来源"}</footer>
            </article>
          ))}
        </div>
      </div>
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

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

function ContextView({ contextIndex, pending, error, onScan, scanEnabled }) {
  const coverage = contextIndex?.coverage || {};
  const topics = contextIndex?.topics || [];
  const tasks = contextIndex?.tasks || [];
  const [taskFilter, setTaskFilter] = useState("all");
  const visibleTasks = tasks.filter((task) => taskFilter === "all" || task.topicId === taskFilter).slice(0, 80);

  return (
    <section className="context-view" aria-labelledby="context-heading">
      <div className="context-hero">
        <div>
          <span className="eyebrow">本机 Codex 上下文索引</span>
          <h2 id="context-heading">不只看当前对话，看见你的完整任务版图</h2>
          <p>首次扫描会逐条读取所有任务中的用户消息。原始对话不写入词汇库，更新时只重读新增或变化的任务。</p>
        </div>
        <button className="context-scan-button" disabled={pending || !scanEnabled} onClick={onScan} type="button">
          <ClockCounterClockwise size={20} weight="bold" />
          {pending ? "正在扫描…" : scanEnabled ? "更新词表" : "演示模式不可扫描"}
        </button>
      </div>
      {error ? <div className="context-error" role="alert"><WarningCircle size={20} weight="fill" />{error}</div> : null}
      <div className="coverage-strip">
        <div><strong>{coverage.discoveredTaskCount || 0}</strong><span>发现的唯一任务</span></div>
        <div><strong>{coverage.titledTaskCount || 0}</strong><span>已建立标题索引</span></div>
        <div><strong>{coverage.fullContentScannedTaskCount || coverage.deepAnalyzedTaskCount || 0}</strong><span>完整扫描用户消息</span></div>
        <div><strong>{formatBytes(coverage.contentBytesIndexed)}</strong><span>已索引历史数据</span></div>
      </div>
      <div className="coverage-note">
        <CheckCircle size={19} weight="duotone" />
        <span>{coverage.scope || "等待首次扫描"} · 本次重读 {coverage.newOrChangedTaskCount || 0} 个、复用 {coverage.reusedContentTaskCount || 0} 个 · 原文持久化：{coverage.rawContentStored ? "是" : "否"} · 更新于 {formatScanTime(contextIndex?.indexedAt)}</span>
      </div>
      <div className="context-section-heading">
        <div><h3>自动分类</h3><p>这些分类默认隐藏，只用于筛选、推荐和来源追溯，不会限制你的完整词表。</p></div>
      </div>
      <div className="topic-grid">
        {topics.map((topic) => (
          <article className="topic-card" key={topic.id}>
            <span className="topic-card-top"><strong>{topic.label}</strong><b>{topic.taskCount} 个任务</b></span>
            <p>{topic.focus}</p>
            <span className="topic-meta">相关词 {topic.wordCount || topic.candidateCount} · 内容扫描 {topic.deepAnalyzedCount} · 最近 {formatScanTime(topic.lastActiveAt)}</span>
            <span className="topic-examples">{(topic.recentTitles || []).slice(0, 3).join(" · ")}</span>
          </article>
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
            <span className={`deep-dot ${task.deepAnalyzed ? "is-deep" : ""}`} title={task.deepAnalyzed ? "用户消息已完整扫描" : "仅元数据"} />
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
  const [activeView, setActiveView] = useState("vocabulary");
  const [sessionOpen, setSessionOpen] = useState(false);
  const [pendingLibraryId, setPendingLibraryId] = useState(null);
  const [contextPending, setContextPending] = useState(false);
  const [contextError, setContextError] = useState("");
  const [contextNotice, setContextNotice] = useState("");
  const [graphSelection, setGraphSelection] = useState({ nodeId: null, edgeId: null });
  const [graphPhase, setGraphPhase] = useState("after");
  const [pendingGraphEdgeId, setPendingGraphEdgeId] = useState(null);
  const [pendingGraphAdd, setPendingGraphAdd] = useState(false);
  const graph = data.knowledgeGraph;
  const defaultGraphNodeId = graph?.nodes?.find((node) => node.term === "deployment pipeline")?.id || graph?.nodes?.[0]?.id || null;
  const selectedGraphNodeId = graphSelection.nodeId && graph?.nodes?.some((node) => node.id === graphSelection.nodeId) ? graphSelection.nodeId : defaultGraphNodeId;
  const selectGraphNode = useCallback((nodeId) => setGraphSelection({ nodeId, edgeId: null }), []);
  const selectGraphEdge = useCallback((edgeId) => setGraphSelection((current) => ({ ...current, edgeId })), []);
  const scopedCandidates = data.candidates;
  const scannedTaskCount = data.contextIndex?.coverage?.deepAnalyzedTaskCount || 0;
  const dueCount = useMemo(() => data.dueCount ?? data.candidates.filter((item) => item.status === "learning").length, [data]);

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

  const handleVocabularyAdd = async (entry) => {
    setPendingLibraryId(entry.id);
    const remote = entry.candidateId
      ? await decideCandidate(entry.candidateId, "learning")
      : await addLibraryEntry(entry.lexiconEntryId || entry.id);
    if (remote) updateLocal({ ...remote, connected: true });
    setPendingLibraryId(null);
  };

  const handleContextScan = async () => {
    setContextPending(true);
    setContextError("");
    setContextNotice("");
    const previousCount = data.personalVocabulary?.entryCount || 0;
    const remote = await scanCodexContext();
    if (remote) {
      updateLocal({ ...remote, connected: true });
      setGraphPhase("after");
      const nextCount = remote.personalVocabulary?.entryCount || 0;
      const added = Math.max(0, nextCount - previousCount);
      const coverage = remote.contextIndex?.coverage || {};
      setContextNotice(`词表已更新：共 ${nextCount} 条记录，新增 ${added} 条；本次重读 ${coverage.newOrChangedTaskCount || 0} 个新建或变化的任务。`);
    }
    else setContextError("扫描没有完成。请确认当前运行的是真实工作台，并稍后重试。");
    setContextPending(false);
  };

  const handleGraphRelation = async (edgeId, action, type = null) => {
    setPendingGraphEdgeId(edgeId);
    const remote = await updateGraphRelation(edgeId, action, type);
    if (remote) updateLocal({ ...remote, connected: true });
    else setContextError("关系没有保存成功，请稍后重试。");
    setPendingGraphEdgeId(null);
  };

  const handleGraphSeen = async (nodeIds) => {
    const remote = await markGraphSeen(nodeIds);
    if (remote) updateLocal({ ...remote, connected: true });
    else setContextError("新词状态没有保存成功，请稍后重试。");
  };

  const handleGraphAdd = async ({ term, meaning, topicId }) => {
    setPendingGraphAdd(true);
    setContextError("");
    const remote = await addGraphExpression(term, meaning, topicId);
    if (remote) {
      updateLocal({ ...remote, connected: true });
      setGraphPhase("after");
      const inserted = remote.knowledgeGraph?.nodes?.find((node) => node.term.toLocaleLowerCase() === term.trim().toLocaleLowerCase() && node.meaning === meaning.trim());
      if (inserted) selectGraphNode(inserted.id);
    }
    else setContextError("没有添加成功。请检查英文表达和中文含义后重试。");
    setPendingGraphAdd(false);
    return Boolean(remote);
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
  const returnLabel = { today: "今日学习", vocabulary: "我的词表", review: "复习", map: "词汇地图", context: "扫描详情", sources: "来源管理" }[activeView] || "工作台";
  const scopedData = { ...data, candidates: scopedCandidates };
  let content;
  if (sessionOpen) content = <LearningSession sessionItems={sessionItems} onExit={() => setSessionOpen(false)} onReview={handleReview} onSpeak={speak} returnLabel={returnLabel} />;
  else if (activeView === "vocabulary") content = <PersonalVocabularyView vocabulary={data.personalVocabulary} pendingId={pendingLibraryId} pendingScan={contextPending} scanNotice={contextNotice} scanError={contextError} onAdd={handleVocabularyAdd} onSpeak={speak} onScan={handleContextScan} onShowScanDetails={() => setActiveView("context")} />;
  else if (activeView === "today") content = <EmptyPanel icon={Target} title="今天最值得学的英语" body="先完成到期复习，再从完整个人词表中加入少量真正想学的表达。" actionLabel="开始今天的学习" onAction={() => setSessionOpen(true)} />;
  else if (activeView === "review") content = <EmptyPanel icon={ListChecks} title={`${dueCount} 项等待复习`} body={dueCount ? "复习会更换措辞或使用场景，检查你是否真正能够迁移使用。" : "今天没有到期项目。新内容只会在你明确加入后进入学习计划。"} actionLabel={dueCount ? "开始复习" : null} onAction={() => setSessionOpen(true)} />;
  else if (activeView === "map") content = <GraphMap graph={graph} topics={data.contextIndex?.topics || []} onScan={handleContextScan} pendingScan={contextPending} onAdd={handleGraphAdd} pendingAdd={pendingGraphAdd} onSeen={handleGraphSeen} selectedNodeId={selectedGraphNodeId} selectedEdgeId={graphSelection.edgeId} onSelectNode={selectGraphNode} onSelectEdge={selectGraphEdge} scanError={contextError} phase={graphPhase} onPhase={setGraphPhase} />;
  else if (activeView === "context") content = <ContextView contextIndex={data.contextIndex} pending={contextPending} error={contextError} onScan={handleContextScan} scanEnabled={data.runtime?.contextScanEnabled !== false} />;
  else content = <SourcesView sources={data.sources} onToggle={handleSourceToggle} />;

  return (
    <div className={`workbench-shell ${loading ? "is-loading" : ""} ${activeView === "map" && !sessionOpen ? "is-map" : ""}`}>
      <NavRail activeView={activeView} onNavigate={navigate} dueCount={dueCount} />
      <main className="workspace-main">
        {data.runtime?.mode === "demo" || !data.connected ? <div className="demo-banner"><WarningCircle size={18} weight="fill" />当前显示演示数据，不代表已扫描你的 Codex 历史。</div> : null}
        <GoalHeader goal={data.goal} subtitle={`已自动整理 ${data.personalVocabulary?.uniqueTermCount || 0} 个表达，覆盖 ${scannedTaskCount} 个 Codex 任务`} /><div className="workspace-content">{content}</div>
      </main>
      {activeView === "map" && !sessionOpen
        ? <GraphInspector graph={graph} selectedNodeId={selectedGraphNodeId} selectedEdgeId={graphSelection.edgeId} onSelectEdge={selectGraphEdge} onRelation={handleGraphRelation} pendingEdgeId={pendingGraphEdgeId} onSeen={handleGraphSeen} phase={graphPhase} />
        : <AssistantRail data={{ ...scopedData, summary: `完整词表已综合基础英语、领域表达和 ${scannedTaskCount} 个任务的扫描结果。`, focusPoints: ["上下文默认隐藏，不需要先选择主题", "更新词表时优先处理最新和变化的任务", "只有主动加入的表达才进入复习队列"] }} onStartLearning={() => setSessionOpen(true)} />}
    </div>
  );
}
