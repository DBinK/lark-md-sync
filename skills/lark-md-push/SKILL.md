---
name: lark-md-push
description: 将本地 Markdown (.md) 极速直推/更新到飞书云文档（Docx/Wiki）。当用户需要把本地 markdown 文件上传、发布、创建、追加或同步到飞书云文档时使用。绕过复杂的 DocxXML 规则推理，直接通过原生 Markdown 极速直达。
metadata:
  version: "0.1.0"
  requires-bin: "lark-cli"
license: MIT
---

# 本地 Markdown 直推飞书云文档（lark-md-push）

本技能指导 AI 将本地 Markdown 文件（`.md`）以**极速、单轮命令直达**的方式推送到飞书/Lark 云文档（新建或更新/追加）。

**核心原则**：
- **拒绝链路膨胀**：不要查阅任何复杂的 DocxXML 块结构规则，严禁进入多轮格式校验推理。
- **原生 Markdown 通道**：利用 `lark-cli docs +create` 和 `lark-cli docs +update` 的 `--doc-format markdown` 原生通道直推。
- **文件直传**：长文本或多行 Markdown 优先使用 `@./path/to/file.md` 或临时相对路径传参，规避 shell 转义损坏。

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
- **更新文档权威指引**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-update.md
  ```
- **CLI 原生帮助兜底**：随时运行 `lark-cli docs +create --help` 或 `lark-cli docs +update --help`。

---

## 1. 核心铁律与避坑

1. **`@file` 路径限制**：
   - `lark-cli` 的 `--content @file` 只接受**当前工作目录下的相对路径**（例如 `@./doc.md` 或 `@sub/doc.md`），绝对路径（如 `@/tmp/doc.md`）会报 `unsafe file path`。
   - 若本地文件在其他路径，可将其复制或软链到当前目录的临时相对路径（如 `./_content.md`），推完后清理。
2. **更新模式选择**：
   - **追加内容**（默认推荐）：`--command append --doc-format markdown --content @./path.md`。
   - **整篇重写**（全量覆盖）：`--command overwrite --doc-format markdown --content @./path.md`（注意：`overwrite` 会重新生成 block ID，远端原有划词批注和历史评论会丢失，仅在用户明确要求覆盖时使用）。
3. **本地图片引用支持**：
   - Markdown 中的本地图片写为 `![alt](@./relative/path.png)`，`lark-cli` 在导入 Markdown 时会自动解析并上传当前工作目录下的本地图片。

---

## 2. 标准操作流程

### 场景 A：新建飞书云文档（导入 Markdown）

直接一步完成创建，并可选指定标题与目标目录：

```bash
# 1. 基础创建（标题从 Markdown 首行提取，或显式指定 --title）
lark-cli docs +create --title "文档标题" --doc-format markdown --content @./path/to/file.md --as user

# 2. 创建到指定云盘文件夹或知识库（Wiki）节点
lark-cli docs +create --title "文档标题" --parent-token "<folder_or_wiki_token>" --doc-format markdown --content @./path/to/file.md --as user
```

命令返回 JSON，提取 `data.document_id` 或 `data.url` 即为生成的飞书云文档链接。

---

### 场景 B：更新或追加到已有云文档

用户提供已有飞书云文档 URL 或 token：

```bash
# 1. 追加到文档末尾（最常用、最安全，不破坏已有内容与评论）
lark-cli docs +update --doc "<doc_url_or_token>" --command append --doc-format markdown --content @./path/to/file.md --as user

# 2. 全量覆盖现有文档（仅在用户明确指示全量覆盖/重写时使用）
lark-cli docs +update --doc "<doc_url_or_token>" --command overwrite --doc-format markdown --content @./path/to/file.md --as user
```

---

## 3. 验证与反馈

执行完毕后：
1. 检查返回的 JSON 中是否包含 `"ok": true`。
2. 向用户返回创建或更新后的飞书文档 URL / token。
