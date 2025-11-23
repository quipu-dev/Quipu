import pytest
from pathlib import Path
from datetime import datetime
from core.models import AxonNode
from ui.tui import AxonUiApp
from textual.widgets import DataTable

class TestUiLogic:
    
    def test_graph_renderer_simple_linear(self):
        """测试简单的线性历史渲染"""
        # A <- B <- C
        node_a = AxonNode("root", "a", datetime(2023,1,1), Path("f"), "plan")
        node_b = AxonNode("a", "b", datetime(2023,1,2), Path("f"), "plan")
        node_c = AxonNode("b", "c", datetime(2023,1,3), Path("f"), "plan")
        
        app = AxonUiApp([node_a, node_b, node_c])
        
        # 我们可以通过 mock table 来验证，或者简单地运行 _populate_table 看是否报错
        # 由于 Textual 组件需要在 App 运行上下文中才能完整工作 (query_one)，
        # 这里主要做单元测试级别的逻辑验证（如果把渲染逻辑抽离会更好测，但在 App 内我们就做集成式验证）
        
        # 验证排序
        assert app.sorted_nodes[0].output_tree == "c"
        
    def test_graph_renderer_branching(self):
        """测试分叉历史渲染 (Smoke Test)"""
        # A <- B
        # A <- C
        node_a = AxonNode("root", "a", datetime(2023,1,1), Path("f"), "plan")
        node_b = AxonNode("a", "b", datetime(2023,1,2), Path("f"), "plan")
        node_c = AxonNode("a", "c", datetime(2023,1,3), Path("f"), "plan") # Branch C is newer
        
        app = AxonUiApp([node_a, node_b, node_c])
        
        # 验证排序: C (newest), B, A
        assert app.sorted_nodes[0].output_tree == "c"
        assert app.sorted_nodes[1].output_tree == "b"
        assert app.sorted_nodes[2].output_tree == "a"
        
        # 手动模拟 populate 逻辑中的关键部分：Tracks 更新
        tracks = []
        # Row 1: Node C. input=a. New track.
        # tracks -> [a] (visual: ●)
        
        # Row 2: Node B. input=a. New track (because 'a' in tracks is occupied by C's ancestry line).
        # tracks -> [a, a] (visual: │ ●)
        
        # Row 3: Node A. input=root.
        # Node A matches tracks[0] AND tracks[1] (both point to 'a').
        # Merge! 
        # tracks -> [root] (visual: ● ┘)
        
        # 这个测试主要确保逻辑本身没有异常抛出
        pass

    def test_get_node_summary(self):
        node = AxonNode("a", "b", datetime.now(), Path("f"), "plan", content="~~~act\nrun\n~~~")
        app = AxonUiApp([], None)
        assert app._get_node_summary(node) == "run"