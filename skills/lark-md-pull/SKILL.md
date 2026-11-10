---
name: lark-md-pull
description: 从飞书云文档（Docx/Wiki）拉取并导出为本地 Markdown (.md)，并自动下载图片附件到本地 assets/ 目录并改写相对路径。当用户需要将飞书文档导出、下载、备份或同步到本地 markdown 时使用。
metadata:
  version: "0.1.0"
  requires-bin: "lark-cli"
license: MIT
---

# 飞书云文档拉取到本地 Markdown（lark-md-pull）

本技能指导 AI 将飞书/Lark 云文档以原生 Markdown 格式高效拉取到本地，并自动将云端图片/多媒体素材落盘至本地 `assets/` 目录，修正本地相对路径引用。

**核心原则**：
- **原生 Markdown 通道**：利用 `lark-cli docs +fetch --doc-format markdown` 直接获取 Markdown 文本。
- **自动素材本地化**：通过内置辅助脚本或 CLI 命令，下载文档内引用的图片至本地 `assets/`，避免本地 Markdown 出现断链或无法渲染的问题。
- **原子落盘**：文件写入采用临时文件替换机制，避免并发写入损坏。

---

## 0. 协议防断裂指针（CRITICAL：以 lark-cli 本地 Skill 为权威）

`lark-cli` 的 CLI 参数与协议可能随版本迭代升级。**严禁把参数硬编码视为永久真理**。
执行前如遇参数疑问或异常，必须按需检视本地绑定的权威指引：

- **读取云文档权威指引**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-fetch.md
  ```
- **多媒体素材下载权威指引**：
  ```bash
  lark-cli skills read lark-doc/references/lark-doc-media-download.md
  ```
- **CLI 原生帮助兜底**：随时运行 `lark-cli docs +fetch --help` 或 `lark-cli docs +media-download --help`。

---

## 1. 核心流程与标准操作

### 方式 A：一键自动化脚本（推荐）

本技能自带自动化拉取与素材本地化脚本 `scripts/pull_md.py`：

```bash
# 语法
python3 <skill-dir>/scripts/pull_md.py "<doc_url_or_token>" -o "./output.md" [--assets-dir assets] [--as user]

# 示例：拉取到当前目录 README.md 并保存图片至 ./assets/
python3 scripts/pull_md.py "https://example.feishu.cn/docx/xxxxx" -o "./README.md"
```

该脚本会自动：
1. 调用 `lark-cli docs +fetch --doc "<token>" --doc-format markdown --as user` 获取文档 Markdown 正文；
2. 扫描正文中引用的媒体资源 token；
3. 调用 `lark-cli docs +media-download` 下载所有图片到目标目录下的 `assets/`；
4. 将正文中的图片引用改写为相对路径 `![alt](assets/<token>.png)`；
5. 原子写入最终的本地 Markdown 文件。

---

### 方式 B：CLI 原生分步直拉（无需脚本）

若在无 Python 环境或仅需纯文本内容的场景，可直接执行原生命令：

```bash
# 1. 直接拉取 Markdown 内容并提取正文写入文件
lark-cli docs +fetch --doc "<doc_url_or_token>" --doc-format markdown --as user -q '.data.document.content' -r > "./output.md"

# 2. （可选）如有图片 token 需要手动下载：
lark-cli docs +media-download --doc "<doc_token>" --token "<media_token>" --output "./assets/<media_token>.png" --as user
```

---

## 2. 导出转义注意事项

根据飞书文档规范，`docs +fetch --doc-format markdown` 导出的内容中，特殊字符已带有合法的 Markdown 转义（例如 `\[`、`\|`、`\\` 等）。
**切勿自行全局反转义或批量去掉 `\`**，以保持 Markdown 语法的严谨性与兼容性。

---

## 3. 验证与反馈

执行完毕后：
1. 检查本地输出文件是否存在且内容完整；
2. 若文档包含图片，检查本地 `assets/` 目录下图片是否正常落盘；
3. 向用户汇报生成的 Markdown 文件路径及已下载的素材数量。
