好的。

我将创建一个 Git 提交来固化这些修复。

### feat(cli, engine): 修复 UI 可达性分析及光标定位回归问题

#### 评论
本次提交解决了在实现双向可达性（祖先+后代）后引入的一系列 UI 回归问题，显著提升了 TUI 在历史导航中的稳定性和用户体验。

#### 目标
-   修复 `quipu ui` 启动时光标不自动聚焦在 `HEAD` 节点的问题。
-   修复当 `HEAD` 是旧节点时，图谱中出现不正确的强制连线（视觉穿插）的问题。
-   确保 UI 在任何情况下都能正确渲染图谱并准确定位。

#### 基本原理
1.  **双向可达性**:
    -   在 `HistoryReader` 接口中增加了 `get_descendant_output_trees` 方法，与现有的 `get_ancestor_output_trees` 对应。
    -   `ViewModel` 现在会合并祖先和后代集合，形成完整的“可达”分支，解决了从旧节点查看新节点时高亮不正确的问题。

2.  **精准页面定位**:
    -   在 `HistoryReader` 接口中增加了 `get_node_position` 方法，用于查询节点在全局时间线上的排名。
    -   UI 启动时，`ViewModel` 使用此方法计算出 `HEAD` 节点所在的正确页码，并直接加载该页面，解决了 `HEAD` 在后续页面时无法显示的问题。

3.  **光标聚焦与渲染修复**:
    -   移除了 TUI 渲染逻辑中导致视觉穿插的强制连线代码。
    -   修正了 `DataTable` 中一个错误的 API 调用 (`is_valid_row_key`)。
    -   恢复并强化了光标定位后的状态同步逻辑，确保节点被正确选中并高亮。

#### 标签
#intent/fix #flow/done #priority/critical #comp/cli #comp/engine #comp/interfaces #scope/ux #ai/instruct #task/domain/ui #task/object/reachability #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 提交变更

~~~~~act
git_add
packages/quipu-interfaces/src/quipu/core/storage.py
packages/quipu-engine/src/quipu/core/git_object_storage.py
packages/quipu-engine/src/quipu/core/sqlite_storage.py
packages/quipu-cli/src/quipu/cli/view_model.py
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~act
git_commit
~~~~~
~~~~~
feat(cli, engine): 修复 UI 可达性分析及光标定位回归问题

本次提交解决了在实现双向可达性（祖先+后代）后引入的一系列 UI 回归问题，显著提升了 TUI 在历史导航中的稳定性和用户体验。

主要修复包括：

1.  **双向可达性**:
    -   在 `HistoryReader` 接口中增加了 `get_descendant_output_trees` 方法。
    -   `ViewModel` 现在会合并祖先和后代集合，形成完整的“可达”分支。

2.  **精准页面定位**:
    -   在 `HistoryReader` 接口中增加了 `get_node_position` 方法，用于查询节点在全局时间线上的排名。
    -   UI 启动时会计算并直接加载 `HEAD` 节点所在的正确页码。

3.  **光标聚焦与渲染修复**:
    -   移除了 TUI 渲染逻辑中导致视觉穿插的强制连线代码。
    -   修正了 `DataTable` 中一个错误的 API 调用 (`is_valid_row_key`)，并替换为更稳健的 `try/except LookupError` 结构。
    -   恢复并强化了光标定位后的状态同步逻辑，确保节点被正确选中并高亮。
~~~~~
