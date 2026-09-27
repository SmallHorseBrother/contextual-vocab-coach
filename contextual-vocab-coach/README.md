# 语境英语 · Contextual Vocab Coach

把你真实做过、说过、写过的内容，自动整理成一份与你有关的英语词表。

它会把本机 Codex 对话和你额外补充的文字、语音转写或 TXT/Markdown 文件视为同一份学习素材；上下文分类默认隐藏，只在需要追溯来源或筛选时出现。你可以选择 500、1000 或 2000+ 项推荐范围，但只有主动点击“加入学习”的表达才会进入复习。

## 一分钟开始

### 有 Codex：自动读取本机对话

在 PowerShell 中运行：

```powershell
git clone https://github.com/SmallHorseBrother/contextual-vocab-coach.git "$env:USERPROFILE\.codex\skills\contextual-vocab-coach"
cd "$env:USERPROFILE\.codex\skills\contextual-vocab-coach"
python scripts\workbench_server.py
```

然后打开 <http://127.0.0.1:4174/>。第一次启动会在本机索引 Codex 历史；原始对话不会写进词汇库，只保留词汇命中、主题与来源索引等派生信息。

也可以直接在 Codex 里说：

> 打开 contextual-vocab-coach 工作台，扫描我的最新对话并生成词表。

### 没有 Codex：粘贴或口述自己的内容

把项目克隆到任意目录后运行：

```powershell
python scripts\workbench_server.py --no-context-scan
```

打开工作台，进入“我的素材”，粘贴一段最近的工作、学习、兴趣或生活内容；也可以使用语音口述或导入 `.txt` / `.md`。以后有新内容，继续追加并点击一次“加入内容并更新词表”即可。

## 最简单的使用方式

1. 打开“我的词表”，先浏览系统推荐的 500 项重点表达。
2. 想补充或更新时，只进入“我的素材”：Codex 对话和手动内容会一起处理。
3. 搜索想学的词，点击“加入学习”；不要一次把几百个词全加入复习。
4. 在“今日学习”或“复习”里做主动回忆；在“词汇地图”里查看新词与已有表达的关系。

词表规模是推荐视图，不会清空学习记录：

- `500`：优先保留高相关、高复用表达。
- `1000`：扩展常见场景和基础词。
- `2000+`：实际目标为 2500 项，加入更细的动作、描述和领域表达。

## 数据与隐私

- 默认数据位置：Windows 为 `%LOCALAPPDATA%\contextual-vocab-coach\state.json`；macOS/Linux 为 `$XDG_DATA_HOME/contextual-vocab-coach/state.json` 或 `~/.local/share/contextual-vocab-coach/state.json`。
- 服务只绑定 `127.0.0.1`，不会公开到局域网或互联网。
- Codex 扫描只把用户消息作为学习证据，不把助手或工具输出当成你的事实。
- 手动补充内容用于本地派生词汇关系，原文不会持久化进学习状态。
- 断开本地服务时，界面会明确显示“连接已断开”，不会用演示词表冒充个人数据。

## 开发与验证

工作台源码位于 `workbench/`。修改前端后运行：

```powershell
cd workbench
npm ci
npm run build
npm run test:sites
cd ..
python -m unittest discover -s tests -p "test_*.py"
```

更完整的 Agent 行为、数据命令和隐私边界请看 [SKILL.md](SKILL.md)、[本地存储说明](references/store-cli.md) 与 [隐私说明](references/privacy.md)。
