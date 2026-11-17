# 官方飞书 Skills 路由引导补丁与恢复指南

> 本指南用于解决用户在日常只说「同步到飞书」「更新飞书文档」「导入 md」时，Agent 先命中了飞书官方 `lark-doc` / `lark-drive` / `lark-wiki` 却绕过 `lark-md-push` / `lark-md-pull`（尤其是绕过防评论脱锚流程与 `.assets/` 伴生图片机制）的问题。

---

## 1. 探测常见 Skills 安装目录

飞书官方 Skills 可能安装在以下任一客户端目录（按实际存在目录逐一检查，跳过符号链接指向同一目录的重复路径）：

```bash
PATCH_VERSION="0.4.0"
for dir in \
  "$HOME/.gemini/antigravity-cli/skills" \
  "$HOME/.claude/skills" \
  "$HOME/.agents/skills" \
  "$HOME/.codex/skills" \
  "$HOME/.config/agents/skills"; do
  for skill in lark-doc lark-drive lark-wiki; do
    file="$dir/$skill/SKILL.md"
    if [ -f "$file" ]; then
      line=$(grep -m1 "BEGIN lark-md-sync-routing" "$file" 2>/dev/null || true)
      if [ -z "$line" ]; then
        echo "$file -> status=missing"
      elif echo "$line" | grep -q "version=$PATCH_VERSION"; then
        echo "$file -> status=up_to_date ($PATCH_VERSION)"
      else
        echo "$file -> status=outdated ($line)"
      fi
    fi
  done
done
```

---

## 2. 注入内容定义（带来源、版本与幂等边界标记）

所有注入内容均用 `<!-- BEGIN lark-md-sync-routing source=DBinK/lark-md-sync version=0.4.0 -->` 与 `<!-- END lark-md-sync-routing -->` 包裹，便于来源溯源、版本校验、原地幂等更新或无损卸载。

### 2.1 `lark-doc/SKILL.md`（核心必注）

建议插入位置：`## 场景与 Shortcut 路由` 标题下方（或正文首段提示之后）。

```markdown
<!-- BEGIN lark-md-sync-routing source=DBinK/lark-md-sync version=0.4.0 -->
> **本地 Markdown 与正文安全编辑协同路由（lark-md-sync）**：
> - 涉及将本地 `.md` 上传、推送、增量同步到飞书文档，**或直接在线修改、更新、增补飞书云文档正文**，**优先加载 `lark-md-push`**；将飞书文档导出为本地 `.md`（含 `.assets/` 图片），**优先加载 `lark-md-pull`**。
> - 修改**已有评论**的飞书文档时，严禁直接对带 `comment-refs` 的文本执行 `str_replace`、`block_delete` 或全篇 `overwrite`，务必按 `lark-md-push` 场景 C 执行写前/写后 `reference_map.comments` 比对。
<!-- END lark-md-sync-routing -->
```

### 2.2 `lark-drive/SKILL.md`（推荐注入）

建议插入位置：官方自带的 `> **副本分流规则：**` 之后、`## 快速决策` 标题之前（与官方分流规则同级并列，不压过顶部的 `CRITICAL` 提示）。

```markdown
<!-- BEGIN lark-md-sync-routing source=DBinK/lark-md-sync version=0.4.0 -->
> **本地 Markdown 导入协同路由（lark-md-sync）**：
> - 若用户需要把本地 `.md` 导入、上传或同步为飞书在线文档（Docx / Wiki），尤其需要处理相对路径图片或保留目标文档已有评论时，**优先转交 `lark-md-push`**（不要直接用 `drive +import` 覆盖）。
<!-- END lark-md-sync-routing -->
```

### 2.3 `lark-wiki/SKILL.md`（可选注入）

建议插入位置：`## 快速决策` 标题下方第一条（紧跟身份选择，不压过顶部的 `CRITICAL` 提示）。

```markdown
<!-- BEGIN lark-md-sync-routing source=DBinK/lark-md-sync version=0.4.0 -->
> **知识库正文 Markdown 协同路由（lark-md-sync）**：
> - `lark-wiki` 仅负责知识空间、成员与节点层级管理；涉及 `/wiki/` 节点正文的本地 `.md` 推送、增量同步或导出，**请转交 `lark-md-push` / `lark-md-pull`**。
<!-- END lark-md-sync-routing -->
```

---

## 3. 安全注入执行流程（必须先征得用户同意）

1. **禁止静默修改第三方文件**：仅在用户明确回复确认（如“注入”“同意注入”）后执行写入。
2. **幂等更新逻辑**：
   - 若目标 `SKILL.md` 已存在 `<!-- BEGIN lark-md-sync-routing -->` 与 `<!-- END lark-md-sync-routing -->`，仅替换两标记之间的内容；
   - 若不存在，则在对应插入位置写入上述片段。
3. **写后核验**：重新 `grep -c "lark-md-sync-routing"` 确认目标文件均为 `>= 1`，并向用户列出已修改的文件绝对路径。

---

## 4. 恢复手段（卸载或还原官方原版）

若注入后希望撤销，或担心影响官方升级，提供两种无损恢复方式：

### 方式 A：精准移除注入块（保留其他一切内容）
删除目标 `SKILL.md` 中从 `<!-- BEGIN lark-md-sync-routing -->` 到 `<!-- END lark-md-sync-routing -->`（含两端注释行）的文本即可，官方原文一字不动。

### 方式 B：用 `lark-cli` 内置官方原文一键还原（无需联网）
`lark-cli` 二进制自身在编译期内置了官方原版 `SKILL.md`，可直接覆盖恢复：

```bash
# 示例：将官方内置原版覆盖写回目标目录（把 <SKILL_ROOT> 替换为实际安装目录）
lark-cli skills read lark-doc/SKILL.md > "<SKILL_ROOT>/lark-doc/SKILL.md"
lark-cli skills read lark-drive/SKILL.md > "<SKILL_ROOT>/lark-drive/SKILL.md"
lark-cli skills read lark-wiki/SKILL.md > "<SKILL_ROOT>/lark-wiki/SKILL.md"
```

### 方式 C：通过重装官方 Skills 包恢复
也可按飞书 CLI 官方文档重新安装/更新官方 Skills 覆盖目录；升级覆盖后，`lark-md-push` / `lark-md-pull` 会在下次会话首次触发时自动重新检测到缺失并提示。
