## fix: 修复 TUI 光标定位与选中状态同步问题

### 错误分析
用户反馈“光标未在当前节点位置”，实际上可能包含两个层面的问题：
1.  **视觉光标位置**: 虽然计算出了正确的页面，但 `_focus_current_node` 中的 `table.cursor_coordinate` 设置可能因为时序问题或 `try-except` 掩盖的错误而未能生效。
2.  **逻辑选中状态**: 在上一次重构中，我移除了 `_focus_current_node` 中手动设置 `self.current_selected_node` 的代码，完全依赖 `DataTable.RowHighlighted` 事件。然而，在表格初始化或重置（`clear()`）并立即设置光标时，Textual 可能不会触发该事件（或者事件触发时机与数据加载存在竞态），导致 `current_selected_node` 为 `None`，右侧内容区无法显示，且光标高亮可能不明显。

此外，用户提到以前的代码包含 `cursor_row == 0` 的检查。虽然我们在新逻辑中希望强制定位，但恢复对选中状态的手动同步是确保可靠性的关键。

### 用户需求
打开 UI 时，光标应准确停留在 HEAD 节点上，并且该节点应处于“选中”状态（右侧显示其内容）。

### 目标
1.  在 `_focus_current_node` 中恢复手动设置 `self.current_selected_node` 的逻辑。
2.  在定位光标后，立即手动刷新内容视图 `_update_content_view`，不依赖事件回调。
3.  保持 `table.focus()` 以确保键盘交互可用。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #scope/ux #ai/instruct #task/domain/ui #task/object/reachability #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 增强 `_focus_current_node` 逻辑

我们将在 `_focus_current_node` 中显式地执行所有状态同步操作，确保“定位”、“数据选中”、“视图刷新”三者原子化完成，不再被动等待可能丢失的 UI 事件。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def _focus_current_node(self, table: DataTable):
        current_output_tree_hash = self.view_model.current_output_tree_hash
        target_node = next(
            (n for n in self.node_by_filename.values() if n.output_tree == current_output_tree_hash), None
        )
        if not target_node:
            return
        try:
            row_key = str(target_node.filename)
            if table.is_valid_row_key(row_key):
                row_index = table.get_row_index(row_key)
                table.cursor_coordinate = Coordinate(row=row_index, column=0)
                # 移除手动状态更新，完全依赖 on_row_highlighted 事件
        except Exception:
            pass

    @on(DataTable.RowHighlighted)
~~~~~
~~~~~python
    def _focus_current_node(self, table: DataTable):
        current_output_tree_hash = self.view_model.current_output_tree_hash
        target_node = next(
            (n for n in self.node_by_filename.values() if n.output_tree == current_output_tree_hash), None
        )
        if not target_node:
            return
        try:
            row_key = str(target_node.filename)
            if table.is_valid_row_key(row_key):
                row_index = table.get_row_index(row_key)
                # 1. 设置视觉光标
                table.cursor_coordinate = Coordinate(row=row_index, column=0)
                
                # 2. 同步逻辑状态 (防止事件未触发)
                self.current_selected_node = target_node
                
                # 3. 刷新关联视图
                if self.is_split_mode:
                    self._update_content_view()
        except Exception as e:
            logger.error(f"Failed to focus current node: {e}")

    @on(DataTable.RowHighlighted)
~~~~~
