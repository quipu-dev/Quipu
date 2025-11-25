# fix-migration: 修复迁移逻辑以保留内容

## 用户需求
用户反馈在执行 `qd history migrate` 后，`qd ui` 中的所有 Plan 节点都失去了描述（summary）。这表明迁移脚本在转换旧节点时，未能正确生成或保留节点的摘要信息。

## 评论
这是一个严重的回归问题。迁移脚本 (`HistoryMigrator`) 是从 `FileSystemHistoryReader` 读取旧节点，然后使用 `GitObjectHistoryWriter` 写入新节点。
在旧的 FS reader 中，我们是从 Frontmatter 或 Content 中提取 summary 的。
在 `HistoryMigrator.migrate` 中，我们构建了 `metadata.json`，其中包含了 `summary`。
但是，`FileSystemHistoryReader.load_all_nodes` 目前（在之前的变更中）对于 `content` 的加载也是预加载的。
问题可能出在：
1. `FileSystemHistoryReader` 加载旧节点时 summary 解析错误。
2. `HistoryMigrator` 在构建 metadata 时使用了错误的 summary 来源。
3. `GitObjectHistoryWriter` 在写入 commit message 时没有正确使用传入的 summary。

检查 `HistoryMigrator._build_metadata` 方法：
```python
"summary": node.summary,
```
它是直接使用 `node.summary` 的。

检查 `FileSystemHistoryReader` (在 `history.py` 中的 `load_all_history_nodes`):
```python
# For legacy nodes, we generate a summary on the fly.
summary = "No description"
if node_type == 'plan':
    # ... logic to extract summary from body_content ...
```
这段逻辑依赖于 `body_content`。

**关键点**：之前的变更将 `FileSystemHistoryReader` 也适配了 `HistoryReader` 接口，但 `load_all_nodes` 依然调用 `load_all_history_nodes`，后者是预加载内容的。所以 `node.summary` 应该是有值的。

让我们检查 `HistoryMigrator.migrate` 中的写入逻辑：
```python
# 5. Commit Tree
parents = [parent_commit] if parent_commit else []
# Subject
message = f"{node.summary}\n\nX-Quipu-Output-Tree: {node.output_tree}"

commit_hash = self.git_db.commit_tree(tree_hash, parents, message)
```
这里使用了 `node.summary` 作为 commit message 的 subject。

再看 `GitObjectHistoryWriter` 的逻辑（虽然 Migrator 直接调用 git_db，没有用 writer，这是一个不一致点，但 Migrator 是为了特殊处理 migration_info，直接操作 git_db 是合理的）。

**疑点**：`node.summary` 在 `FileSystemHistoryReader` 中是否正确生成了？
`packages/quipu-engine/src/quipu/core/history.py` 中的逻辑看起来是健壮的。

等等，我在上一个 fix-perf 计划中修改了 `FileSystemHistoryReader`，但只是加了 `get_node_content`，没有修改 `load_all_nodes`。

然而，`qd ui` (TUI) 是如何获取 summary 的？
```python
# packages/quipu-cli/src/quipu/cli/tui.py

    def _get_node_summary(self, node: QuipuNode) -> str:
        # 它直接读取 node.content !!!
        content = node.content.strip()
        lines = content.split('\n')
        # ... parsing logic ...
```
**这就是原因！**
`qd ui` 依然依赖 `node.content` 来现场提取 summary，而不是信任 `node.summary` 字段（虽然 `GitObjectHistoryReader` 已经填充了这个字段）。
而在 Lazy Loading 模式下，`node.content` 默认为空字符串！
因此 `qd ui` 面对空内容，提取出了默认值 "No description" 或者空的 summary。

**修复方案**：
修改 `packages/quipu-cli/src/quipu/cli/tui.py`，优先使用 `node.summary` 字段。这个字段在 `GitObjectHistoryReader` 加载 metadata 时已经填充好了（这正是 metadata 分离的意义所在）。对于旧版 FS Reader，`node.summary` 也是填充好的。

所以这是一个 UI 层的修复，而不是迁移脚本的问题。

## 目标
修复 `qd ui` 在 Lazy Loading 模式下无法显示节点摘要的问题。

## 基本原理
更新 `QuipuUiApp._get_node_summary` 方法，使其直接返回 `node.summary`，而不再尝试解析 `node.content`。这不仅修复了 Bug，还符合性能优化的初衷（避免 UI 读取内容）。

## 标签
#comp/cli #concept/ui #fix

---

## Script

### Acts 1: 修复 UI Summary 获取逻辑

~~~~~act
replace packages/quipu-cli/src/quipu/cli/tui.py
~~~~~

~~~~~python
    def _get_node_summary(self, node: QuipuNode) -> str:
        content = node.content.strip()
        lines = content.split('\n')
        summary = "No description"
        if node.node_type == 'plan':
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith(('~~~', '```')): continue
                if clean_line: summary = clean_line; break
        elif node.node_type == 'capture':
            summary = next((line.strip() for line in lines if line.strip() and not line.startswith(('#', '`', '-', "###"))), "Workspace Snapshot")
        return (summary[:60] + '...') if len(summary) > 60 else summary
~~~~~

~~~~~python
    def _get_node_summary(self, node: QuipuNode) -> str:
        """
        获取节点摘要。
        优先使用节点对象中预加载的 summary 字段 (来自 metadata 或 commit message)。
        这避免了触发 Lazy Loading 读取 content。
        """
        if node.summary:
            return node.summary
            
        # Fallback (主要是为了兼容某些极端情况，或者是旧版数据未正确填充 summary)
        if not node.content:
            return "No summary available"
            
        content = node.content.strip()
        lines = content.split('\n')
        summary = "No description"
        if node.node_type == 'plan':
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith(('~~~', '```')): continue
                if clean_line: summary = clean_line; break
        elif node.node_type == 'capture':
            summary = next((line.strip() for line in lines if line.strip() and not line.startswith(('#', '`', '-', "###"))), "Workspace Snapshot")
        return (summary[:60] + '...') if len(summary) > 60 else summary
~~~~~