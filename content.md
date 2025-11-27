## fix: 修复 TUI 启动时无法自动聚焦当前节点的问题

### 错误分析
虽然 `quipu ui` 能够正确计算并跳转到 HEAD 所在的页面，但 `DataTable` 组件在加载数据后，光标（高亮行）并未自动定位到 HEAD 节点对应的行。

原因有两点：
1.  **缺少焦点**: `DataTable` 在 `on_mount` 时没有被显式赋予焦点 (`focus()`)，导致高亮样式可能不明显或未激活键盘导航状态。
2.  **状态同步冗余**: `_focus_current_node` 方法中尝试手动更新 `self.current_selected_node`，这与 `DataTable` 的 `RowHighlighted` 事件逻辑重叠，可能导致状态竞态。正确的做法是只操作 UI 光标，让 UI 事件驱动数据状态更新。

### 用户需求
打开 UI 时，不仅要翻到正确的页，光标还必须直接停留在当前 HEAD 节点上，用户无需按键寻找。

### 评论
这是一个提升“开箱即用”体验的小但关键的修复。

### 目标
1.  在 TUI 启动时强制聚焦 `DataTable`。
2.  简化 `_focus_current_node` 逻辑，确保光标坐标设置生效。

### 基本原理
-   在 `on_mount` 末尾调用 `table.focus()`。
-   在 `_focus_current_node` 中仅设置 `table.cursor_coordinate`，移除副作用代码。

### 标签
#intent/fix #flow/ready #priority/medium #comp/cli #scope/ux #ai/instruct #task/domain/ui #task/object/reachability #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 强制聚焦并简化光标设置逻辑

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
        # 计算 HEAD 所在的页码并跳转
        initial_page = self.view_model.calculate_initial_page()
        logger.debug(f"TUI: HEAD is on page {initial_page}. Loading...")
        self._load_page(initial_page)

    def on_unmount(self) -> None:
~~~~~
~~~~~python
        # 计算 HEAD 所在的页码并跳转
        initial_page = self.view_model.calculate_initial_page()
        logger.debug(f"TUI: HEAD is on page {initial_page}. Loading...")
        self._load_page(initial_page)
        
        # 强制将焦点给到表格，确保高亮可见且键盘可用
        table.focus()

    def on_unmount(self) -> None:
~~~~~
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
                if not self.current_selected_node:
                    self.current_selected_node = target_node
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
                table.cursor_coordinate = Coordinate(row=row_index, column=0)
                # 移除手动状态更新，完全依赖 on_row_highlighted 事件
        except Exception:
            pass

    @on(DataTable.RowHighlighted)
~~~~~
