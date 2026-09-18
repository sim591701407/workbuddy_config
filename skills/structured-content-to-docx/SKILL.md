---
name: structured-content-to-docx
description: Turn structured source content (JSON / Markdown / database rows / a config file) into a faithful, well-structured Word .docx via the local editor_sdk MCP — for cases where the text must be reproduced verbatim (experiment materials, questionnaires, protocol appendices, spec dumps) rather than written by an AI author. Use when the user says "把 XX 的文本内容整理成 Word", "导出成 word 文档", "分阶段/分章节整理出来", or when a doc must carry exact emphasis (bold/red) matching the source.
agent_created: true
---

# 把结构化内容忠实排版成 Word

## Purpose
源内容**已经存在**（JSON 配置、流程定义、数据库行、Markdown），用户要的是**原样整理成 Word**，
不是让 AI 另写一篇文章。核心目标是**保真**：文字一字不改、换行与层级不丢、原文的强调样式（如红色加粗）能对上。

## When to use
- 「把 X 里的文本内容整理出来，输出一个 word 文档」
- 实验材料 / 问卷 / 指导语 / 协议附录 / 软件文案 需要固化交付
- 源文件是 JSON/Markdown/代码里的字符串，需要按章节或阶段重新组织
- 原文用某种标记表达强调（如 `**…**` = 前端红色），Word 里要还原

**不适用**：从零撰写文档、按主题创作内容（那是 `tencent-docx` 插件 full_pipeline 的活）；
只做样式美化（beauty_only）；对已有 docx 做局部微调（直接用 `tencent-local-office-edit`）。

## 关键判断：Markdown 通道 vs HTML 通道

两者都走 `tencent-local-office-edit` 的 `doc_insert_*`，但保真能力不同：

| | `doc_insert_markdown` | `doc_insert_html_content` |
|---|---|---|
| 标题 | `#`→Heading1 等 | `<h1>`~`<h6>` 同样映射 |
| 表格 | 支持（GFM 语法） | 支持（基本网格） |
| **换行保真** | **连续行会被并成同一段**，源里的硬换行丢失 | 每个 `<p>` / `<br>` 就是一行的落点，**逐行可控** |
| **颜色** | 不支持 | **`<span style="color:#C00000;font-weight:bold">` 可精确设色** |
| 反引号等 | 有语义 | 无（自己转义） |

**结论：要求保真就用 HTML 通道。** 典型场景——源文本靠硬换行分行（指导语、条目列表），
且强调样式含颜色。Markdown 通道会把多行并段、且无法上色。

### 为什么不要「先 Markdown 再全局改色」
`doc_insert_markdown` 让标题 run **直接带 `bold`**（实测 `doc_get_text_property idx=0` 返回 `{"bold":true,"font_size":22}`）。
于是想用 `doc_find_and_set {"match":{"bold":true},"action":"update_property"}` 给强调文字上色时，
**标题会被一起染红**。想绕开只能在标题上做 `doc_clear_format`（会连标题级别一起清），得不偿失。
直接用 HTML 一次到位。

## 流程

### 1. 先确认「源」和「活口」
- 找到**线上真正生效**的那份数据（本例：服务端启动时直接 `open(flow/blocks.json)`，所以它就是活口，
  旁边的 `.bak_*` 全部作废）。**不要**从截图、界面文案或旧备份里抄。
- 用脚本把源解析出来，**不要手打**。原文里的标记（如 `**…**`）原样保留。

### 2. 生成 HTML（而不是 Markdown）
写一个小生成脚本，把源结构映射成受控 HTML 子集：
```python
# 标题：# ~ ######  →  <h1> ~ <h6>
# 表格：| a | b |   →  <table><tr><th>/<td>
# 连续 "1. xxx" 行 →  <ol><li>
# 其余每个非空行   →  <p>（一行一段，保住源里的硬换行）
# 强调：**x** → <span style="color:#C00000;font-weight:bold">x</span>
```
注意点：
- **`html.escape(s, quote=False)` 必须先做**，再做行内替换，否则原文里的 `<` `>`（如 `p<阶段号>_<名称>`）会破坏结构。
- 源里以 `- ` / `1. ` / `#` 开头的正文行会被误判成列表/标题 —— 生成时打印告警并人工确认；
  稳妥做法是把这类内容放在标签之后（例如写成「题干：1. 请…」而不是让 `1.` 顶在行首）。
- 别把自己的说明文字也用 `**` 加粗，否则会跟「原文强调」混在一起变成红色。

### 3. 写入并保存
```bash
cd <skill_dir_of_tencent-local-office-edit>
python3 edsdk.py call create_doc                     # → file_id
# 内容很长时用 --json-file，别把 20KB 塞进命令行
python3 edsdk.py call doc_insert_html_content --json-file args.json   # {file_id, idx:0, html_text}
python3 edsdk.py call save_file file_id=<id> file_path="<绝对路径>.docx"
```
- `args.json` 用 `json.dump({...}, ensure_ascii=False)` 写，编码问题最少。
- 先跑 `edsdk.py schema <工具名>` 再调（强制流程）。
- **不要主动 `close_file`**：用户可能正在预览面板里看。
- 保存后**必须 `present_files`** 把 docx 呈现给用户（`save_file` 不会打开预览）。

### 4. 落盘后独立校验（别只看"保存成功"）
用 `zipfile` + `ElementTree` 直接读 `word/document.xml`，核对：
```python
# 段落数 / pStyle 或 outlineLvl 分布（标题层级是否成立）
# 颜色 run 数：count(color val == 'C00000') —— 应与源里强调片段数一致
# 表格数 + 每张表的 行×列（大表要对上源里的条目总数，如 120 条 → 121 行含表头）
# 关键短语全在（取几个头尾样本 + 最长的条目 ID）
```
实测坑：可能没有 `w:pStyle`（标题靠 `w:outlineLvl` + 直接格式实现）。
**这不影响 Word 导航窗格**（它认 outline level），但**基于 Heading 样式的目录（TOC）收不到** ——
需要目录时改用 `doc_insert_paragraph_with_text` + `doc_apply_named_style`，或提前告知用户。

## 关键坑
- **不要用 `doc_get_outline` 当作内容校验**：它只给标题，不给正文，容易把"标题在、正文空"当成通过。
- **超长行会拖慢/截断命令**：`--json-file` 是标准解法；`doc_insert_markdown` 虽支持
  `markdown="file://<绝对路径>"`，但路径在 Windows 下的书写方式容易踩坑，`--json-file` 更稳。
- **命名来源要可追溯**：源数据里没有名字的条目（如某步骤 title 为空、服务端回退成裸 ID），
  补名字时**必须写明是补的**（在哪一行、依据什么），别让读者以为源里本来就有。
- **表格宽度**：HTML 表格只支持基本网格，复杂样式会丢；够用即可，不要指望合并单元格。

## 交付话术
> 文档已生成 <路径>。内容 100% 取自 <源文件>（线上生效版本），未做改写；
> 原文的强调片段已按前端渲染方式设为红色加粗。第 X 章是 120 条任务题全量清单。
