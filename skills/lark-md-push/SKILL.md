---
name: lark-md-push
description: >-
  凡需要将本地文件同步到飞书云文档，或直接在线修改、更新、增补飞书云文档（Docx / Wiki）正文内容时，优先使用本技能——即使用户只说“更新飞书文档”“改一下飞书这段话”“增量同步”“保留原评论修改”，而未提到“Markdown”或“.md”。覆盖：本地 .md 发布新建、空白或无远端变更时的极速覆写，以及保留已有评论、划词批注、高亮样式与远端手动改动前提下的增量同步。不适用于：纯读取摘要（走 lark-doc）、导出本地（走 lark-md-pull）、飞书云盘原生 .md 静态文件（走 lark-markdown），或仅操作文档内画板与思维笔记（走 lark-doc）。
metadata:
  version: "0.5.0"
  requires-bin: "lark-cli"
license: MIT
---

# 本地 Markdown 直推飞书云文档（lark-md-push）

本技能指导 AI 将本地 Markdown 文件（`.md`）以**高效、保真、安全**的方式推送到飞书/Lark 云文档（新建、极速覆写、增量保真同步、含评论定点编辑）。

**核心原则**：
- **拒绝链路膨胀**：新建文档或确认无远端变更/样式时，直接走 `--doc-format markdown` 原生通道直推，不做多余推理。
- **远端变更感知与增量保真同步（Remote-Aware Incremental Sync）**：
  - 更新已有文档前，必须先用 `lark-cli docs +fetch --doc "<doc>" --doc-format xml --detail full --as user` 一次探测远端评论、非 Markdown 样式/扩展块与正文内容（注：`--doc-format markdown` 会忽略 `--detail full`，看不到背景高亮和块 ID）。
  - **写前自动版本备份**：对非空已有云文档执行任何写操作前，先主动调用飞书版本接口保存一个命名备份版本（格式：`<简短修改动机> 改动前备份版本`）。
  - **Markdown 无法表达的样式/扩展块**（文字背景高亮 `background-color`、文字颜色 `text-color`、下划线 `<u>`、高亮块 `<callout>`、分栏 `<grid>`、画板等）：推送时通过块级增量更新尽可能保留；**不提示**合并回本地 `.md`。
  - **Markdown 可表达的内容与格式**（标题、正文增删改、列表/表格/代码块、链接，以及**加粗**、斜体、行内代码、删除线等）：推送时保留远端非冲突改动（双向冲突块先请用户确认），并在完成后列出差异**提示用户是否将飞书端变更合并回本地 `.md`**。
- **有评论时的锚点安全**：若存在未解决评论（`reference_map.comments`），在增量保真同步基础上额外叠加写前/写后评论快照校验与禁碰带评论列表规则；仅当明确属于文末新增独立章节时才用 `--command append`。

---

## 首次触发自检：官方 Skills 路由协同（不阻塞主任务）

在**当前会话第一次**触发本技能时，顺手用极轻量命令检查本机已安装的 `lark-doc` / `lark-drive` / `lark-wiki` 的 `SKILL.md` 是否已包含**最新版本的** `lark-md-sync-routing` 标记（`version=0.5.0`，探测路径与详细流程见 [`references/official-skills-routing-patch.md`](references/official-skills-routing-patch.md)）。
- **已注入且版本最新**：静默跳过。
- **未注入或版本过期**：**不打断当前推送任务**；在任务结束后向用户**强烈建议注入/更新**协同路由：“检测到官方 `lark-doc` / `lark-drive` / `lark-wiki` 尚未注入（或版本过期）防脱锚与路由引导。若不注入，后续口述「更新/修改飞书文档」时极易直接命中官方技能导致评论脱锚，**强烈建议回复「注入」按参考文档原地幂等写入**（带来源与版本注释，随时可精准卸载或用 `lark-cli skills read` 一键还原官方原版）”。禁止未经用户确认直接修改官方 Skill 文件。

---

## 0. 协议防断裂指针（CRITICAL：以 lark-cli 本地 Skill 为权威）

`lark-cli` 的 CLI 参数与协议可能随版本迭代升级。**严禁把参数硬编码视为永久真理**。
执行前如遇参数疑问或异常，必须按需检视本地绑定的权威指引：

- **Markdown 语法与转义规范**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-md.md
  ```
- **创建文档权威指引**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-create.md
  ```
