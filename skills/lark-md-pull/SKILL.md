---
name: lark-md-pull
description: 从飞书云文档（Docx/Wiki）拉取并导出为本地 Markdown (.md)，并自动下载图片附件到文档专属的 <doc_name>.assets/ 伴生目录并改写相对路径。当用户需要将飞书文档导出、下载、备份或同步到本地 markdown，或提到“拉取飞书文档”“下载飞书文档为md”“导出飞书云文档”时使用。纯上传/创建飞书文档不适用（使用 lark-md-push）。
metadata:
  version: "0.3.0"
  requires-bin: "lark-cli"
license: MIT
---

# 飞书云文档拉取到本地 Markdown（lark-md-pull）

本技能指导 AI 将飞书/Lark 云文档以原生 Markdown 格式高效拉取到本地，并自动将云端图片/画板缩略图落盘至文档专属的 `<doc_name>.assets/` 伴生目录，自动消除文件名空格并修正相对路径引用。

**核心原则**：
- **原生 Markdown 通道**：利用 `lark-cli docs +fetch --doc-format markdown` 直接获取 Markdown 文本与 `reference_map` 元数据。
- **独立伴生素材目录**：默认落盘至 `<doc_slug>.assets/`（Typora 同款伴生规范），严禁污染全局平铺的 `assets/` 目录，彻底杜绝多文档素材冲突或重名覆盖。
- **扩展名自动感知**：调用 `lark-cli docs +media-download` 时不硬编码扩展名，由 CLI 根据响应的 `Content-Type` 自动识别并补全真实扩展名（`.png` / `.jpg` / `.gif` 等）。
- **Unicode 无空格 Slug 化**：本地文件名自动执行 Unicode Slugify（保留中文，剔除空格与不安全字符，替换为连字符 `-`，英文字母小写化），保证终端与 CLI 环境无缝使用。
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
python3 <skill-dir>/scripts/pull_md.py "<doc_url_or_token>" [-o "./output.md"] [--assets-dir <dir>] [--as user]

# 示例 1：默认自动从文档标题生成无空格文件名与专属素材伴生目录
# 飞书标题 "系统架构设计 2.0 (草案)" -> 自动生成 "系统架构设计-2.0-草案.md" 和 "系统架构设计-2.0-草案.assets/"
python3 <skill-dir>/scripts/pull_md.py "https://example.feishu.cn/docx/xxxxx"

# 示例 2：显式指定输出文件名
python3 <skill-dir>/scripts/pull_md.py "https://example.feishu.cn/docx/xxxxx" -o "./system-design.md"
```

该脚本会自动：
1. 调用 `lark-cli docs +fetch --doc "<token>" --doc-format markdown --as user` 获取文档 Markdown 正文及 `reference_map`；
2. 提取标题并通过 Unicode Slugify 规则生成无空格的安全文件名（若未显式传 `-o`）；
3. 扫描正文中引用的图片、附件或画板 token（自动关联解析 `reference_map`）；
4. 调用 `lark-cli docs +media-download --token "<media_token>" --output "<assets_dir>/<media_token>"` 下载素材并自动补全真实扩展名；
5. 将正文中的图片引用改写为相对路径 `![alt](<doc_stem>.assets/<filename>)`；
6. 原子写入最终的本地 Markdown 文件。

---

### 方式 B：CLI 原生分步直拉（无需脚本）

若在无 Python 环境或仅需纯文本内容的场景，可直接执行原生命令（注意：`docs +fetch` 默认输出 JSON，使用 `-q` 过滤时字符串自带换行输出，不要传 `-r` 或 `--json`）：

```bash
# 1. 直接拉取 Markdown 内容并提取正文写入文件
lark-cli docs +fetch --doc "<doc_url_or_token>" --doc-format markdown --as user -q '.data.document.content' > "./output.md"

# 2. （可选）如有图片或画板 token 需要手动下载（注意：+media-download 不接受 --doc 参数，且不带后缀时自动补全扩展名）：
mkdir -p "./output.assets"
lark-cli docs +media-download --token "<media_token>" --output "./output.assets/<media_token>" --overwrite --as user
```

---

## 2. 导出转义与边界注意事项

1. **导出已转义，切勿反转义**：
   - 根据飞书文档规范，`docs +fetch --doc-format markdown` 导出的内容中，特殊字符已带有合法的 Markdown 转义（例如 `\[`、`\|`、`\\`、`\*` 等）。
   - **切勿自行全局反转义或批量去掉 `\`**，否则后续将内容通过 `lark-md-push` 写回或做 `str_replace` 匹配时会导致语法吞字或匹配失败。
2. **云文档（Docx/Wiki）vs 云盘原生 `.md` 文件**：
   - 本技能专用于飞书在线云文档（URL 含 `/docx/` 或 `/wiki/`）。若目标只是飞书云盘（Drive）中存储的普通静态 `.md` 文件，应使用 `lark-cli markdown +fetch`。

---

## 3. 验证与反馈

执行完毕后：
1. 检查本地输出文件是否存在且内容完整；
2. 若文档包含图片，检查本地 `<doc_stem>.assets/` 目录下图片是否正常落盘；
3. 向用户汇报生成的 Markdown 文件路径及已下载的素材伴生目录。
