# ⚡ lark-md-sync

[![skills.sh](https://skills.sh/b/DBinK/lark-md-sync)](https://skills.sh/DBinK/lark-md-sync)
[![GitHub stars](https://img.shields.io/github/stars/DBinK/lark-md-sync?style=flat&color=yellow)](https://github.com/DBinK/lark-md-sync/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Compatible](https://img.shields.io/badge/Compatible-Any_Agent-8A2BE2)](README.md#-怎么使用)
[![Performance](https://img.shields.io/badge/Token_Saved-90%25+-brightgreen)](README.md#-为什么需要-lark-md-sync)

> **专为 AI Coding Agents 打造的本地 Markdown (`.md`) ↔ 飞书云文档极速读写套件。**  
> 一行命令直达，摆脱繁冗的 DocxXML 规则推理，单次同步节约 90%+ Token。

兼容：**Claude Code** · **Antigravity** · **Cursor** · **Windsurf** · **OpenCode** · **Cline** · **Codex** 等 20+ Agent 客户端。

---

## 💡 为什么需要 lark-md-sync？

官方 `lark-doc` 是一套全功能的飞书云文档块级操作技能，但当面对**纯 Markdown 文件读写**这种高频日常场景时，往往会陷入“杀鸡用牛刀”的困境：

| 维度 | 官方 `lark-doc` | ⚡ `lark-md-sync` |
| :--- | :--- | :--- |
| **执行模式** | 渐进式加载 DocxXML 规则，多轮解析 | **单轮直达**：原生 Markdown 通道直推/直拉 |
| **思考轮次** | 4 ~ 6 轮（读规则 → 查 ID → 差异比对 → 逐步 Patch） | **1 轮完成** |
| **Token 消耗** | 约 20,000 ~ 50,000 Tokens / 次 | **< 1,500 Tokens / 次（降低 90%+）** |
| **评论安全** | 规则繁杂，误调 overwrite 易丢失评论 | **智能护栏**：自动检测评论，无评论极速覆写，有评论严格追加保全 |
| **多文章素材** | 混合塞入全局 `assets/`，容易冲突覆盖 | **`<doc>.assets/` 专属伴生目录**（Typora 规范） |
| **跨平台文件名** | 飞书标题常含空格与特殊符号，终端易转义报错 | **自动 Unicode Slugify**（去空格，对终端与 Git 极度友好） |
| **任务语义** | 推与拉混在一个庞大 Skill 中，Agent 易纠结方向 | **`push` 与 `pull` 职责明确解耦**，零认知摇摆 |

---

## 📦 安装

一行命令全局安装整套技能：

```bash
npx -y skills add DBinK/lark-md-sync -g -y
```

安装后即自动注册两个专精 Skill：
- **`lark-md-push`**：本地 Markdown 直推到飞书云文档（新建 / 智能覆写与追加）。
- **`lark-md-pull`**：飞书云文档拉取为本地 Markdown（自动去空格，图片下载至专属伴生目录）。

---

## 🚀 怎么使用？

### 方式 1：对话自然语言触发（最常用）

安装后无需记忆复杂语法，直接在对话中对你的 AI Agent 下指令：

- **推送到飞书**：
  > “帮我把 `./docs/design.md` 推送到飞书新建一篇云文档，标题叫‘系统架构设计’。”  
  > “把本地最新的 `README.md` 同步到这篇飞书文档：`https://example.feishu.cn/docx/xxxxx`。”  
  > *(AI 会自动探测该文档：无评论时极速覆写，有评论时自动转为安全追加以保全评论)*
- **从飞书拉取**：
  > “把这篇飞书文档拉取到本地：`https://example.feishu.cn/docx/xxxxx`。”  
  > *(飞书标题 `系统设计 2.0 (草案)` 会自动保存为 `系统设计-2.0-草案.md`，图片自动下载到 `系统设计-2.0-草案.assets/` 并重写为相对路径)*

### 方式 2：显式调用 Skill / 斜杠命令（精准直达）

在支持 Skill 显式调用或 Slash Command 的客户端（如 Claude Code、Antigravity、OpenCode 等）中，可以直接显式调用：

- **显式直推（新建或更新）**：
  ```text
  /lark-md-push 把 ./README.md 推送到飞书新建文档，标题为 "产品说明书"
  /lark-md-push 同步 ./README.md 到已有飞书文档: https://example.feishu.cn/docx/xxxxx
  ```
- **显式拉取（带图片本地化与去空格）**：
  ```text
  /lark-md-pull 拉取 https://example.feishu.cn/docx/xxxxx 到本地
  /lark-md-pull 拉取 https://example.feishu.cn/docx/xxxxx 并保存为 custom-name.md
  ```

---

## 🛠️ 设计考量 (Design Highlights)

- **原生通道优先 (Markdown-Native)**：充分利用 `lark-cli` 原生 `--doc-format markdown` 能力，绕开高耗损的 DocxXML 抽象层。
- **智能防顶评论 (Smart Guardrail)**：更新云文档前先探测 `reference_map.comments`。文档无评论时，走 `--command overwrite` 极速整篇覆写，干净彻底；检测到有讨论/划词评论时，强制回退到 `--command append` 追加模式，保证团队沟通资产不丢失。
- **伴生素材隔离 (Per-Doc Assets)**：对齐 Typora 与现代 Markdown 生态规范，每篇文档独立拥有 `<filename>.assets/`，文章重命名、移动或删除时素材生命周期与正文保持一致。
- **Unicode Slugify**：保留中文语义的同时剔除空格和特殊符号，在 CLI 和脚本中无需繁琐的引号转义。
- **协议防断裂 (Protocol Resilient)**：内置动态指针自适应本地 `lark-cli` 最新规范，防止版本迭代参数废弃。

---

## 📋 依赖环境

- 已安装并登录 [lark-cli](https://github.com/larksuite/cli)。
- Python 3.10+（拉取时下载素材需要，采用纯标准库，无需安装任何 pip 依赖）。

## 📄 开源协议

[MIT License](LICENSE)