- **更新文档权威指引（含 block 指令规范）**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-update.md
  ```
- **CLI 原生帮助兜底**：随时运行 `lark-cli docs +create --help` 或 `lark-cli docs +update --help`。

---

## 1. 核心铁律与避坑（CRITICAL）

1. **严禁对非空已有文档盲目 `overwrite`**：
   - 即使 `has_comments == 0`，远端文档仍可能包含人工添加的文字背景高亮、文字颜色、扩展块或线上增删改。
   - **探测必须用 `--doc-format xml --detail full`**：`--doc-format markdown` 会忽略 `--detail full`（不导出 `background-color`、`text-color` 与 `block_id`），不能用于样式与变更探测。
   - 仅当目标文档为空文档、或经探测确认「无评论 + 无非 Markdown 样式/扩展块 + 无未合并的远端内容改动」、或用户显式授权强制覆写时，才允许使用 `--command overwrite`。
2. **`@file` 相对路径限制**：
   - `lark-cli` 的 `--content @file` 只接受**当前工作目录（CWD）下的相对路径**（例如 `@./doc.md` 或 `@sub/doc.md`），传绝对路径（如 `@/tmp/doc.md`）会报 `unsafe file path`。
   - 若本地文件在其他目录，先将其复制或软链到当前目录的临时相对路径（如 `./_content.md`），推完后立即清理。
3. **本地图片与附件随文直推语法**：
   - 本地 Markdown 中若包含本地图片或附件，需将路径写为基于当前工作目录的 `@./` 前缀格式：
     - 本地图片：`![图片描述](@./my-doc.assets/photo.png)`（路径含空格时写为 `![描述](<@./my-doc.assets/product shot.png>)`）。
     - 本地附件：`<source path="@./files/report.pdf"/>`。
   - `lark-cli` 导入 Markdown 时会自动解析并上传这些本地资源（不支持直接传入 Base64 Data URI）。
4. **特殊字符转义与 `--pattern` 匹配规则**：
   - 在 `--doc-format markdown` 下写入字面量特殊字符（如 `\`、`` ` ``、`*`、`_`、`[`、`]`、`$`、`~`、`<`）或行首 `#`/`-`/`+`/`>`、表格内 `|` 时，需用 `\` 转义（尤其是字面量 `<tag>` 须写为 `\<tag>`，否则会被当作 XML 富文本标签解析）。
   - `docs +fetch --doc-format markdown` 导出的文本已自动包含转义（如 `\[`、`\\`）。使用 `str_replace` 更新时，`--pattern` 与 `--content` 必须保持导出的转义形式才能精准匹配。
5. **划词评论脱锚与不可逆铁律**：
   - 飞书的划词评论严格锚定在段落 `block_id` 和文本偏移上。
   - **`overwrite` 必毁所有评论**：全量清空文档并重新生成全部 block ID，导致全篇划词批注和历史讨论全部脱锚。
   - **文本还原无法恢复锚点**：在带评论的块内或紧邻列表项执行 `str_replace`、`block_replace`、`block_insert_after`，可能触发飞书服务端重构该列表块并更换 `block_id`。一旦脱锚，**即使把文本逐字还原回去，已脱锚的评论也不会恢复锚点**！
   - **历史版本不可靠**：`docs +history-list` 返回的版本点极为稀疏，最近的编辑很可能根本不在版本历史中，**严禁向用户承诺“可以通过版本历史回退找回评论锚点”**。
6. **`append` 的代价与边界**：
   - `--command append` 是在文末追加内容。如果文档已有完整正文，盲目将整篇本地 Markdown 执行 `append` 会导致**正文整篇重复**！
   - 仅当明确属于“在文末追加新章节/附录/更新日志”，或用户明确同意文末追加时才使用。若需修改中间正文，必须走增量同步或【场景 C：定点安全编辑】。
7. **云文档（Docx/Wiki）vs 云盘原生 `.md` 文件**：
   - 本技能专用于飞书在线云文档（Docx / Wiki）。若用户明确要求将 `.md` 作为普通静态文件原样上传到飞书云盘（不转换为在线文档），应改用 `lark-cli markdown +create` / `+overwrite`。
8. **写前备份版本与权限边界**：
   - 对非空已有文档执行任何写入前，应先调用 `lark-cli api POST "/open-apis/drive/v1/files/<document_id>/versions"` 创建快照，`name` 用简短一句话说明修改动机，格式为 `<简短修改动机> 改动前备份版本`，`obj_type` 固定为 `"docx"`。
   - 备份版本用于保全改前正文与样式，**不能替代**有评论时的锚点保护流程（恢复版本仍可能影响评论锚点）。
   - 若调用返回 `missing_scope`（缺少 `drive:drive:version`），**不得静默忽略**：需告知用户运行 `lark-cli auth login --scope "drive:drive:version"` 补齐权限，或先向用户确认本次是否跳过备份继续写入。

---

## 2. 标准操作流程

### 场景 A：新建飞书云文档（导入 Markdown）

直接一步完成创建，并可选指定标题与目标目录：

```bash
# 1. 基础创建（标题从 Markdown 首行提取，或显式指定 --title）
lark-cli docs +create --title "文档标题" --doc-format markdown --content @./path/to/file.md --as user

# 2. 创建到指定云盘文件夹或知识库（Wiki）节点
lark-cli docs +create --title "文档标题" --parent-token "<folder_or_wiki_token>" --doc-format markdown --content @./path/to/file.md --as user

# 3. 创建到知识库“我的空间”（个人知识库位置）
lark-cli docs +create --title "文档标题" --parent-position my_library --doc-format markdown --content @./path/to/file.md --as user
```

命令返回 JSON，提取 `data.document.document_id` 或 `data.document.url` 即为生成的飞书云文档链接（同时留意 `data.warnings` 是否存在降级提示）。

---

### 场景 B：更新已有云文档（先探测，再分流）

更新已有云文档前，先执行一次全量 XML 探测（同时拿到评论、非 Markdown 样式、扩展块、正文与 `block_id`）：
```bash
lark-cli docs +fetch --doc "<doc_url_or_token>" --doc-format xml --detail full --as user > /tmp/lark_remote_before.json
has_comments=$(jq -r '.data.document.reference_map.comments // {} | to_entries | map(select(.key != "tips")) | length' /tmp/lark_remote_before.json)
```

检查 `/tmp/lark_remote_before.json` 中的 `data.document.content`：
1. **真实评论数**（`has_comments`）；
2. **文档是否为空，或是否包含非 Markdown 样式/扩展块**（如 `background-color`、`text-color`、`<u>`、`<callout>`、`<grid>`、`<whiteboard>`、`<cite>` 等）；
3. **远端标题、正文与 Markdown 可表达格式**（如 `<b>` 加粗、`<em>` 斜体、`<code>` 行内代码、`<a>` 链接、增删段落/列表项）与本地 `.md` 的差异。

#### 写前必做：保存改动前备份版本（空文档可跳过）
在执行分支 B1、分支 B2 或场景 C 的任何写操作前，先基于 `/tmp/lark_remote_before.json` 中的 `document_id` 保存一个命名备份版本：
```bash
doc_id=$(jq -r '.data.document.document_id' /tmp/lark_remote_before.json)
lark-cli api POST "/open-apis/drive/v1/files/${doc_id}/versions" \
  --data '{"name": "<简短修改动机> 改动前备份版本", "obj_type": "docx"}' \
  --as user
```
- 若返回 `missing_scope`（缺少 `drive:drive:version`），停止写入并提示用户补齐授权（`lark-cli auth login --scope "drive:drive:version"`）或确认跳过本次备份。

按探测结果分流：

#### 分支 B1：极速全量覆写（`overwrite`）
仅当 `has_comments == 0`，且满足以下任一条件时执行：
- 目标文档为空文档；
- 经检查无任何非 Markdown 样式/扩展块，且无未合并的远端独立内容改动；
- 用户显式指定“强制全量覆写”。

```bash
lark-cli docs +update --doc "<doc_url_or_token>" --command overwrite --doc-format markdown --content @./path/to/file.md --as user
```

#### 分支 B2：无评论但有远端样式或内容改动 → 增量保真同步（默认安全路径）
当 `has_comments == 0` 但远端存在背景高亮/颜色/扩展块或文字改动时，**禁止 `overwrite`**，按以下规则做增量同步：
1. **保留未改动块**：文字未变化的块绝对不触碰（天然保留其背景高亮、文字颜色等一切样式）。
2. **最小化增量写入**：仅对真正需要变更的块执行 `str_replace` / `block_replace` / `block_insert_after` / `block_delete`；若被修改的块自身带有 `background-color` / `text-color` 等行内样式，优先用 `str_replace` 仅替换变化文本，或用 XML `block_replace` 保留原有 `<span background-color="...">` 等样式属性。
3. **远端差异分类处理**：
   - **仅非 Markdown 样式差异**（文字背景高亮、文字颜色、下划线等）：推送时保留，**无需提示回写本地 `.md`**。
   - **Markdown 可表达的内容/格式差异**（改标题、改正文、增删条目、加粗/斜体/代码/链接变更）：
     - 同一块发生**双向冲突**（飞书与本地均改过）：暂停覆盖该冲突块，向用户展示两端差异并确认取舍后再写入。
     - 属于**远端非冲突改动**：推送时保留该改动，并在同步完成后汇总差异清单，**主动询问用户是否将飞书端的变更合并回本地 `.md`**（仅在用户确认后修改本地文件）。

---

### 场景 C：已有评论文档的定点安全编辑（推荐模式）

当文档已存在评论（`has_comments > 0`），且需要修改正文特定内容时（**无论来源于本地文件同步还是纯在线口述修改**），在遵循**分支 B2 增量保真同步**的基础上，**额外叠加**以下评论防脱锚闭环：

#### 步骤 1：写前记录评论锚点快照（必做）
从已拉取的 `/tmp/lark_remote_before.json` 提取所有有效评论 key 与数据快照：
```bash
jq -r '.data.document.reference_map.comments // {} | to_entries | map(select(.key != "tips") | {key: .key, data: .value.data})' \
  /tmp/lark_remote_before.json > /tmp/lark_comments_before.json
```

#### 步骤 2：检查目标位置是否带有评论
在 `/tmp/lark_remote_before.json` 中定位拟修改的目标块（或用 `--scope keyword --keyword "<原文>" --detail with-ids` 复核）：
- **检查红线**：
  - 若命中块包含 `comment-refs="c..."` 属性，或该块处于带有 `comment-refs` 的有序/无序列表容器内：**严禁直接对该 block 执行 `str_replace`、`block_replace` 或在该列表内 `block_insert_after`**！
  - **安全替代方案**：改在整个列表容器外部新增独立说明段落（例如在列表父级块后 `block_insert_after`，插入 `> **补充说明**：...`），绕过带评论列表。
- **允许编辑范围**：
  - 只有确认目标块自身无 `comment-refs`，且其所在的父级列表/容器完全无任何评论时，才允许执行局部的 `str_replace` 或 `block_replace`：
    ```bash
    # 单处简单行内文本替换（注意 --pattern 须保持转义一致性）
    lark-cli docs +update --doc "<doc_url_or_token>" --command str_replace --doc-format markdown --pattern '旧内容' --content '新内容' --as user

    # 针对无评论独立 block 的替换
    lark-cli docs +update --doc "<doc_url_or_token>" --command block_replace --block-id "<block_id>" --doc-format markdown --content @./_patch.md --as user
    ```

#### 步骤 3：写后锚点比对与即时校验（必做）
写操作完成后，立即重新获取评论快照并比对：
```bash
lark-cli docs +fetch --doc "<doc_url_or_token>" --detail simple --as user \
  -q '.data.document.reference_map.comments // {} | to_entries | map(select(.key != "tips") | {key: .key, data: .value.data})' \
  > /tmp/lark_comments_after.json

# 比对前后数量与锚点数据
diff -u /tmp/lark_comments_before.json /tmp/lark_comments_after.json
```
- **校验判定**：
  - 若 diff 为空（评论 key 与内容完全一致）：说明修改安全，评论锚点毫发无损。
  - 若有 key 消失：说明发生了评论脱锚，**必须立即终止后续写入并向用户告警脱锚情况**。

---

## 3. 验证与反馈

执行写操作后，必须通过以下检查：
1. **接口状态与警告检查**：返回的 JSON 中必须包含 `"ok": true` 且 `data.result` 为 `"success"`（创建时检查 `data.document.document_id`），同时检查 `data.warnings` 是否有未完全处理的降级警告。
2. **评论锚点一致性**：若原文档有评论，比对写前与写后的 `/tmp/lark_comments_before.json` 与 `/tmp/lark_comments_after.json`，确保评论总数与 ID 无任何丢失。
3. **向用户汇报**：
   - 返回文档 URL，并明确说明本次操作模式（“无远端变更极速覆写”、“增量保真同步（保留远端高亮与改动）”、“含评论定点安全编辑（锚点 100% 留存）”或“独立章节追加”）。
   - 汇报已创建的改前备份版本名称/ID（若因空文档跳过或缺少 `drive:drive:version` 权限跳过，也需明确说明）。
   - 若检测到飞书端存在 Markdown 可表达的文字或格式变更（如改了标题、增删正文、加粗等），清晰列出差异并**询问用户是否需要合并回本地 `.md`**（非 Markdown 样式如背景高亮则不提示回写）。
