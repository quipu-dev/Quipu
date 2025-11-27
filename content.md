## fix: TUI 光标定位添加调试日志

### 错误分析
当前光标定位逻辑失效的原因尚不明确。为了精确定位问题（是页面计算错误、节点查找失败、还是 UI 设置无效），我们需要在关键路径上添加详细的调试日志。这将帮助我们观察 `_focus_current_node` 的内部执行状态。

### 用户需求
修复光标不自动定位的问题。

### 目标
在 `_focus_current_node` 方法中添加详细的 DEBUG 日志。

### 标签
#intent/tune #flow/ready #priority/high #comp/cli #scope/dx #ai/instruct #task/domain/ui #task/object/logging #task/action/debug #task/state/continue

---

### Script

#### Acts 1: 添加详细调试日志

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
                # 1. 设置视觉光标
                table.cursor_coordinate = Coordinate(row=row_index, column=0)
                
                # 2. 同步逻辑状态 (防止事件未触发)
                self.current_selected_node = target_node
                
                # 3. 刷新关联视图
                if self.is_split_mode:
                    self._update_content_view()
        except Exception as e:
            logger.error(f"Failed to focus current node: {e}")
~~~~~
~~~~~python
    def _focus_current_node(self, table: DataTable):
        current_output_tree_hash = self.view_model.current_output_tree_hash
        logger.debug(f"DEBUG: Attempting focus. HEAD={current_output_tree_hash}")

        if not current_output_tree_hash:
            logger.debug("DEBUG: No HEAD hash, skipping.")
            return

        # 查找当前页面中匹配 HEAD 的所有节点
        matching = [n for n in self.node_by_filename.values() if n.output_tree == current_output_tree_hash]
        logger.debug(f"DEBUG: Found {len(matching)} matching nodes in current page map.")

        target_node = matching[0] if matching else None
        if not target_node:
            logger.debug("DEBUG: Target node not found in current page.")
            return

        try:
            row_key = str(target_node.filename)
            logger.debug(f"DEBUG: Target row key: {row_key}")

            if table.is_valid_row_key(row_key):
                row_index = table.get_row_index(row_key)
                logger.debug(f"DEBUG: Row index found: {row_index}. Setting cursor.")
                
                # 1. 设置视觉光标
                table.cursor_coordinate = Coordinate(row=row_index, column=0)
                
                # 2. 同步逻辑状态 (防止事件未触发)
                self.current_selected_node = target_node
                
                # 3. 刷新关联视图
                if self.is_split_mode:
                    self._update_content_view()
            else:
                logger.warning(f"DEBUG: Row key {row_key} is invalid in DataTable (maybe filtered?).")
        except Exception as e:
            logger.error(f"DEBUG: Failed to focus current node: {e}", exc_info=True)
~~~~~
