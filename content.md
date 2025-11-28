你的分析是正确的。TUI 滚动时的卡顿和视图切换的视觉问题，其根源在于对 `textual` 事件的响应方式。

我将为你生成一份详细的分析和修复计划。

## [WIP] fix: 优化 TUI 内容视图的加载性能，解决滚动卡顿问题

### 错误分析
你在 `TUI-markdown加载速度过慢.md` 中描述的现象，其核心原因是 TUI 对用户输入的响应是**同步且昂贵的**。

1.  **事件风暴 (Event Storm)**: 当用户按住 `j` 或 `k` 键快速滚动时，`textual` 的 `DataTable` 会为光标经过的**每一行**都触发一个 `RowHighlighted` 事件。
2.  **同步重绘 (Synchronous Rendering)**: 当前的 `on_row_highlighted` 事件处理器会**立即**、**同步地**执行一系列重度操作：
    *   从 `ViewModel` 获取节点对象。
    *   调用 `get_content_bundle`，这会从 `HistoryReader` (可能涉及磁盘 I/O 或 Git 对象解压) 读取两个文件内容 (公共计划和私有元数据)。
    *   将拼接后的长字符串传递给 `Markdown` 组件。
    *   `Markdown` 组件对这个新内容进行解析和语法高亮渲染，这是一个消耗 CPU 的过程。
3.  **渲染瓶颈**: 当滚动很快时，上述昂贵操作会被连续触发几十次，导致 Textual 的渲染循环被阻塞，无法及时处理其他 UI 更新（如清空旧视图），从而表现为卡顿、延迟和视觉残留 (你看到的“高亮会覆盖之前没有被清空的页面”)。

### 用户需求
根据你的分析，核心需求是：
1.  解决 TUI 在快速滚动时右侧内容视图的卡顿和闪烁问题。
2.  在视图切换 (`v`) 时，确保内容面板能被正确、快速地显示和隐藏，消除视觉残留。
3.  提升 TUI 的整体交互流畅性和响应速度。

### 评论
这是一个关键的用户体验 (UX) 优化。一个流畅、响应迅速的 TUI 是工具专业性的体现。通过引入异步加载和防抖 (debouncing) 机制，我们可以从根本上解决这个问题，使 TUI 即使在处理大量历史记录时也能保持顺滑。

### 目标
1.  在 `tui.py` 中实现一个**防抖 (debouncing)** 机制，避免在快速滚动时频繁触发内容渲染。
2.  当用户滚动时，内容视图应立即显示一个“加载中...”的提示，提供即时反馈。
3.  仅当用户停止滚动一小段时间后，才执行实际的内容加载和渲染。
4.  确保该优化能附带修复视图切换时的视觉残留问题。

### 基本原理
我们将利用 `textual` 内置的定时器 (`set_timer`) 来实现防抖。

1.  当 `on_row_highlighted` 事件被触发时，我们不再直接调用内容更新函数。
2.  取而代之，我们会：
    a.  取消任何已存在的、等待执行的更新定时器。
    b.  **立即**将右侧 Markdown 面板的内容更新为 `*Loading...*`。
    c.  启动一个新的定时器，设定一个短暂的延迟 (例如 150 毫秒)。
3.  如果用户在 150 毫秒内移动到下一行，新的 `RowHighlighted` 事件会触发，并重复步骤 2a，从而取消上一个还未执行的更新。
4.  只有当用户停止滚动超过 150 毫秒，定时器才会成功触发其回调函数，该函数将执行真正昂贵的内容获取和 Markdown 渲染工作。

这个机制确保了无论用户滚动多快，昂贵的渲染操作只会在他停下来后执行一次。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #concept/ui #scope/ux
#ai/brainstorm
#task/domain/ui #task/object/tui-performance #task/action/improvement #task/state/begin

---

### Script

#### Acts 1: 为 `QuipuUiApp` 引入防抖机制

我们将修改 `packages/quipu-cli/src/quipu/cli/tui.py` 文件，为 `Markdown` 内容的更新添加防抖逻辑。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
import sys
import logging
from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual import on

from quipu.core.models import QuipuNode
~~~~~
~~~~~python
import sys
import logging
from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual import on
from textual.timer import Timer

from quipu.core.models import QuipuNode
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def __init__(self, work_dir: Path):
        super().__init__()
        self.work_dir = work_dir
        self.engine: Optional[Engine] = None
        self.view_model: Optional[GraphViewModel] = None
        # is_split_mode 是纯视图状态，保留在 App 中
        self.is_split_mode = False
~~~~~
~~~~~python
    def __init__(self, work_dir: Path):
        super().__init__()
        self.work_dir = work_dir
        self.engine: Optional[Engine] = None
        self.view_model: Optional[GraphViewModel] = None
        self.is_split_mode = False
        
        # --- Performance Optimization ---
        self.update_timer: Optional[Timer] = None
        self.debounce_delay_seconds: float = 0.15  # 150ms delay
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key.value
        if row_key:
            self.view_model.select_node_by_key(row_key)
            if self.is_split_mode:
                self._update_content_view()

    def _update_content_view(self):
        node = self.view_model.get_selected_node()
        if not node:
            return
        header = self.query_one("#content-header", Static)
        header.update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")
        content = self.view_model.get_content_bundle(node)
        markdown = self.query_one("#content-body", Markdown)
        markdown.update(content)
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

    def _debounced_update_content_view(self) -> None:
        """The expensive update logic, called only after the user stops scrolling."""
        node = self.view_model.get_selected_node()
        if not node:
            return
        
        header = self.query_one("#content-header", Static)
        header.update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")

        content = self.view_model.get_content_bundle(node)
        
        markdown_widget = self.query_one("#content-body", Markdown)
        markdown_widget.update(content)
    
    def action_toggle_view(self) -> None:
        self.is_split_mode = not self.is_split_mode
        container = self.query_one("#main-container")
        container.set_class(self.is_split_mode, "split-mode")
        
        # On view toggle, immediately update content if a row is highlighted
        if self.is_split_mode and self.view_model.get_selected_node():
            self._debounced_update_content_view()
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
        Binding("v", "toggle_view", "切换内容视图"),
~~~~~
~~~~~python
        # Re-map 'v' to the new debounced action handler
        Binding("v", "toggle_view", "切换内容视图"),
~~~~~


### 下一步建议
我们已经修改了代码逻辑。现在，你需要手动验证修复效果：
1.  重新安装开发环境的 `quipu-cli`。
2.  运行 `quipu ui` 命令进入 TUI。
3.  **验证滚动性能**: 按住 `j` 或 `k` 键快速滚动列表。确认左侧列表滚动流畅，右侧面板应显示 `*Loading...*`，并在你停止滚动后片刻才更新为最终内容。
4.  **验证视图切换**: 反复按 `v` 键，确认内容面板能够干净利落地显示和隐藏，没有之前的视觉残留问题。

如果验证通过，我们可以创建一个 `[COMMIT]` 计划来提交这些改进。
