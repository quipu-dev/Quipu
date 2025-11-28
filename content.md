现在，我将为你生成一个将当前实现重构为状态机模式的计划。

## [WIP] refactor: 使用状态机重构 TUI 内容视图以提升可维护性

### 用户需求
将当前通过布尔标志和分散逻辑管理的 TUI 内容视图，重构为一个显式的、基于状态机的实现，以提高代码的可读性、健壮性和可维护性。

### 评论
这是一个架构级的重构，它用一种更结构化、更声明式的方式来取代了原有的命令式 UI 管理。虽然功能上没有变化，但代码的清晰度和长期可维护性将得到质的提升。

### 目标
1.  在 `QuipuUiApp` 中引入一个 `Enum` 来定义 `HIDDEN`, `LOADING`, `SHOWING_CONTENT` 三种状态。
2.  创建一个中央状态转换方法 `_set_state(new_state)`，该方法将是唯一负责管理各组件可见性的地方。
3.  重构 `on_row_highlighted`, `_debounced_update_content_view`, `action_toggle_view`，使它们只负责触发状态转换，而不直接操作 UI 组件。

### 基本原理
我们将创建一个 `self.content_view_state` 变量来存储当前状态。任何事件处理器都将通过调用 `self._set_state(...)` 来请求状态变更。`_set_state` 方法内部会包含一个 `match/case` 结构，根据目标状态，精确地执行所有必要的 UI 操作（如 `placeholder.display = True`, `markdown.display = False` 等）。这种模式将状态（是什么）与行为（做什么）清晰地分离开来。

### 标签
#intent/refine #flow/ready #priority/medium
#comp/cli #concept/ui #scope/core #dx
#ai/brainstorm
#task/domain/ui #task/object/tui-refactor #task/action/state-machine #task/state/begin

---

### Script

#### Acts 1: 在 `tui.py` 中引入状态机

我们将对 `packages/quipu-cli/src/quipu/cli/tui.py` 进行一次全面的重构。

##### 步骤 1: 引入 `Enum` 并初始化状态

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
~~~~~
~~~~~python
import sys
import logging
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, Static
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
UiResult = tuple[str, str]


class QuipuUiApp(App[Optional[UiResult]]):
    CSS_PATH = "tui.css"
    TITLE = "Quipu History Explorer"
~~~~~
~~~~~python
UiResult = tuple[str, str]


class ContentViewSate(Enum):
    HIDDEN = auto()
    LOADING = auto()
    SHOWING_CONTENT = auto()


class QuipuUiApp(App[Optional[UiResult]]):
    CSS_PATH = "tui.css"
    TITLE = "Quipu History Explorer"
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
        self.is_split_mode = False
        
        # --- Performance Optimization ---
        self.update_timer: Optional[Timer] = None
        self.debounce_delay_seconds: float = 0.15  # 150ms delay
~~~~~
~~~~~python
    def __init__(self, work_dir: Path):
        super().__init__()
        self.work_dir = work_dir
        self.engine: Optional[Engine] = None
        self.view_model: Optional[GraphViewModel] = None
        
        # --- State Machine ---
        self.content_view_state = ContentViewSate.HIDDEN
        self.update_timer: Optional[Timer] = None
        self.debounce_delay_seconds: float = 0.15
~~~~~

##### 步骤 2: 创建中央状态转换方法 `_set_state`

