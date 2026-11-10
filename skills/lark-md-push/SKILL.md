---
name: lark-md-push
description: 将本地 Markdown (.md) 极速直推/更新到飞书云文档（Docx/Wiki）。当用户需要把本地 markdown 文件上传、发布、创建、追加或同步到飞书云文档时使用。绕过复杂的 DocxXML 规则推理，直接通过原生 Markdown 极速直达。
metadata:
  version: "0.2.0"
  requires-bin: "lark-cli"
license: MIT
---

# 本地 Markdown 直推飞书云文档（lark-md-push）

本技能指导 AI 将本地 Markdown 文件（`.md`）以**极速、单轮命令直达**的方式推送到飞书/Lark 云文档（新建或更新/追加）。

**核心原则**：
- **拒绝链路膨胀**：不要查阅任何复杂的 DocxXML 块结构规则，严禁进入多轮格式校验推理。
- **原生 Markdown 通道**：利用 `lark-cli docs +create` 和 `lark-cli docs +update` 的 `--doc-format markdown` 原生通道直推。
- **智能防顶评论（Smart Guardrail）**：
  - 更新文档时，先通过轻量只读检查目标文档是否存在未解决评论（`reference_map.comments`）。
  - **无评论时**：直接执行 `--command overwrite` 全量覆写，速度最快、版面最干净。
  - **有评论时**：严格退回 `--command append` 追加模式（或先提示用户），严禁使用 `overwrite` 误伤划词批注与讨论历史。

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
2. **评论保护与覆写判断规则**：
   - 飞书的划词评论严格锚定在 `block_id` 上。`overwrite` 会清空整篇文档并重新生成全部 block ID，导致历史评论全部丢失。
   - 更新文档前，运行只读检查：
     ```bash
     lark-cli docs +fetch --doc "<doc_token>" --detail simple --json -q '.data.document.reference_map.comments // {} | length'
     ```
     - **返回 `0`（无评论）**：直接使用 `--command overwrite` 全量覆写，速度最快。
     - **返回 `> 0`（存在评论）**：**禁止使用 overwrite**，自动降级为 `--command append` 追加，并告知用户“文档存在评论，已自动采用追加模式以保全评论”。

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

### 场景 B：更新已有云文档（智能覆写/追加）

当用户需要把本地 Markdown 同步到已有飞书文档时：

1. **第一步：快速检测有无评论**
   ```bash
   has_comments=$(lark-cli docs +fetch --doc "<doc_url_or_token>" --detail simple --json -q '.data.document.reference_map.comments // {} | length')
   ```

2. **第二步：根据评论状态决定指令**
   - **Case 1：无评论 (`has_comments == 0`) ➔ 极速全量覆写**：
     ```bash
     lark-cli docs +update --doc "<doc_url_or_token>" --command overwrite --doc-format markdown --content @./path/to/file.md --as user
     ```
   - **Case 2：有评论 (`has_comments > 0`) ➔ 安全追加模式**：
     ```bash
     lark-cli docs +update --doc "<doc_url_or_token>" --command append --doc-format markdown --content @./path/to/file.md --as user
     ```
     *(并在输出中向用户说明：文档包含划词评论，为避免评论丢失，已采用追加模式更新)*

---

## 3. 验证与反馈

执行完毕后：
1. 检查返回的 JSON 中是否包含 `"ok": true`。
2. 向用户返回文档链接，并明确说明本次是“无评论极速覆写”还是“有评论安全追加”。
