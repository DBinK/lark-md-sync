# lark-md-sync

专为 AI Agent（Claude Code、Antigravity、Cursor、Windsurf 等）打造的本地 Markdown (`.md`) 与飞书云文档极速读写技能套件。

解决官方 `lark-doc` 规则繁重、思考链路慢、上下文 Token 消耗大以及图片素材易断链的问题。

## 安装

```bash
npx -y skills add DBinK/lark-md-sync -g -y
```

一次安装即包含套件内的全部 Skills：
- **`lark-md-push`**：本地 Markdown 直推到飞书云文档（支持新建与追加/更新）。
- **`lark-md-pull`**：飞书云文档拉取为本地 Markdown（自动下载图片到 `assets/` 并重写相对路径）。

---

## 怎么使用？

安装后无需手动执行命令，直接在对话中给你的 AI Agent 下指令即可：

### 1. 推送到飞书（`lark-md-push`）

- **新建文档**：
  > “帮我把 `./docs/design.md` 推送到飞书新建一篇云文档，标题叫‘系统架构设计’。”
- **追加内容**：
  > “把这篇更新笔记追加到这篇飞书文档末尾：`https://example.feishu.cn/docx/xxxxx`。”
- **全量覆盖**：
  > “用本地最新的 `README.md` 全量更新这篇飞书文档：`https://example.feishu.cn/docx/xxxxx`。”

### 2. 从飞书拉取（`lark-md-pull`）

- **拉取文档并保存图片**：
  > “把这篇飞书文档拉取到本地保存为 `README.md`，图片帮我放 `assets/` 目录：`https://example.feishu.cn/docx/xxxxx`。”
- **备份文档**：
  > “帮我把这个 Wiki 知识库页面导出成本地 Markdown 备份。”

---

## 环境要求

- 已安装并登录 [lark-cli](https://github.com/larksuite/cli)。
- Python 3.10+（拉取时下载并重写图片素材需要，使用纯标准库无第三方依赖）。
