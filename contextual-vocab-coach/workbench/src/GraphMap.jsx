import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { BubbleSetsPlugin } from "cytoscape-bubblesets";
import {
  ArrowsOut, Check, CheckCircle, ClockCounterClockwise, MagnifyingGlass,
  Minus, Plus, ShareNetwork, Sparkle, WarningCircle, X,
} from "@phosphor-icons/react";
import "./graph.css";

const RELATIONS = {
  same_scene: "同场景", component: "组成", similar: "近义",
  collocation: "搭配", contrast: "对比", prerequisite: "先修",
};
const STATUS = {
  available: "待选择", proposed: "待选择", test: "等待短测",
  learning: "正在学习", known: "已经会了", not_now: "近期不用",
};
const DOMAIN_META = {
  product: { label: "产品与用户", color: "#288f75", x: 260, y: 335 },
  research: { label: "AI 研究", color: "#c99636", x: 650, y: 265 },
  life: { label: "生活与健康", color: "#54a884", x: 1030, y: 325 },
  engineering: { label: "工程与运维", color: "#168b91", x: 680, y: 585 },
  robotics: { label: "具身智能", color: "#8371c7", x: 1060, y: 675 },
  content: { label: "内容创作", color: "#4e92c8", x: 245, y: 715 },
  everyday: { label: "日常表达", color: "#839caf", x: 640, y: 875 },
};

function domainFor(node) {
  const topics = node.primaryContextId ? [node.primaryContextId] : (node.contextIds || []);
  if (topics.includes("product-startup") || topics.includes("product-building")) return "product";
  if (topics.includes("ai-research")) return "research";
  if (topics.includes("engineering-ops") || topics.includes("engineering-infra") || topics.includes("engineering")) return "engineering";
  if (topics.includes("embodied-ai")) return "robotics";
  if (topics.includes("content-creation")) return "content";
  if (topics.includes("food-health")) return "life";
  if (topics.includes("english-learning")) return "everyday";
  const scenarios = node.scenarioIds || [];
  if (scenarios.some((id) => ["work", "digital"].includes(id))) return "engineering";
  if (scenarios.some((id) => ["study"].includes(id))) return "research";
  if (scenarios.some((id) => ["health", "food", "home", "weather"].includes(id))) return "life";
  if (scenarios.some((id) => ["shopping", "travel", "transport"].includes(id))) return "content";
  return "everyday";
}

function nodeScore(node, degree) {
  return (node.isNew ? 460 : 0) + (["learning", "test"].includes(node.status) ? 260 : 0)
    + (node.sourceType === "contextual" ? 320 : 0)
    + (node.term.includes(" ") ? 42 : 0)
    + Math.min(Math.log1p(node.taskCount || 0) * 8, 55)
    + Math.min(degree || 0, 10) * 7;
}

