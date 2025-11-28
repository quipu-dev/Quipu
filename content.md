这是一个非常好的建议。用节点的 `summary` 作为加载占位符，不仅解决了性能问题，还极大地提升了用户体验，因为它提供了即时的、有语义的反馈。这个改动成本很低，因为 `summary` 数据在 `ViewModel` 中已经是预加载好的。

我将更新计划，以实现这个更优雅的方案。

## [WIP] refactor: 优化 TUI 加载占位符，使用节点摘要替代通用文本

### 用户需求
将 TUI 内容视图中 "Loading..." 的通用占位符，替换为当前高亮节点的 `summary`，以便在加载完整内容前，为用户提供即时、有意义的上下文预览。

### 评论
这个改进将占位符从一个纯粹的技术状态指示器，转变为一个有价值的 UX 元素。用户在快速滚动时，可以即时预览每个节点的摘要，这使得信息浏览的效率和体验都得到了显著提升。

### 目标
修改 `on_row_highlighted` 方法，使其在设置防抖定时器之前，执行以下操作：
1.  从 `ViewModel` 中获取当前选中的 `QuipuNode` 对象。
2.  提取节点的 `summary` 属性。
3.  构建一个包含该 `summary` 的、格式化的 Markdown 字符串作为占位符。
4.  将此占位符更新到 `Markdown` 组件中。

### 基本原理
基本原理仍然是防抖机制。我们只是将防抖期间显示的静态占位符 (`*Loading...*`) 替换为一个动态生成的、包含节点摘要的预览。由于 `QuipuNode` 对象及其 `summary` 字段在分页加载时已存在于内存中，这个操作几乎没有性能开销，可以安全地在每次 `RowHighlighted` 事件中同步执行。

### 标签
#intent/refine #flow/ready #priority/high
#comp/cli #concept/ui #scope/ux
#ai/brainstorm
#task/domain/ui #task/object/tui-performance #task/action/improvement #task/state/continue

---

### Script

#### Acts 1: 更新 `on_row_highlighted` 以显示动态占位符

我们将修改 `packages/quipu-cli/src/quipu/cli/tui.py` 中的 `on_row_highlighted` 方法，以实现新的占位符逻辑。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handles cursor movement with debouncing to prevent lag."""
        # Stop any pending content update
        if self.update_timer:
            self.update_timer.stop()

        # Update selection immediately for internal state
        row_key = event.row_key.value
        if row_key:
            self.view_model.select_node_by_key(row_key)

        # If view is visible, show loading and schedule the real update
        if self.is_split_mode:
            markdown_widget = self.query_one("#content-body", Markdown)
            markdown_widget.update("*Loading...*")
            self.update_timer = self.set_timer(self.debounce_delay_seconds, self._debounced_update_content_view)
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handles cursor movement with debouncing to prevent lag."""
        # Stop any pending content update
        if self.update_timer:
            self.update_timer.stop()

        # Update selection immediately for internal state
        selected_node = None
        row_key = event.row_key.value
        if row_key:
            selected_node = self.view_model.select_node_by_key(row_key)

        # If view is visible, show a meaningful placeholder and schedule the real update
        if self.is_split_mode:
            markdown_widget = self.query_one("#content-body", Markdown)
            if selected_node and selected_node.summary:
                placeholder = f"### {selected_node.summary}\n\n---\n*Loading full content...*"
            else:
                placeholder = "*Loading...*"
            markdown_widget.update(placeholder)
            self.update_timer = self.set_timer(self.debounce_delay_seconds, self._debounced_update_content_view)
~~~~~

### 下一步建议
和之前一样，请手动验证修复效果。
1.  重新安装开发环境的 `quipu-cli`。
2.  运行 `quipu ui` 命令。
3.  **验证新的占位符**: 快速滚动列表。确认右侧面板现在显示的是每个节点的摘要标题，并带有 "Loading full content..." 的提示。
4.  **验证最终加载**: 停止滚动后，确认摘要占位符被完整的节点内容所替换。
5.  **验证无摘要情况**: 如果有无摘要的节点，确认其占位符回退到了 `*Loading...*`。

如果一切符合预期，这个功能就完成了，我们可以准备提交它。
