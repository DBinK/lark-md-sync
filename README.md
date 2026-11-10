# lark-md-sync

专用于 **本地 Markdown (`.md`) 与 飞书云文档** 之间双向读写的极速 Agent Skills。

## 为什么需要本项目？

在使用 AI 编程助手（如 Claude Code、Antigravity、Cursor、Windsurf 等）处理本地 Markdown 与飞书云文档同步时，官方 `lark-doc` 技能涵盖飞书 DocxXML 几乎全部复杂的块级操作规范，导致日常纯 Markdown 同步遇到以下痛点：
- **思考链路过长**：处理纯 Markdown 文件时，Agent 往往需要经历 4~6 轮思考、反复翻阅长篇 DocxXML 规则，白白消耗大量上下文 Token。
- **任务定位模糊**：推和拉混在一个庞大的多合一技能中，Agent 容易反复纠结同步方向和冲突比对。
- **素材丢失断链**：从飞书拉取文档时，图片素材仍为云端短时 token，未下载到本地导致本地 Markdown 预览断图。

本项目将 Markdown 读写能力清晰解耦为两个专精 Skill：
- **`lark-md-push`**：本地 Markdown 直推到飞书云文档（极简单轮直达、支持新建与追加/更新）。
- **`lark-md-pull`**：飞书云文档拉取为本地 Markdown（原生 Markdown 导出、自动下载图片附件至 `assets/` 并重写相对路径）。

---

## 包含的 Skills

| Skill | 描述 | 核心命令 / 工具 |
| --- | --- | --- |
| [`lark-md-push`](skills/lark-md-push/SKILL.md) | 本地 Markdown 极速推送到飞书云文档 | `lark-cli docs +create / +update --doc-format markdown` |
| [`lark-md-pull`](skills/lark-md-pull/SKILL.md) | 飞书文档拉取为本地 Markdown + 图片本地化 | `lark-cli docs +fetch --doc-format markdown` + `scripts/pull_md.py` |

---

## 快速安装

支持通过 [agentskills.io](https://agentskills.io) 兼容的标准工具 `skills` CLI 一键全局安装：

```bash
# 全局安装 lark-md-push（直推技能）
npx --yes skills add DBinK/lark-md-sync --skill lark-md-push -g -y

# 全局安装 lark-md-pull（拉取与素材本地化技能）
npx --yes skills add DBinK/lark-md-sync --skill lark-md-pull -g -y
```

> **提示**：若在本地克隆了本项目，也可直接在项目根目录下运行：
> ```bash
> npx --yes skills add . --skill lark-md-push -g -y
> npx --yes skills add . --skill lark-md-pull -g -y
> ```

---

## 核心功能与使用示例

### 1. `lark-md-push`：极速推送

无需让 Agent 推理 DocxXML 格式，直接通过 `--doc-format markdown` 原生通道直推：

- **新建文档**：
  ```bash
  lark-cli docs +create --title "项目技术设计" --doc-format markdown --content @./design.md --as user
  ```
- **追加内容到已有文档**：
  ```bash
  lark-cli docs +update --doc "<doc_token>" --command append --doc-format markdown --content @./notes.md --as user
  ```
- **全量覆盖已有文档**：
  ```bash
  lark-cli docs +update --doc "<doc_token>" --command overwrite --doc-format markdown --content @./README.md --as user
  ```

### 2. `lark-md-pull`：拉取与素材本地化

从飞书拉取 Markdown，并自动下载文档中的图片素材至本地 `assets/` 目录，重写相对路径：

- **自动化脚本（推荐）**：
  ```bash
  python3 <skill-dir>/scripts/pull_md.py "<doc_url_or_token>" -o "./README.md"
  ```
- **CLI 原生分步直拉**：
  ```bash
  lark-cli docs +fetch --doc "<doc_url_or_token>" --doc-format markdown --as user -q '.data.document.content' -r > "./output.md"
  ```

---

## 依赖环境

- [lark-cli](https://github.com/larksuite/cli) 已安装并配置登录身份。
- Python 3.10+（仅在执行 `lark-md-pull` 的自动化媒体下载脚本时需要，使用纯标准库无需安装额外 pip 包）。

---

## 协议防断裂保证

本项目的两个 Skill 均内置了指向本地 `lark-cli` 权威参考文件的动态指针（如 `lark-cli skills read lark-doc/...`）。当未来 `lark-cli` 版本升级或接口调整时，Agent 能够自动对齐本地最新的 CLI 参数与规范，杜绝硬编码参数失效的问题。

## 开源协议

[MIT License](LICENSE)