function graphElements(graph, density, domain, phase, relationType, pinnedNodeId) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const degree = new Map();
  edges.filter((edge) => edge.status !== "ignored").forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
  });
  const groups = new Map();
  nodes.forEach((node) => {
    const key = domainFor(node);
    if (domain !== "all" && key !== domain && node.id !== pinnedNodeId) return;
    if (phase === "before" && (graph?.lastAddedIds || []).includes(node.id)) return;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(node);
  });
  const neighbourIds = new Set();
  edges.forEach((edge) => {
    if (edge.source === pinnedNodeId) neighbourIds.add(edge.target);
    if (edge.target === pinnedNodeId) neighbourIds.add(edge.source);
  });
  const visible = [];
  groups.forEach((items) => {
    items.sort((a, b) => nodeScore(b, degree.get(b.id)) - nodeScore(a, degree.get(a.id)) || a.term.localeCompare(b.term));
    const cap = density === "all" ? Infinity : density === "more" ? 22 : 6;
    const chosen = items.filter((node, index) => index < cap || node.id === pinnedNodeId || neighbourIds.has(node.id));
    visible.push(...chosen);
  });
  const visibleIds = new Set(visible.map((node) => node.id));
  const elements = [];
  const grouped = new Map();
  visible.forEach((node) => {
    const key = domainFor(node);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(node);
  });
  grouped.forEach((items, key) => {
    const meta = DOMAIN_META[key];
    elements.push({ data: { id: `domain:${key}`, domain: key, label: meta.label, count: nodes.filter((node) => domainFor(node) === key).length, color: meta.color }, position: { x: meta.x - 55, y: meta.y - 65 }, classes: "domain-node" });
    items.forEach((node, index) => {
      const angle = index * 2.3999632297;
      const radius = 68 + 32 * Math.sqrt(index);
      const size = node.id === pinnedNodeId ? 36 : node.isNew ? 28 : nodeScore(node, degree.get(node.id)) > 250 ? 26 : 18;
      elements.push({
        data: { id: node.id, domain: key, term: node.term, meaning: node.meaning, label: node.term,
          color: meta.color, size, isNew: node.isNew, status: node.status },
        position: { x: meta.x + Math.cos(angle) * radius, y: meta.y + Math.sin(angle) * radius },
        classes: `vocab-node ${node.isNew ? "new-node" : ""} ${node.status === "learning" ? "learning-node" : ""}`,
      });
    });
  });
  edges.forEach((edge) => {
    if (edge.status === "ignored" || !visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return;
    if (relationType !== "all" && edge.type !== relationType) return;
    elements.push({
      data: { id: edge.id, source: edge.source, target: edge.target, label: RELATIONS[edge.type] || edge.type, type: edge.type, status: edge.status },
      classes: `relation-edge ${edge.status === "suggested" ? "suggested-edge" : "confirmed-edge"}`,
    });
  });
  return { elements, visibleCount: visible.length, domainCount: grouped.size };
}

function graphStyle() {
  return [
    { selector: "node.domain-node", style: {
      "background-color": "data(color)", "width": 30, "height": 30,
      "border-color": "#fffefa", "border-width": 4,
      "label": "data(label)", "font-size": 22, "font-weight": 700, "color": "data(color)",
      "text-valign": "center", "text-halign": "left", "text-margin-x": -14,
      "text-background-color": "#fffefa", "text-background-opacity": 0.85,
      "text-background-padding": 4, "text-background-shape": "round-rectangle",
    } },
    { selector: "node.vocab-node", style: {
      "background-color": "data(color)", "width": "data(size)", "height": "data(size)",
      "border-width": 3, "border-color": "#fffefa", "label": "data(label)",
      "font-size": 15, "font-weight": 600, "color": "#1a3446", "text-valign": "bottom", "text-halign": "center",
      "text-margin-y": 11, "text-wrap": "wrap", "text-max-width": 110,
      "text-background-color": "#fffefa", "text-background-opacity": 0.84,
      "text-background-padding": 2, "text-background-shape": "round-rectangle",
      "overlay-opacity": 0,
    } },
    { selector: "node.learning-node", style: { "border-color": "#d4a143", "border-width": 4 } },
    { selector: "node.new-node", style: { "border-color": "#528fe1", "border-width": 5, "shadow-blur": 18, "shadow-color": "#5aa6e7", "shadow-opacity": 0.55 } },
    { selector: "node.is-selected", style: { "width": 44, "height": 44, "border-color": "#dff2ee", "border-width": 7, "font-size": 18, "font-weight": 700, "z-index": 100 } },
    { selector: "edge.relation-edge", style: {
      "curve-style": "bezier", "line-color": "#9ebeb7", "width": 1.45,
      "opacity": 0.56, "label": "", "font-size": 10, "color": "#648193",
      "text-background-color": "#fffefa", "text-background-opacity": 0.85,
      "text-background-padding": 1, "text-rotation": "autorotate", "z-index": 2,
    } },
    { selector: "edge.suggested-edge", style: { "line-style": "dashed", "line-color": "#438ada", "opacity": 0.84, "width": 1.8 } },
    { selector: "edge.is-near-selected", style: { "label": "data(label)", "opacity": 0.88, "z-index": 20 } },
    { selector: "edge.is-selected", style: { "line-color": "#087462", "width": 3.3, "opacity": 1, "font-size": 11, "font-weight": 700, "z-index": 90 } },
  ];
}

