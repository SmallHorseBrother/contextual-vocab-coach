import { useEffect, useRef, useState } from "react";
import { CheckCircle, FileText, Microphone, MicrophoneSlash, Sparkle, WarningCircle } from "@phosphor-icons/react";
import "./context-studio.css";

export function ContextStudio({ context, contextIndex, onImport, pendingImport, onScan, pendingScan, scanNotice, scanError, onOpenVocabulary, demoMode }) {
  const [text, setText] = useState("");
  const [localError, setLocalError] = useState("");
  const [notice, setNotice] = useState("");
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const recognitionRef = useRef(null);
  const canDictate = typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  const taskCount = contextIndex?.coverage?.deepAnalyzedTaskCount || contextIndex?.coverage?.tasksWithText || 0;
  const segmentCount = context?.totalSegments || 0;
  const pending = pendingImport || pendingScan;

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

  const updateMaterials = async (event) => {
    event.preventDefault();
    setNotice("");
    setLocalError("");
    const trimmed = text.trim();
    if (trimmed && trimmed.length < 20) { setLocalError("请至少说或写 20 个字符，或者留空只同步 Codex 对话。"); return; }
    if (trimmed.length > 12000) { setLocalError("单次最多 12000 个字符；提交后可以继续追加下一段。"); return; }

    let imported = null;
    if (trimmed) {
      imported = await onImport("我的补充内容", trimmed);
      if (!imported) { setLocalError("这段内容没有保存成功。你的文字仍在这里，可以直接重试。"); return; }
      setText("");
      setInterim("");
    }

    const scanned = demoMode ? null : await onScan();
    if (scanned || imported) {
      setNotice(imported
        ? `已加入第 ${imported.segmentCount} 段补充内容，并与 Codex 对话一起重新整理词表。`
        : "Codex 对话已同步，词表已经重新整理。");
    }
  };

  return <section className="context-studio" aria-labelledby="studio-title">
    <div className="studio-intro"><h2 id="studio-title">更新素材</h2><p>输入新内容，或直接同步 Codex。词表会自动重新排序。</p></div>

    <div className="material-status">
      <span>Codex 对话 <strong>{taskCount}</strong></span>
      <span>补充内容 <strong>{segmentCount} 段</strong></span>
    </div>

    <form className="studio-composer studio-composer-simple" onSubmit={updateMaterials}>
      <label htmlFor="material-text">补充最近在做的事</label>
      <textarea id="material-text" aria-label="输入或语音转写的补充内容" maxLength={12000} placeholder="随便说说最近在做的项目、遇到的问题、读到的内容或生活场景……" rows={7} value={text} onChange={(event) => setText(event.target.value)} />
      {interim ? <p className="studio-interim">正在识别：{interim}</p> : null}
      <div className="studio-input-actions"><button aria-pressed={listening} className={listening ? "is-listening" : ""} disabled={!canDictate || demoMode || pending} onClick={toggleVoice} type="button">{listening ? <MicrophoneSlash size={18} /> : <Microphone size={18} />}{listening ? "停止口述" : "语音口述"}</button><label className="studio-file"><FileText size={18} />导入 TXT / MD<input accept=".txt,.md,text/plain,text/markdown" disabled={demoMode || pending} onChange={readFile} type="file" /></label><span>{text.length} / 12000</span></div>
      {localError || scanError ? <div className="studio-error" role="alert"><WarningCircle size={17} />{localError || scanError}</div> : null}
      {notice || scanNotice ? <div className="studio-notice" role="status"><CheckCircle size={18} />{notice || scanNotice}</div> : null}
      <button className="studio-submit" disabled={pending || demoMode} type="submit"><Sparkle size={19} />{pending ? "正在更新你的素材与词表…" : text.trim() ? "加入内容并更新词表" : "同步 Codex 并更新词表"}</button>
      <p className="studio-privacy">本地优先：系统只保存词汇命中、主题与来源索引，不把你的原始内容写进公开词库。</p>
    </form>

    <div className="studio-after"><button onClick={onOpenVocabulary} type="button">返回我的词表</button><span>以后想到新内容，回到这里继续追加即可。</span></div>

    <details className="material-details">
      <summary>查看素材来源与隐私说明</summary>
      <div className="material-details-content">
        <p><strong>Codex：</strong>{taskCount ? `已索引 ${taskCount} 个对话。更新时只重读新建或发生变化的任务。` : "尚未发现可用对话；仍可只用文字、语音或文件。"}</p>
        <p><strong>补充内容：</strong>{segmentCount ? `已累计 ${segmentCount} 段。` : "还没有补充内容。"}</p>
        {context?.sources?.length ? <div className="material-source-list">{context.sources.map((source) => <span key={source.id}>{source.label} · {source.segmentCount} 段</span>)}</div> : null}
      </div>
    </details>
  </section>;
}
