---
name: lark-md-push
description: 将本地 Markdown (.md) 极速直推/更新到飞书云文档（Docx/Wiki）。当用户需要把本地 markdown 文件上传、发布、创建、追加或同步到飞书云文档，或提到“推送到飞书”“Markdown建飞书文档”“更新飞书文档”“上传md到飞书”时使用。绕过复杂的 DocxXML 规则推理，直接通过原生 Markdown 极速直达。纯读取/下载飞书文档不适用（使用 lark-md-pull）。
metadata:
  version: "0.3.0"
  requires-bin: "lark-cli"
license: MIT
---

# 本地 Markdown 直推飞书云文档（lark-md-push）

本技能指导 AI 将本地 Markdown 文件（`.md`）以**极速、单轮命令直达**的方式推送到飞书/Lark 云文档（新建、更新覆写、安全追加或定点精准修改）。

**核心原则**：
- **拒绝链路膨胀**：不要查阅任何复杂的 DocxXML 块结构规则，严禁进入多轮格式校验推理。
- **原生 Markdown 通道**：利用 `lark-cli docs +create` 和 `lark-cli docs +update` 的 `--doc-format markdown` 原生通道直推。
- **智能防顶评论与锚点安全（Smart Guardrail & Anchor Safety）**：
  - 更新文档时，先通过轻量只读检查目标文档是否存在未解决评论（`reference_map.comments`）。
  - **无评论时**：直接执行 `--command overwrite` 全量覆写，速度最快、版面最干净。
  - **有评论时**：
    - 若需要局部修改内容：执行**定点安全编辑流程**，严禁触碰带有评论的块及其所在容器/列表，写前记录评论快照，写后校验锚点一致性。
    - 若需要大篇幅增补：仅在用户明确接受文末追加或属于新增独立章节时使用 `--command append`。严禁盲目把整篇内容 append 导致正文完全重复。

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

1. **`@file` 相对路径限制**：
   - `lark-cli` 的 `--content @file` 只接受**当前工作目录（CWD）下的相对路径**（例如 `@./doc.md` 或 `@sub/doc.md`），传绝对路径（如 `@/tmp/doc.md`）会报 `unsafe file path`。
   - 若本地文件在其他目录，先将其复制或软链到当前目录的临时相对路径（如 `./_content.md`），推完后立即清理。
2. **本地图片与附件随文直推语法**：
   - 本地 Markdown 中若包含本地图片或附件，需将路径写为基于当前工作目录的 `@./` 前缀格式：
     - 本地图片：`![图片描述](@./my-doc.assets/photo.png)`（路径含空格时写为 `![描述](<@./my-doc.assets/product shot.png>)`）。
     - 本地附件：`<source path="@./files/report.pdf"/>`。
   - `lark-cli` 导入 Markdown 时会自动解析并上传这些本地资源（不支持直接传入 Base64 Data URI）。
3. **特殊字符转义与 `--pattern` 匹配规则**：
   - 在 `--doc-format markdown` 下写入字面量特殊字符（如 `\`、`` ` ``、`*`、`_`、`[`、`]`、`$`、`~`、`<`）或行首 `#`/`-`/`+`/`>`、表格内 `|` 时，需用 `\` 转义（尤其是字面量 `<tag>` 须写为 `\<tag>`，否则会被当作 XML 富文本标签解析）。
   - `docs +fetch --doc-format markdown` 导出的文本已自动包含转义（如 `\[`、`\\`）。使用 `str_replace` 更新时，`--pattern` 与 `--content` 必须保持导出的转义形式才能精准匹配。
4. **划词评论脱锚与不可逆铁律**：
   - 飞书的划词评论严格锚定在段落 `block_id` 和文本偏移上。
   - **`overwrite` 必毁所有评论**：全量清空文档并重新生成全部 block ID，导致全篇划词批注和历史讨论全部脱锚。
   - **文本还原无法恢复锚点**：在带评论的块内或紧邻列表项执行 `str_replace`、`block_replace`、`block_insert_after`，可能触发飞书服务端重构该列表块并更换 `block_id`。一旦脱锚，**即使把文本逐字还原回去，已脱锚的评论也不会恢复锚点**！
   - **历史版本不可靠**：`docs +history-list` 返回的版本点极为稀疏，最近的编辑很可能根本不在版本历史中，**严禁向用户承诺“可以通过版本历史回退找回评论锚点”**。
5. **`append` 的代价与边界**：
   - `--command append` 是在文末追加内容。如果文档已有完整正文，盲目将整篇本地 Markdown 执行 `append` 会导致**正文整篇重复**！
   - 仅当明确属于“在文末追加新章节/附录/更新日志”，或用户明确同意文末追加时才使用。若需修改中间正文且存在评论，必须走【场景 C：定点安全编辑】。
6. **云文档（Docx/Wiki）vs 云盘原生 `.md` 文件**：
   - 本技能专用于飞书在线云文档（Docx / Wiki）。若用户明确要求将 `.md` 作为普通静态文件原样上传到飞书云盘（不转换为在线文档），应改用 `lark-cli markdown +create` / `+overwrite`。

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

### 场景 B：无评论文档更新（极速覆写）

更新文档前，先做只读轻量检测（排除截断提示项 `tips`，统计真实评论数）：
```bash
has_comments=$(lark-cli docs +fetch --doc "<doc_url_or_token>" --detail simple -q '.data.document.reference_map.comments // {} | to_entries | map(select(.key != "tips")) | length' --as user)
```

- **若 `has_comments == 0`（确认无任何未解决评论）**：
  直接执行极速全量覆写，速度最快、版面最干净：
  ```bash
  lark-cli docs +update --doc "<doc_url_or_token>" --command overwrite --doc-format markdown --content @./path/to/file.md --as user
  ```

---

### 场景 C：已有评论文档的定点安全编辑（推荐模式）

当文档已存在评论（`has_comments > 0`），且需要修改正文特定内容时，必须按以下防护步骤执行：

#### 步骤 1：写前记录评论锚点快照（必做）
先抓取当前文档的所有有效评论 key 与数据快照（注意：`docs +fetch` 默认即为 JSON 输出，直接用 `-q` 提取）：
```bash
lark-cli docs +fetch --doc "<doc_url_or_token>" --detail simple --as user \
  -q '.data.document.reference_map.comments // {} | to_entries | map(select(.key != "tips") | {key: .key, data: .value.data})' \
  > /tmp/lark_comments_before.json
```

#### 步骤 2：检查目标位置是否带有评论
用关键词定位拟修改的目标块：
```bash
lark-cli docs +fetch --doc "<doc_url_or_token>" --scope keyword --keyword "<拟修改的原文片段>" --detail with-ids --as user
```
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
3. **向用户汇报**：向用户返回文档 URL，并明确说明本次操作模式（“无评论全量覆写”、“定点安全编辑（锚点 100% 留存）”或“独立章节追加”）。