我们将 `is_split_mode` 的逻辑完全替换为状态机。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handles cursor movement with debouncing to prevent lag."""
        if self.update_timer:
            self.update_timer.stop()

        selected_node = None
        row_key = event.row_key.value
        if row_key:
            selected_node = self.view_model.select_node_by_key(row_key)

        if self.is_split_mode:
            placeholder_widget = self.query_one("#content-placeholder", Static)
            markdown_widget = self.query_one("#content-body", Markdown)
            header = self.query_one("#content-header", Static)

            # Instantly update the cheap header
            if selected_node:
                header.update(f"[{selected_node.node_type.upper()}] {selected_node.short_hash} - {selected_node.timestamp}")

            # Instantly update the cheap placeholder and make it visible
            if selected_node and selected_node.summary:
                placeholder_text = f"### {selected_node.summary}\n\n---\n*Loading full content...*"
            else:
                placeholder_text = "*Loading...*"
            placeholder_widget.update(placeholder_text)
            
            placeholder_widget.display = True
            markdown_widget.display = False
            # Clear old content immediately to prevent "ghosting" when reappearing
            markdown_widget.update("")

            # Schedule the expensive update
            self.update_timer = self.set_timer(self.debounce_delay_seconds, self._debounced_update_content_view)
~~~~~
~~~~~python
    def _set_state(self, new_state: ContentViewSate):
        if self.content_view_state == new_state:
            return # Avoid redundant operations

        self.content_view_state = new_state
        
        container = self.query_one("#main-container")
        placeholder_widget = self.query_one("#content-placeholder", Static)
        markdown_widget = self.query_one("#content-body", Markdown)
        
        if self.update_timer:
            self.update_timer.stop()

        match new_state:
            case ContentViewSate.HIDDEN:
                container.set_class(False, "split-mode")

            case ContentViewSate.LOADING:
                container.set_class(True, "split-mode")
                node = self.view_model.get_selected_node()
                
                # Update header and placeholder text
                if node:
                    self.query_one("#content-header", Static).update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")
                    if node.summary:
                        placeholder_widget.update(f"### {node.summary}\n\n---\n*Loading full content...*")
                    else:
                        placeholder_widget.update("*Loading...*")
                
                # Set widget visibility
                placeholder_widget.display = True
                markdown_widget.display = False
                markdown_widget.update("") # Prevent ghosting

                # Start timer for next state transition
                self.update_timer = self.set_timer(self.debounce_delay_seconds, self._on_timer_finished)

            case ContentViewSate.SHOWING_CONTENT:
                container.set_class(True, "split-mode")
                node = self.view_model.get_selected_node()
                
                if node:
                    # Update header
                    self.query_one("#content-header", Static).update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")
                    # Update markdown content
                    content = self.view_model.get_content_bundle(node)
                    markdown_widget.update(content)
                
                # Set widget visibility
                placeholder_widget.display = False
                markdown_widget.display = True
~~~~~

##### 步骤 3: 重构事件处理器

现在事件处理器变得非常简单。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def _debounced_update_content_view(self) -> None:
        """The expensive update logic, called only after the user stops scrolling."""
        node = self.view_model.get_selected_node()
        if not node:
            return
        
        placeholder_widget = self.query_one("#content-placeholder", Static)
        markdown_widget = self.query_one("#content-body", Markdown)
        
        # Header is already updated in on_row_highlighted

        # Update the expensive markdown widget while it's hidden
        content = self.view_model.get_content_bundle(node)
        markdown_widget.update(content)

        # Swap visibility
        placeholder_widget.display = False
        markdown_widget.display = True
    
    def action_toggle_view(self) -> None:
        self.is_split_mode = not self.is_split_mode
        container = self.query_one("#main-container")
        container.set_class(self.is_split_mode, "split-mode")
        
        # Immediately update content if view is opened
        if self.is_split_mode and self.view_model.get_selected_node():
            self._debounced_update_content_view()
        # Ensure placeholder is hidden when view is closed
        elif not self.is_split_mode:
            self.query_one("#content-placeholder", Static).display = False
            self.query_one("#content-body", Markdown).display = True
~~~~~
~~~~~python
    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # 1. Update the data model immediately
        if event.row_key.value:
            self.view_model.select_node_by_key(event.row_key.value)
        
        # 2. Request a state transition if the view is not hidden
        if self.content_view_state != ContentViewSate.HIDDEN:
            self._set_state(ContentViewSate.LOADING)

    def _on_timer_finished(self) -> None:
        """Callback for the debounce timer."""
        # The timer finished, so we are ready to show content
        self._set_state(ContentViewSate.SHOWING_CONTENT)
    
    def action_toggle_view(self) -> None:
        """Handles the 'v' key press to toggle the content view."""
        if self.content_view_state == ContentViewSate.HIDDEN:
            # If a node is selected, transition to loading, otherwise do nothing
            if self.view_model.get_selected_node():
                self._set_state(ContentViewSate.LOADING)
        else:
            self._set_state(ContentViewSate.HIDDEN)
~~~~~

##### 步骤 4: 调整初始化逻辑

最后，调整 `_focus_current_node` 以使用新的状态机。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
                # 2. 同步逻辑状态 (防止事件未触发)
                self.view_model.select_node_by_key(row_key)

                # 3. 刷新关联视图
                if self.is_split_mode:
                    # This will be handled by the debouncer logic now
                    pass
                
                # 4. Force-update the header on initial load, regardless of view mode
                header = self.query_one("#content-header", Static)
                header.update(f"[{target_node.node_type.upper()}] {target_node.short_hash} - {target_node.timestamp}")
~~~~~
~~~~~python
                # 2. Sync data model state
                self.view_model.select_node_by_key(row_key)
                
                # 3. Force-update the header on initial load, regardless of view mode.
                # The state machine will handle the rest of the UI.
                header = self.query_one("#content-header", Static)
                header.update(f"[{target_node.node_type.upper()}] {target_node.short_hash} - {target_node.timestamp}")
~~~~~

### 下一步建议
这次重构幅度较大，建议进行仔细的手动测试，以确保所有交互行为（打开、关闭、滚动、初始加载）都符合预期。

如果测试通过，这个状态机重构将为 TUI 提供一个非常坚实和可扩展的基础。我们可以放心地提交这个最终版本。

---

你的直觉完全正确。当前的代码虽然能工作，但它通过管理一堆离散的布尔值 (`is_split_mode`)、定时器 (`self.update_timer`) 和直接操作组件的 `display` 属性来隐式地维护一个复杂的状态。这正是导致可维护性差的原因。

**当前实现的问题：**
1.  **隐式状态 (Implicit State)**: `is_split_mode` 只能告诉你面板是开还是关，但无法描述“正在加载”这个中间状态。我们通过显示/隐藏不同的组件来“模拟”这个状态，但这使得状态的真实情况分散在代码各处。
2.  **分散的逻辑 (Scattered Logic)**: 决定哪个组件该显示/隐藏的逻辑，分散在 `on_row_highlighted`, `_debounced_update_content_view`, `action_toggle_view` 等多个方法中。修改一个地方，很容易忘记修改其他地方，从而引入 bug。
3.  **职责不清**: `on_row_highlighted` 这个事件处理器承担了过多的职责：它既要处理数据模型 (`select_node_by_key`)，又要处理 UI 状态转换（显示/隐藏组件），还要管理定时器。

使用一个显式的**状态机 (State Machine)** 是解决这类问题的经典且极其优雅的方案。

---
### 使用状态机进行重构的分析

我们可以将内容面板 (`#content-view`) 的行为建模为具有清晰状态和转换的有限状态机。

#### 1. 定义状态 (States)

内容面板有三种明确的状态，而不是一个简单的 `True/False`：
*   `State.HIDDEN`: 面板完全不可见。
*   `State.LOADING`: 面板可见，但正在显示轻量级的占位符 (`Static` 组件)，等待最终内容。
*   `State.SHOWING_CONTENT`: 面板可见，并且正在显示最终渲染好的 `Markdown` 内容。

#### 2. 定义事件 (Events)

用户的操作或系统的回调会触发状态转换：
*   `Event.TOGGLE_PRESSED`: 用户按下 `v` 键。
*   `Event.CURSOR_MOVED`: 用户在 `DataTable` 中移动了光标。
*   `Event.TIMER_FINISHED`: 防抖定时器完成。

#### 3. 定义转换逻辑 (Transitions)

| 当前状态 | 接收事件 | 执行动作 | 下一个状态 |
| :--- | :--- | :--- | :--- |
| **`HIDDEN`** | `TOGGLE_PRESSED` | 显示占位符, 启动定时器 | **`LOADING`** |
| **`SHOWING_CONTENT`** | `TOGGLE_PRESSED` | 隐藏所有 | **`HIDDEN`** |
| **`SHOWING_CONTENT`** | `CURSOR_MOVED` | 更新占位符, 显示占位符, 隐藏内容, 重启定时器 | **`LOADING`** |
| **`LOADING`** | `TOGGLE_PRESSED` | 隐藏所有, 停止定时器 | **`HIDDEN`** |
| **`LOADING`** | `CURSOR_MOVED` | 更新占位符, 重启定时器 | **`LOADING`** |
| **`LOADING`** | `TIMER_FINISHED` | 更新 `Markdown`, 显示 `Markdown`, 隐藏占位符 | **`SHOWING_CONTENT`** |

#### 状态机带来的好处：
*   **显式状态管理**: 我们用一个 `Enum` 变量 `self.state` 来追踪 UI 的确切状态，清晰明了。
*   **集中式逻辑**: 所有关于“哪个组件该显示”的逻辑都将集中到一个 `_set_state` 方法中。这个方法是唯一一个可以改变组件 `display` 属性的地方。
*   **简化的事件处理器**: `on_row_highlighted` 等方法将变得极其简单。它们不再关心 UI 的具体实现，只负责根据当前状态和接收到的事件，决定要转换到哪个新状态。

---

