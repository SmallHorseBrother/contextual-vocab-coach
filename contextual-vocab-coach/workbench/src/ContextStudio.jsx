import { useEffect, useRef, useState } from "react";
import { CheckCircle, FileText, Microphone, MicrophoneSlash, Plus, Sparkle, WarningCircle } from "@phosphor-icons/react";
import "./context-studio.css";

const SCALES = [
  { value: 500, label: "500 项", detail: "重点表达 · 先抓高复用词" },
  { value: 1000, label: "1000 项", detail: "常见场景 · 扩展基础词" },
  { value: 2500, label: "2000+ 项", detail: "细化表达 · 更多动作与描述" },
];

export function VocabularyScale({ target = 500, available = 0, pending = false, onChange }) {
  return <div className="vocabulary-scale" role="group" aria-label="选择词表规模">
    {SCALES.map((choice) => <button aria-pressed={target === choice.value} className={target === choice.value ? "is-active" : ""} disabled={pending} key={choice.value} onClick={() => onChange(choice.value)} type="button"><strong>{choice.label}</strong><span>{choice.detail}</span></button>)}
    <small>当前离线候选池 {available} 项；切换档位只改变推荐范围，不清除学习记录。</small>
  </div>;
}

export function ContextStudio({ context, vocabulary, onImport, pendingImport, onTarget, pendingTarget, onOpenVocabulary, demoMode }) {
  const [label, setLabel] = useState("我的工作与生活");
  const [text, setText] = useState("");
  const [localError, setLocalError] = useState("");
  const [notice, setNotice] = useState("");
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef(null);
  const canDictate = typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  const toggleVoice = () => {
    if (listening) { recognitionRef.current?.stop(); return; }
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { setLocalError("当前浏览器不支持网页语音识别。可使用系统语音输入，或直接粘贴文字。"); return; }
    setLocalError("");
    const instance = new Recognition();
    instance.lang = "zh-CN";
    instance.continuous = true;
    instance.interimResults = true;
    instance.onresult = (event) => {
      const finished = [];
      let partial = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finished.push(result[0].transcript);
        else partial += result[0].transcript;
      }
      if (finished.length) setText((current) => [current.trim(), ...finished].filter(Boolean).join("\n"));
      setInterim(partial);
    };
    instance.onerror = (event) => setLocalError(`语音输入已停止（${event.error}）。你可以继续打字或使用系统听写。`);
    instance.onend = () => { setListening(false); setInterim(""); recognitionRef.current = null; };
    recognitionRef.current = instance;
    try { instance.start(); setListening(true); } catch { setLocalError("没有成功启动语音输入。请检查浏览器的麦克风设置。"); }
  };

  const readFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setLocalError("");
    if (file.size > 64 * 1024) { setLocalError("单个文件请控制在 64 KB 内；较长内容可以分段添加。"); return; }
    const content = await file.text();
    if (content.length > 12000) { setLocalError("这份文字超过单次 12000 字符上限，请分段添加。"); return; }
    setText((current) => [current.trim(), content.trim()].filter(Boolean).join("\n\n"));
    event.target.value = "";
  };

  const submit = async (event) => {
    event.preventDefault();
    setNotice("");
    if (text.trim().length < 20) { setLocalError("请至少说或写 20 个字符，描述真实生活、工作或兴趣。"); return; }
    if (text.trim().length > 12000) { setLocalError("单次最多 12000 个字符；提交后可以继续追加下一段。"); return; }
    setLocalError("");
    const result = await onImport(label, text);
    if (result) {
      setText(""); setInterim("");
      setNotice(`已追加第 ${result.segmentCount} 段内容，直接关联 ${result.matchedCount} 个离线词条；词表已经重新排序。`);
    } else setLocalError("这段内容没有保存成功，请稍后重试。你输入的文字仍在这里。");
  };

  const personalWords = (vocabulary?.entries || []).filter((entry) => entry.userContextCount > 0).slice(0, 12);
  return <section className="context-studio" aria-labelledby="studio-title">
    <div className="studio-intro"><span className="eyebrow">不需要 Codex，也不需要先定学习目标</span><h2 id="studio-title">把你正在做的事，说给词表听。</h2><p>聊聊今天做了什么、在学什么、想解决什么问题。可以随意口述、粘贴笔记，或者导入文字；以后想到新内容，再追加到同一个上下文。</p></div>
    <div className="studio-layout"><form className="studio-composer" onSubmit={submit}>
      <div className="studio-step"><b>01</b><div><strong>给这一组内容起个名字</strong><span>同名内容会累积；名称只是整理用，不会限制你学哪些词。</span></div></div>
      <input aria-label="上下文名称" maxLength={80} value={label} onChange={(event) => setLabel(event.target.value)} placeholder="例如 我的工作与生活" />
      {context?.sources?.length ? <div className="studio-existing"><span>继续补充：</span>{context.sources.slice(0, 4).map((source) => <button key={source.id} onClick={() => setLabel(source.label)} type="button">{source.label}</button>)}</div> : null}
      <div className="studio-step"><b>02</b><div><strong>自由输入一段真实上下文</strong><span>想到什么就说什么，中文、英文都可以；越具体越容易找到相关词。</span></div></div>
      <textarea aria-label="输入或语音转写的上下文" maxLength={12000} placeholder="比如：我最近在做一个健康饮食产品，要向朋友介绍它的功能；下班后常自己做饭，也想练习用英语讲清楚产品思路……" rows={8} value={text} onChange={(event) => setText(event.target.value)} />
      {interim ? <p className="studio-interim">正在识别：{interim}</p> : null}
      <div className="studio-input-actions"><button aria-pressed={listening} className={listening ? "is-listening" : ""} disabled={!canDictate || demoMode} onClick={toggleVoice} type="button">{listening ? <MicrophoneSlash size={18} /> : <Microphone size={18} />}{listening ? "停止口述" : "语音口述"}</button><label className="studio-file"><FileText size={18} />导入 TXT / MD<input accept=".txt,.md,text/plain,text/markdown" disabled={demoMode} onChange={readFile} type="file" /></label><span>{text.length} / 12000 字符</span></div>
      <p className="studio-privacy">语音识别由浏览器提供，音频可能经浏览器服务处理；你可以只用文字。提交后仅在本机保留词汇命中和主题等派生信息，不保存原文。</p>
      {localError ? <div className="studio-error" role="alert"><WarningCircle size={17} />{localError}</div> : null}
      {notice ? <div className="studio-notice" role="status"><CheckCircle size={18} />{notice}</div> : null}
      <button className="studio-submit" disabled={pendingImport || demoMode} type="submit"><Sparkle size={19} />{pendingImport ? "正在整理词表…" : "追加上下文并推荐词汇"}</button>
      {demoMode ? <small>演示模式不会保存个人上下文；请启动本地真实工作台。</small> : null}
    </form><div className="studio-side"><div className="studio-scale"><div className="studio-step"><b>03</b><div><strong>决定词表有多宽</strong><span>少量抓重点，多一些就延伸到更细的表达。</span></div></div><VocabularyScale target={context?.targetSize || 500} available={vocabulary?.availableCount || 0} onChange={onTarget} pending={pendingTarget} /></div><div className="studio-sources"><h3>已经积累的上下文</h3>{context?.sources?.length ? context.sources.map((source) => <article key={source.id}><strong>{source.label}</strong><p>{source.segmentCount} 段 · {source.characterCount} 字 · 关联 {source.matchedCount} 项</p><small>{source.topicLabels.join(" / ") || "其他工作与生活"}</small></article>) : <p>还没有添加内容。先从一段随意的自我介绍开始就好。</p>}</div></div></div>
    {personalWords.length ? <div className="studio-preview"><div><span className="eyebrow">根据你的内容，优先浮出的词</span><h3>这批英语已经和你的生活连上了</h3></div><div className="studio-preview-words">{personalWords.map((word) => <span key={word.id}><strong>{word.term}</strong><small>{word.meaning}</small></span>)}</div><button onClick={onOpenVocabulary} type="button">打开完整词表 <Plus size={15} /></button></div> : null}
  </section>;
}
