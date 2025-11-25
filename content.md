这是一个彻底的重构方案，我们将把 `ui/tui.py` 从基于 `Tree` 的组件重写为基于 `DataTable` 的时间轴视图，并在 `main.py` 中注入当前状态信息以实现自动定位。

### 1. 重构 UI 模块 (ui/tui.py)

我们将废弃原有的树状实现，引入 `DataTable`。为了实现类似 `git log --graph` 的视觉效果，我们需要对节点按时间倒序排列，并根据父子关系生成简单的 ASCII 连线符号。

~~~act
write_file
~~~
~~~path
ui/tui.py
~~~
~~~python
import sys
from datetime import datetime
from typing import List, Optional
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from textual.binding import Binding

# 确保能从上级目录导入 core 模块
sys.path.append('..')
from core.models import AxonNode

class AxonUiApp(App):
    """
    Axon Timeline Explorer
    一个基于 DataTable 的时间轴历史浏览器，类似于 git log --graph。
    """

    CSS = """
    DataTable {
        height: 100%;
        background: $surface;
        border: none;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
    ]

    def __init__(self, nodes: List[AxonNode], current_hash: Optional[str] = None):
        super().__init__()
        # 1. 数据预处理：按时间戳倒序排列 (最新的在上面)
        self.sorted_nodes = sorted(nodes, key=lambda n: n.timestamp, reverse=True)
        self.current_hash = current_hash
        self.node_map = {node.output_tree: node for node in nodes}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        """初始化表格数据与样式"""
        table = self.query_one(DataTable)
        
        # 定义列
        table.add_columns("Time", "Graph", "Node Info")
        
        # 填充数据
        self._populate_table(table)
        
        # 自动定位到当前状态
        self._focus_current_node(table)
        
        table.focus()

    def _populate_table(self, table: DataTable):
        """
        构建时间轴视图。
        为了模拟简单的 Graph 效果，我们检查当前节点是否是上一行节点的父节点。
        """
        for i, node in enumerate(self.sorted_nodes):
            # 1. Time Column
            ts_str = node.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            # 2. Graph Column (Simple Logic)
            # 如果不是第一行，且当前节点是上一行节点的父节点，则画竖线，否则画分叉
            graph_symbol = "│" 
            if i > 0:
                prev_node = self.sorted_nodes[i-1]
                if prev_node.parent != node:
                    # 上一行的父节点不是我 -> 说明这里发生了分支跳跃或合并
                    graph_symbol = "├─↗"
            
            # 对最新的节点（第一行）做特殊标记
            if i == 0:
                graph_symbol = "o"

            # 3. Info Column
            node_type_code = "[P]" if node.node_type == "plan" else "[C]"
            short_hash = node.short_hash
            summary = self._get_node_summary(node)
            
            info_str = f"{node_type_code} {short_hash} - {summary}"
            
            # 添加行，使用 full hash 作为 key 以便查找
            table.add_row(ts_str, graph_symbol, info_str, key=node.output_tree)

    def _get_node_summary(self, node: AxonNode) -> str:
        """提取简洁的摘要信息"""
        content = node.content.strip()
        lines = content.split('\n')
        
        summary = "No description"
        
        if node.node_type == 'plan':
            # 尝试提取第一个 Act
            for line in lines:
                clean_line = line.strip()
                # 忽略围栏符号
                if clean_line.startswith(('~~~', '```')):
                    continue
                if clean_line:
                    # 如果是 act 指令行（通常比较短），直接用
                    summary = clean_line
                    break
        elif node.node_type == 'capture':
            # 尝试提取用户备注或变更摘要
            user_msg = ""
            for line in lines:
                if "### 💬 备注:" in line:
                    continue
                if line.strip() and not line.startswith(('#', '`', '-')):
                     user_msg = line.strip()
                     break
            
            if user_msg:
                summary = user_msg
            else:
                summary = "Workspace Snapshot"

        # 截断过长的文本
        return (summary[:60] + '...') if len(summary) > 60 else summary

    def _focus_current_node(self, table: DataTable):
        """尝试定位并高亮当前工作区对应的行"""
        if not self.current_hash:
            return

        try:
            # DataTable 使用 row_key (也就是 output_tree) 来定位
            # get_row_index 会返回行号
            row_index = table.get_row_index(self.current_hash)
            table.move_cursor(row=row_index)
        except Exception:
            # 当前哈希可能不在历史记录中（例如全新的脏状态），此时默认停留在顶部
            pass

    def action_checkout_node(self) -> None:
        """处理检出动作"""
        table = self.query_one(DataTable)
        try:
            # 获取选中行的 Key (即 output_tree hash)
            selected_hash = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            if selected_hash:
                self.exit(result=selected_hash)
        except Exception:
            pass
~~~

### 2. 更新 Main 入口 (main.py)

我们需要修改 `main.py` 中的 `ui` 命令，使其在启动 UI 前获取当前工作区的 Tree Hash，并将其传递给 `AxonUiApp`。

~~~act
replace
~~~
~~~path
main.py
~~~
~~~old_string
    app_instance = AxonUiApp(root_nodes)
    selected_hash = app_instance.run()

    if selected_hash:
        typer.secho(f"\n> TUI 请求检出到: {selected_hash[:7]}", err=True)
        _execute_checkout(ctx, graph[selected_hash], work_dir)
~~~
~~~new_string
    # 获取当前工作区状态哈希，用于在 UI 中自动定位
    current_hash = engine.git_db.get_tree_hash()
    
    # 传入所有节点（不仅仅是 root_nodes，因为我们需要线性列表）和当前哈希
    all_nodes = list(graph.values())
    
    app_instance = AxonUiApp(all_nodes, current_hash=current_hash)
    selected_hash = app_instance.run()

    if selected_hash:
        typer.secho(f"\n> TUI 请求检出到: {selected_hash[:7]}", err=True)
        _execute_checkout(ctx, graph[selected_hash], work_dir)
~~~

### 3. 验证变更

为了确保新的 `DataTable` 逻辑不会导致崩溃，我们将创建一个新的集成测试。这个测试将模拟 UI 的初始化逻辑（不启动真正的 TUI loop，只测试数据填充）。

~~~act
write_file
~~~
~~~path
tests/test_ui_logic.py
~~~
~~~~~python
import pytest
from pathlib import Path
from datetime import datetime
from core.models import AxonNode
from ui.tui import AxonUiApp

class TestUiLogic:
    
    def test_populate_table_ordering(self):
        """测试 UI 数据填充的排序逻辑"""
        # 构造乱序的节点
        node1 = AxonNode(
            input_tree="a", output_tree="b", 
            timestamp=datetime(2023, 1, 1, 10, 0), 
            filename=Path("f1"), node_type="plan", content="Oldest"
        )
        node2 = AxonNode(
            input_tree="b", output_tree="c", 
            timestamp=datetime(2023, 1, 1, 12, 0), 
            filename=Path("f2"), node_type="plan", content="Newest"
        )
        
        nodes = [node1, node2]
        app = AxonUiApp(nodes, current_hash="c")
        
        # 验证构造函数是否正确排序（倒序）
        assert app.sorted_nodes[0] == node2
        assert app.sorted_nodes[1] == node1
        
    def test_get_node_summary_plan(self):
        """测试 Plan 节点的摘要提取"""
        content = """
~~~act
write_file
~~~
~~~path
test.txt
~~~
"""
        node = AxonNode(
            input_tree="a", output_tree="b", timestamp=datetime.now(),
            filename=Path("f"), node_type="plan", content=content
        )
        app = AxonUiApp([], None)
        summary = app._get_node_summary(node)
        assert summary == "write_file"

    def test_get_node_summary_capture(self):
        """测试 Capture 节点的摘要提取"""
        content = """
# Snapshot
### 💬 备注:
Fix critical bug
### 📝 变更文件摘要:
...
"""
        node = AxonNode(
            input_tree="a", output_tree="b", timestamp=datetime.now(),
            filename=Path("f"), node_type="capture", content=content
        )
        app = AxonUiApp([], None)
        summary = app._get_node_summary(node)
        assert summary == "Fix critical bug"

~~~~~

### 4. 执行测试

运行新添加的 UI 逻辑测试。

~~~act
run_command
~~~
~~~command
pytest tests/test_ui_logic.py
~~~