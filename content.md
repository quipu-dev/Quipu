# 这表明在我重构 `tui.py` 时，使用了 Textual `DataTable` 组件一个不存在的事件 `@on(DataTable.Scrolled)`。错误提示建议使用 `scroll_end`。

### 错误分析

错误日志非常明确：
`AttributeError: type object 'DataTable' has no attribute 'Scrolled'. Did you mean: 'scroll_end'?`

这表明在我重构 `tui.py` 时，使用了 Textual `DataTable` 组件一个不存在的事件 `@on(DataTable.Scrolled)`。错误提示建议使用 `scroll_end`。

查阅 Textual 文档可以确认，正确的事件是 `DataTable.ScrollEnd`，它在用户滚动到底部并停止时触发，这正是实现“无限滚动”所需的事件。

我将修正这个事件的名称，并相应地调整事件处理函数的名称和逻辑。

### 用户需求

修复在 `阶段三` 代码重构中引入的 `AttributeError`，使 `pytest` 测试能够正常收集和运行。

### 评论

这是一个典型的 API 使用错误，测试在模块导入阶段就捕获了它，这展示了测试驱动开发的重要性。修复这个问题很简单，只需要将错误的事件监听器更正为 Textual 框架支持的正确事件即可。

### 目标

1.  将 `packages/quipu-cli/src/quipu/cli/tui.py` 中的事件监听器从 `@on(DataTable.Scrolled)` 修改为 `@on(DataTable.ScrollEnd)`。
2.  相应地重命名事件处理函数，并调整其内部逻辑以正确触发分页加载。

### 基本原理

Textual 的事件系统是基于消息传递的。当一个 widget 发生特定交互（如滚动到底部）时，它会发布一个对应的消息（事件）。应用程序可以通过 `@on(...)` 装饰器来订阅这些消息并执行相应的处理函数。我之前使用的 `DataTable.Scrolled` 是一个不存在的消息类型，而 `DataTable.ScrollEnd` 才是当滚动条到达末端时发出的正确消息。

### 标签

#intent/fix #flow/ready #priority/critical
#comp/cli #concept/ui #scope/core
#ai/instruct
#task/domain/ui
#task/object/pagination
#task/action/bug-fix
#task/state/continue
#task/status/active

---

### Script

#### Acts 1: 修正 TUI 中的滚动事件监听器

我将修改 `tui.py` 文件，将错误的 `@on(DataTable.Scrolled)` 装饰器替换为正确的 `@on(DataTable.ScrollEnd)`，并更新处理函数以匹配新的事件。

~~~~~act
patch_file
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key.value
        if node := self.node_by_filename.get(row_key):
            self.current_selected_node = node
            if self.is_split_mode:
                self._update_content_view()

    @on(DataTable.Scrolled)
    def on_scrolled(self, event: DataTable.Scrolled) -> None:
        # Trigger load when scrollbar is near the bottom
        if event.y + event.visible_size >= event.virtual_size - 10:
            self.run_load()

    def _update_content_view(self):
        if not self.current_selected_node:
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key.value
        if node := self.node_by_filename.get(row_key):
            self.current_selected_node = node
            if self.is_split_mode:
                self._update_content_view()

    @on(DataTable.ScrollEnd)
    def on_data_table_scroll_end(self, event: DataTable.ScrollEnd) -> None:
        # Trigger load when scrollbar is at the bottom (or very near it)
        if event.y >= event.virtual_size.height - event.size.height - 1:
            self.run_load()

    def _update_content_view(self):
        if not self.current_selected_node:
~~~~~
