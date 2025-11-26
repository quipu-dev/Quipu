## fix: 修复 TUI 中 DataTable.Scroll 属性错误并实现无限滚动

### 错误分析
在 `tui.py` 中使用了 `DataTable.Scroll` 作为事件监听器 (`@on(DataTable.Scroll)`)，但 `DataTable` 类并没有这个属性（也没有定义该类型的消息）。这导致了 `pytest` 收集测试用例时抛出 `AttributeError`。Textual 的 `DataTable` 并不直接发出 `Scroll` 消息。

### 用户需求
修复测试错误，并正确实现当用户滚动到底部时自动加载更多数据的逻辑。

### 评论
需要通过子类化 `DataTable` 来捕获滚动行为（包括鼠标滚动和键盘导航），并发射自定义消息 `NearBottom` 来触发加载。这是实现“无限滚动”的标准 Textual 模式。

### 目标
1.  在 `tui.py` 中定义 `HistoryDataTable` 子类。
2.  实现滚动检测逻辑（覆盖 `on_scroll` 事件和键盘动作）。
3.  修复 `QuipuUiApp` 以使用新组件和消息。

### 基本原理
由于 `DataTable` 没有内置的滚动到底部通知，我们需要拦截导致视图滚动的操作。通过检查 `scroll_offset.y` 与 `row_count` 的关系，判断是否接近底部，并发送自定义消息通知 App 层加载数据。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #concept/ui #scope/dx
#ai/refine
#task/domain/ui #task/object/tui #task/action/fix-scroll
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 tui.py 实现 HistoryDataTable

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~content
import sys
from typing import List, Optional, Tuple
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Markdown, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual import on, work

from quipu.core.models import QuipuNode
from .view_model import GraphViewModel

# 定义 UI 返回类型: (动作类型, 数据)
# 动作: "checkout" | "dump"
UiResult = Tuple[str, str]


class HistoryDataTable(DataTable):
    """
    自定义 DataTable，用于检测滚动到底部的事件。
    """
    class NearBottom(Message):
        """当滚动位置接近底部时发送的消息。"""
        pass

    def _check_scroll_position(self):
        """检查当前滚动位置，如果接近底部则发送 NearBottom 消息。"""
        if self.row_count == 0:
            return

        # 获取可视区域高度
        visible_height = self.size.height
        if visible_height == 0:
            return

        # scroll_offset.y 是当前顶部的行索引（浮点数）
        # 如果 (总行数 - 当前滚动位置 - 可视高度) < 阈值，则认为接近底部
        # 阈值设为 10 行
        if (self.row_count - self.scroll_offset.y - visible_height) < 10:
            self.post_message(self.NearBottom())

    def on_scroll(self, event) -> None:
        """处理滚动事件（通常由鼠标滚轮触发）。"""
        super().on_scroll(event)
        self._check_scroll_position()

    def action_cursor_down(self) -> None:
        """处理向下移动光标（键盘 j / down）。"""
        super().action_cursor_down()
        self._check_scroll_position()

    def action_page_down(self) -> None:
        """处理向下翻页（键盘 PageDown）。"""
        super().action_page_down()
        self._check_scroll_position()
    
    # 注意：还有其他可能改变滚动位置的操作，但覆盖主要操作通常足够