export function GraphMap({ graph, topics = [], onScan, onOpenStudio, hasCodexTasks, pendingScan, onAdd, pendingAdd, onSeen, selectedNodeId, selectedEdgeId, onSelectNode, onSelectEdge, scanError, phase, onPhase }) {
  const [domain, setDomain] = useState("all");
  const [density, setDensity] = useState("overview");
  const [relationType, setRelationType] = useState("all");
  const [query, setQuery] = useState("");
  const [pinnedNodeId, setPinnedNodeId] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [newTerm, setNewTerm] = useState("");
  const [newMeaning, setNewMeaning] = useState("");
  const [newTopicId, setNewTopicId] = useState("");
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const computed = useMemo(() => graphElements(graph, density, domain, phase, relationType, pinnedNodeId), [graph, density, domain, phase, relationType, pinnedNodeId]);
  const searchResults = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return term ? (graph?.nodes || []).filter((node) => `${node.term} ${node.meaning}`.toLocaleLowerCase().includes(term)).slice(0, 7) : [];
  }, [graph, query]);

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const cy = cytoscape({
      container: containerRef.current,
      elements: computed.elements,
      style: graphStyle(), layout: { name: "preset", fit: true, padding: 48 },
      minZoom: 0.15, maxZoom: 2.8, wheelSensitivity: 0.18,
      boxSelectionEnabled: false, autoungrabify: true,
    });
    cyRef.current = cy;
    let bubbleSets = null;
    if (density !== "all") {
      bubbleSets = new BubbleSetsPlugin(cy);
      Object.entries(DOMAIN_META).forEach(([key, meta]) => {
        const members = cy.nodes().filter((node) => node.data("domain") === key);
        if (members.length < 2) return;
        const links = cy.edges().filter((edge) => edge.source().data("domain") === key && edge.target().data("domain") === key);
        bubbleSets.addPath(members, links, null, { style: { fill: meta.color, fillOpacity: "0.045", stroke: meta.color, strokeOpacity: "0.3", strokeWidth: "1", strokeDasharray: "3 5" }, virtualEdges: true });
      });
    }
    cy.on("tap", "node.vocab-node", (event) => onSelectNode(event.target.id()));
    cy.on("tap", "edge.relation-edge", (event) => onSelectEdge(event.target.id()));
    if (selectedNodeId) cy.$id(selectedNodeId).addClass("is-selected");
    if (selectedEdgeId) cy.$id(selectedEdgeId).addClass("is-selected");
    const observer = new ResizeObserver(() => cy.resize());
    observer.observe(containerRef.current);
    return () => { observer.disconnect(); bubbleSets?.destroy(); cy.destroy(); cyRef.current = null; };
  }, [computed.elements, onSelectNode, onSelectEdge, density]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.nodes(".vocab-node").removeClass("is-selected");
    cy.edges().removeClass("is-selected is-near-selected");
    const node = selectedNodeId ? cy.$id(selectedNodeId) : null;
    const edge = selectedEdgeId ? cy.$id(selectedEdgeId) : null;
    if (node?.length) { node.addClass("is-selected"); node.connectedEdges().addClass("is-near-selected"); }
    if (edge?.length) edge.addClass("is-selected");
  }, [selectedNodeId, selectedEdgeId, computed.elements]);

  useEffect(() => {
    if (!pinnedNodeId) return;
    const cy = cyRef.current;
    const target = cy?.$id(pinnedNodeId);
    if (target?.length) cy.animate({ center: { eles: target }, zoom: Math.max(cy.zoom(), 0.9) }, { duration: 350 });
  }, [pinnedNodeId, computed.elements]);

  const selectSearchResult = (node) => {
    setDomain("all"); onPhase("after"); setQuery(""); setPinnedNodeId(node.id); onSelectNode(node.id);
  };
  const zoom = (factor) => {
    const cy = cyRef.current;
    if (cy) cy.animate({ zoom: Math.min(2.8, Math.max(0.15, cy.zoom() * factor)) }, { duration: 220 });
  };
  const fit = () => cyRef.current?.fit(undefined, 48);
  const freshCount = graph?.unseenCount || 0;
  const submitNew = async (event) => {
    event.preventDefault();
    if (!newTerm.trim() || !newMeaning.trim()) return;
    const saved = await onAdd({ term: newTerm, meaning: newMeaning, topicId: newTopicId });
    if (saved) { setAddOpen(false); setNewTerm(""); setNewMeaning(""); setNewTopicId(""); }
  };

  return <section className="graph-experience" aria-labelledby="graph-title">
    <div className="graph-toolbar">
      <button className="graph-scan-button" disabled={hasCodexTasks && pendingScan} onClick={hasCodexTasks ? onScan : onOpenStudio} type="button">{hasCodexTasks ? <ClockCounterClockwise size={18} /> : <Plus size={18} />}{hasCodexTasks ? (pendingScan ? "正在扫描并接入…" : "扫描最新对话") : "添加上下文"}</button>
      <button className="graph-add-button" aria-expanded={addOpen} onClick={() => setAddOpen((value) => !value)} type="button"><Plus size={16} />添加表达</button>
      <select aria-label="按知识领域筛选" value={domain} onChange={(event) => setDomain(event.target.value)}><option value="all">全部领域</option>{Object.entries(DOMAIN_META).map(([id, meta]) => <option key={id} value={id}>{meta.label}</option>)}</select>
      <div className="graph-density" aria-label="图谱密度">{[["overview", "重点"], ["more", "扩展"], ["all", "全部"]].map(([id, label]) => <button aria-pressed={density === id} className={density === id ? "is-active" : ""} key={id} onClick={() => setDensity(id)} type="button">{label}</button>)}</div>
      <label className="graph-search"><MagnifyingGlass size={18} /><input aria-label="搜索图谱词汇" placeholder="搜索词汇或中文意思…" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      {searchResults.length ? <div className="graph-search-results">{searchResults.map((node) => <button key={node.id} onClick={() => selectSearchResult(node)} type="button"><strong>{node.term}</strong><small>{node.meaning}</small></button>)}</div> : null}
      {addOpen ? <form className="graph-add-form" onSubmit={submitNew}><strong>添加到个人词表与图谱</strong><label>英文表达<input autoFocus maxLength={80} placeholder="例如 continuous delivery" required value={newTerm} onChange={(event) => setNewTerm(event.target.value)} /></label><label>中文含义<input maxLength={80} placeholder="例如 持续交付" required value={newMeaning} onChange={(event) => setNewMeaning(event.target.value)} /></label><label>相关领域（可选）<select value={newTopicId} onChange={(event) => setNewTopicId(event.target.value)}><option value="">自动判断</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.label}</option>)}</select></label><div><button disabled={pendingAdd} type="submit">{pendingAdd ? "接入中…" : "接入图谱"}</button><button onClick={() => setAddOpen(false)} type="button">取消</button></div></form> : null}
    </div>
    {scanError ? <div className="graph-error" role="alert"><WarningCircle size={18} />{scanError}</div> : null}
    <div className="graph-stage">
      <div className="graph-intro"><span className="eyebrow">你的表达，正在形成自己的网络</span><h2 id="graph-title"><ShareNetwork size={28} weight="duotone" />我的英语知识图谱</h2><p>{graph?.nodes?.length || 0} 个词与表达 · {graph?.edges?.filter((edge) => edge.status !== "ignored").length || 0} 条有依据的关系</p></div>
      <div className="graph-legend-card"><strong>学习状态</strong><span><i className="graph-dot dot-learn" />正在学习</span><span><i className="graph-dot dot-new" />本次新增</span><span><i className="graph-line" />已有关系</span><span><i className="graph-line dashed" />待核对关系</span></div>
      {freshCount ? <div className="graph-new-tray"><Sparkle size={20} weight="duotone" /><div><strong>待查看的新表达 {freshCount} 个</strong><span>已尝试寻找邻居；有依据的虚线关系可逐条核对。</span></div><button onClick={() => onSeen(null)} type="button">看过本次新增</button></div> : <div className="graph-new-tray is-quiet"><CheckCircle size={19} /><div><strong>词汇网络已更新</strong><span>下次添加内容发现的新表达会在这里亮起。</span></div></div>}
      <div className="graph-canvas" ref={containerRef} role="img" aria-label={`可缩放的词汇知识图谱，当前显示 ${computed.visibleCount} 个表达，分布在 ${computed.domainCount} 个领域`} />
      <div className="graph-controls"><button aria-label="放大图谱" onClick={() => zoom(1.35)} type="button"><Plus size={19} /></button><button aria-label="缩小图谱" onClick={() => zoom(0.75)} type="button"><Minus size={19} /></button><button aria-label="适合屏幕" onClick={fit} type="button"><ArrowsOut size={18} /></button></div>
      <div className="graph-relation-filter"><span>关系</span><select aria-label="按关系类型筛选" value={relationType} onChange={(event) => setRelationType(event.target.value)}><option value="all">全部关系</option>{Object.entries(RELATIONS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></div>
      <div className="graph-timeline"><span>最近一次更新</span><div className="graph-timeline-buttons"><button className={phase === "before" ? "is-active" : ""} disabled={!graph?.lastAddedCount} onClick={() => onPhase("before")} type="button">更新前</button><button className={phase === "after" ? "is-active" : ""} onClick={() => onPhase("after")} type="button">更新后</button></div><small>显示 {computed.visibleCount} / {graph?.nodes?.length || 0} 个节点</small></div>
    </div>
  </section>;
}

export function GraphInspector({ graph, selectedNodeId, selectedEdgeId, onSelectEdge, onRelation, pendingEdgeId, onSeen, phase }) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const node = nodes.find((item) => item.id === selectedNodeId) || nodes.find((item) => item.term === "deployment pipeline") || nodes[0];
  const nodeNotYetAdded = phase === "before" && (graph?.lastAddedIds || []).includes(node?.id);
  const notYetAdded = new Set(phase === "before" ? graph?.lastAddedIds || [] : []);
  const related = node ? edges.filter((edge) => edge.status !== "ignored" && !notYetAdded.has(edge.source) && !notYetAdded.has(edge.target) && (edge.source === node.id || edge.target === node.id)).sort((a, b) => (a.status === "suggested" ? -1 : 1) - (b.status === "suggested" ? -1 : 1) || b.confidence - a.confidence) : [];
  const edge = related.find((item) => item.id === selectedEdgeId) || related[0];
  const other = edge ? nodes.find((item) => item.id === (edge.source === node.id ? edge.target : edge.source)) : null;
  const [chosenType, setChosenType] = useState("");
  useEffect(() => { setChosenType(edge?.type || "same_scene"); }, [edge?.id, edge?.type]);
  return <aside className="assistant-rail graph-inspector" aria-label="词汇关系说明">
    <header><h2>图谱助手</h2><p>词汇之间的联系，可追溯、可调整</p></header>
    <section className="graph-inspector-progress"><div className="assistant-section-title"><Sparkle size={21} weight="duotone" /><strong>新词如何接入</strong></div><ol><li className="is-done">发现新表达</li><li className="is-done">寻找现有邻居</li><li className="is-done">根据线索推断关系</li><li className={graph?.suggestedCount ? "is-current" : "is-done"}>核对不确定的关系</li></ol><p>本地词表中有 {nodes.length} 个节点，{graph?.suggestedCount || 0} 条关系待核对。</p></section>
    {nodeNotYetAdded ? <section className="graph-inspector-empty"><ClockCounterClockwise size={25} /><strong>更新前尚无这个表达</strong><p>切换到“更新后”，查看它进入图谱的位置与新建立的连接。</p></section> : node ? <section className="graph-inspector-node"><span className="graph-inspector-kicker">当前词汇 {node.isNew ? "· 本次新增" : ""}</span><h3>{node.term}</h3><p>{node.meaning}</p><div className="graph-inspector-tags"><span>{STATUS[node.status] || node.status}</span><span>{node.sourceType === "contextual" ? "领域表达" : node.taskCount ? `见于 ${node.taskCount} 项任务` : "基础词表"}</span></div>{node.isNew ? <button className="graph-seen-single" onClick={() => onSeen([node.id])} type="button"><Check size={15} />标记这个词已看</button> : null}</section> : null}
    {!nodeNotYetAdded && edge && other ? <section className="graph-relation-detail"><span className="graph-inspector-kicker">{edge.status === "suggested" ? "待核对的连接" : edge.status === "confirmed" ? "已确认的连接" : "根据线索推断的连接"}</span><div className="graph-relation-pair"><strong>{node.term}</strong><span>↔</span><strong>{other.term}</strong></div><div className="graph-relation-type"><span>关系类型</span><strong>{RELATIONS[edge.type] || edge.type}</strong><span>规则线索 {Math.round(edge.confidence * 100)} 分</span></div><h4>为什么联系在一起？</h4><p>{edge.reason}</p><div className="graph-evidence"><strong>依据</strong><span>{edge.evidence}</span></div><label className="graph-type-edit">调整关系类型<select aria-label="调整关系类型" value={chosenType} onChange={(event) => setChosenType(event.target.value)}>{Object.entries(RELATIONS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><div className="graph-inspector-actions"><button className="graph-accept" disabled={pendingEdgeId === edge.id || edge.status === "confirmed"} onClick={() => onRelation(edge.id, "accept")} type="button"><Check size={17} />{edge.status === "confirmed" ? "已确认" : "接受关系"}</button><button disabled={pendingEdgeId === edge.id} onClick={() => chosenType === edge.type ? onRelation(edge.id, "ignore") : onRelation(edge.id, "change_type", chosenType)} type="button">{chosenType === edge.type ? <><X size={17} />忽略</> : "保存类型"}</button></div></section> : !nodeNotYetAdded ? <section className="graph-inspector-empty"><ShareNetwork size={25} /><strong>{node ? "暂未找到可靠连接" : "选择图上的词或连线"}</strong><p>{node ? "这个表达仍会留在词表中。后续扫描、补充领域线索或新增表达后，可再次寻找关系。" : "这里会解释联系的依据，也能调整不准确的关系。"}</p></section> : null}
    {!nodeNotYetAdded && related.length > 1 ? <section className="graph-neighbours"><h4>附近的表达</h4>{related.slice(0, 7).map((item) => { const peer = nodes.find((entry) => entry.id === (item.source === node.id ? item.target : item.source)); return peer ? <button className={edge?.id === item.id ? "is-active" : ""} key={item.id} onClick={() => onSelectEdge(item.id)} type="button"><span>{peer.term}</span><small>{RELATIONS[item.type]}{item.status === "suggested" ? " · 待核对" : ""}</small></button> : null; })}</section> : null}
    <p className="graph-inspector-footnote">新旧只表示发现时间；是否掌握由你的学习记录决定。</p>
  </aside>;
}
