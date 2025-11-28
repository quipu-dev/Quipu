好的，这个优化建议非常好。

当前 TUI 在滚动时会有一个短暂的延迟，因为它会等待一个防抖计时器结束后再渲染完整的 Markdown 内容。在等待期间，它只显示节点的摘要。你的建议是在这个“加载中”的阶段，直接用纯文本显示节点的主要内容，因为纯文本渲染几乎没有性能开销，可以提供即时的反馈，极大地提升滚动时的流畅感。

我将生成一个计划来实现这个改动。

## [WIP] feat: 在 TUI 滚动时即时显示纯文本内容以提升性能

### 用户需求
在 TUI 的历史视图中，当用户快速上下滚动时，右侧的内容预览面板响应迟钝。为了改善体验，希望在滚动期间（即最终的 Markdown 渲染完成前），预览面板能立即显示节点的纯文本内容，而不是只显示摘要或“加载中”的提示。

### 评论
这是一个非常有效的交互优化。它利用了纯文本渲染速度极快的特点，在用户滚动时提供了即时的内容预览，而在用户停止滚动后，再进行消耗性能的 Markdown 格式化渲染。这创造了一种流畅且响应迅速的用户体验。

### 目标
1.  修改 `quipu-cli` 包中的 `tui.py` 文件。
2.  调整 `_update_loading_preview` 方法的逻辑。
3.  使其在“加载中”状态下，优先从 `QuipuNode` 对象中获取已加载的 `content` 字段，并将其作为纯文本显示在预览面板中。
4.  如果 `content` 字段不可用，则回退到显示摘要的旧行为。

### 基本原理
`QuipuNode` 对象在通过分页加载时，其 `.content` 属性（即计划的公共内容）已经被填充。这意味着在 TUI 中，当光标移动到一个新的节点上时，其核心内容是立即可用的，无需额外的 I/O 操作。

当前的性能瓶颈在于 Textual 的 `Markdown` 组件渲染复杂的 Markdown 文本。而 `Static` 组件渲染纯文本则非常快。

我们将利用这一点，修改 UI 的状态机：在 `LOADING` 状态（用户正在滚动时触发）下，我们将节点的 `.content` 字符串直接传递给一个 `Static` 组件进行显示。当滚动停止，防抖计时器结束后，UI 进入 `SHOWING_CONTENT` 状态，此时再调用 `Markdown` 组件来渲染完整的内容（包括私有数据），实现最终的精美排版。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-performance #task/action/optimization #task/state/begin

---

### Script

#### Acts 1: 更新 TUI 的加载预览逻辑

我们将修改 `_update_loading_preview` 函数，使其在快速滚动时能够即时显示节点的纯文本内容。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def _update_loading_preview(self):
        """A lightweight method to only update header/placeholder text."""
        node = self.view_model.get_selected_node()
        if not node:
            return

        # Update header and placeholder text
        self.query_one("#content-header", Static).update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")
        placeholder_widget = self.query_one("#content-placeholder", Static)
        if node.summary:
            placeholder_widget.update(f"### {node.summary}\n\n---\n*Loading full content...*")
        else:
            placeholder_widget.update("*Loading...*")
~~~~~
~~~~~python
    def _update_loading_preview(self):
        """A lightweight method to only update header/placeholder text."""
        node = self.view_model.get_selected_node()
        if not node:
            return

        # Update header and placeholder text
        self.query_one("#content-header", Static).update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")
        placeholder_widget = self.query_one("#content-placeholder", Static)

        # Prioritize showing the raw public content if it's already loaded in the node object.
        # This provides a very fast preview while scrolling.
        if node.content and node.content.strip():
            placeholder_widget.update(node.content)
        # Fallback to summary if content isn't loaded or is empty.
        elif node.summary:
            placeholder_widget.update(f"### {node.summary}\n\n---\n*Loading full content...*")
        else:
            placeholder_widget.update("*Loading...*")
~~~~~

### 下一步建议
代码修改已完成。现在，你可以运行 `qd ui` 来亲自体验一下滚动性能的提升。确认无误后，我们可以为这个功能改进编写一个测试，或者直接创建一个 `[COMMIT]` 计划将其合并到主线历史中。