class QuipuUiApp(App[Optional[UiResult]]):
    CSS = """
    #main-container {
        height: 100%;
    }
    
    HistoryDataTable { 
        height: 100%; 
        background: $surface; 
        border: none; 
    }

    /* Split Mode Styles */
    .split-mode #history-table {
        width: 50%;
    }

    #content-view {
        display: none; /* 默认隐藏右侧内容区 */
        width: 50%;
        height: 100%;
        border-left: solid $primary;
        background: $surface;
    }
    
    .split-mode #content-view {
        display: block;
    }

    #content-header {
        height: 1;
        background: $primary;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    #content-body {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("v", "toggle_view", "切换内容视图"),
        Binding("p", "dump_content", "输出内容(stdout)"),
        Binding("h", "toggle_hidden", "显隐非关联分支"),
        # Vim 风格导航
        Binding("k", "move_up", "上移", show=False),
        Binding("j", "move_down", "下移", show=False),
        Binding("up", "move_up", "上移", show=False),
        Binding("down", "move_down", "下移", show=False),
    ]

    def __init__(self, view_model: GraphViewModel):
        super().__init__()
        self.view_model = view_model
        
        # UI State
        self.is_split_mode = False
        self.current_selected_node: Optional[QuipuNode] = None
        self.show_unreachable = True  # 暂时保留此标记
        
        # Graph Rendering State (Incremental)
        self.tracks: List[Optional[str]] = []
        
        # Pagination State
        self.is_loading = False
        
        # Cache for row lookups
        self.node_by_filename = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # 使用 Horizontal 容器包裹列表和内容预览
        with Horizontal(id="main-container"):
            # 使用自定义的 HistoryDataTable
            yield HistoryDataTable(id="history-table", cursor_type="row", zebra_stripes=False)

            with Vertical(id="content-view"):
                yield Static("Node Content", id="content-header")
                yield Markdown("", id="content-body")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(HistoryDataTable)
        # 初始化列
        table.add_columns("Time", "Graph", "Node Info")
        
        # 初始化 VM 并加载第一页
        self.view_model.initialize()
        self.load_more_data()

    # --- Data Loading ---

    @work(exclusive=True)
    async def load_more_data(self) -> None:
        """异步加载更多数据"""
        if self.is_loading or not self.view_model.has_more_data():
            return

        self.is_loading = True
        self.query_one(Footer).value = "正在加载更多历史记录..."
        
        try:
            # 在后台线程加载数据
            new_nodes = self.view_model.load_next_page(size=50)
            
            # 回到主线程更新 UI
            if new_nodes:
                self.call_from_thread(self._append_nodes, new_nodes)
        finally:
            self.is_loading = False
            self.query_one(Footer).value = ""

    def _append_nodes(self, new_nodes: List[QuipuNode]):
        """将新节点追加到表格中"""
        table = self.query_one(HistoryDataTable)
        
        for node in new_nodes:
            # 更新本地查找缓存
            self.node_by_filename[str(node.filename)] = node
            
            # 渲染行
            row_data = self._render_node_row(node)
            table.add_row(*row_data, key=str(node.filename))

        # 如果是第一次加载，尝试聚焦到 HEAD
        if table.cursor_row == 0 and self.view_model.current_hash:
             self._focus_current_node(table)

    def _render_node_row(self, node: QuipuNode) -> List[str]:
        """增量渲染单行数据"""
        is_reachable = self.view_model.is_reachable(node.output_tree)
        dim_tag = "[dim]" if not is_reachable else ""
        end_dim_tag = "[/dim]" if dim_tag else ""

        base_color = "magenta"
        if node.node_type == "plan":
            base_color = "green" if node.input_tree == node.output_tree else "cyan"

        # --- Graph Logic (Incremental) ---
        tracks = self.tracks
        
        merging_indices = [i for i, h in enumerate(tracks) if h == node.output_tree]
        try:
            col_idx = tracks.index(None) if not merging_indices else merging_indices[0]
        except ValueError:
            col_idx = len(tracks) if not merging_indices else merging_indices[0]

        while len(tracks) <= col_idx:
            tracks.append(None)
        tracks[col_idx] = node.output_tree

        graph_chars = []
        for i, track_hash in enumerate(tracks):
            if i == col_idx:
                symbol_char = "●" if node.node_type == "plan" else "○"
                graph_chars.append(f"{dim_tag}[{base_color}]{symbol_char}[/] {end_dim_tag}")
            elif i in merging_indices:
                graph_chars.append(f"{dim_tag}┘ {end_dim_tag}")
            elif track_hash:
                graph_chars.append(f"{dim_tag}│ {end_dim_tag}")
            else:
                graph_chars.append("  ")

        # 更新 tracks 状态以供下一行使用
        tracks[col_idx] = node.input_tree
        for i in merging_indices[1:]:
            tracks[i] = None
        while tracks and tracks[-1] is None:
            tracks.pop()
        
        # --- End Graph Logic ---

        ts_str = f"{dim_tag}{node.timestamp.strftime('%Y-%m-%d %H:%M')}{end_dim_tag}"
        graph_str = "".join(graph_chars)
        
        summary = node.summary or "No description"
        tag_char = node.node_type.upper()
        info_text = f"[{base_color}][{tag_char}] {node.short_hash}[/{base_color}] - {summary}"
        info_str = f"{dim_tag}{info_text}{end_dim_tag}"

        return [ts_str, graph_str, info_str]

    # --- Actions ---

    def action_move_up(self) -> None:
        self.query_one(HistoryDataTable).action_cursor_up()

    def action_move_down(self) -> None:
        self.query_one(HistoryDataTable).action_cursor_down()

    def action_toggle_hidden(self) -> None:
        # TODO: 由于现在是增量加载，简单的隐藏逻辑可能不再适用或需要重新实现过滤
        self.show_unreachable = not self.show_unreachable
        status = "显示" if self.show_unreachable else "隐藏"
        self.notify(f"已切换不可达节点显示: {status} (需刷新生效，功能开发中)")

    def action_toggle_view(self) -> None:
        """切换分栏预览模式"""
        self.is_split_mode = not self.is_split_mode
        container = self.query_one("#main-container")
        
        if self.is_split_mode:
            container.add_class("split-mode")
            self._update_content_view()
        else:
            container.remove_class("split-mode")

    def action_checkout_node(self) -> None:
        if self.current_selected_node:
            self.exit(result=("checkout", self.current_selected_node.output_tree))

    def action_dump_content(self) -> None:
        if self.current_selected_node:
            content = self.view_model.get_content_bundle(self.current_selected_node)
            self.exit(result=("dump", content))

    # --- Event Handlers ---

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row_key = event.row_key.value
        node = self.node_by_filename.get(row_key)
        if node:
            self.current_selected_node = node
            if self.is_split_mode:
                self._update_content_view()

    @on(HistoryDataTable.NearBottom)
    def on_history_table_near_bottom(self, event: HistoryDataTable.NearBottom) -> None:
        """当滚动到底部时触发加载"""
        self.load_more_data()

    def _focus_current_node(self, table: DataTable):
        if not self.view_model.current_hash:
            return
            
        for key, node in self.node_by_filename.items():
            if node.output_tree == self.view_model.current_hash:
                try:
                    row_index = table.get_row_index(key)
                    table.cursor_coordinate = Coordinate(row=row_index, column=0)
                    self.current_selected_node = node
                except Exception:
                    pass
                break

    def _update_content_view(self):
        if not self.current_selected_node:
            return

        node = self.current_selected_node
        header = self.query_one("#content-header", Static)
        header.update(f"[{node.node_type.upper()}] {node.short_hash} - {node.timestamp}")

        # 使用 Worker 异步加载内容，避免 UI 卡顿
        self._load_content_async(node)

    @work(exclusive=True)
    async def _load_content_async(self, node: QuipuNode):
        markdown_widget = self.query_one("#content-body", Markdown)
        
        # 在 VM 中获取内容 bundle
        content = self.view_model.get_content_bundle(node)
        
        # 回到 UI 线程更新
        self.call_from_thread(markdown_widget.update, content)
~~~~~

### 下一步建议
修复了 `tui.py` 后，需要继续 **Phase 4**，即修改 `main.py` 以正确调用新的 `QuipuUiApp` 构造函数。此外，需要修复可能因为这次重构而破坏的单元测试。
