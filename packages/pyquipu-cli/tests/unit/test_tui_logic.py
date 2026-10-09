from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from quipu.cli.tui import QuipuUiApp
from quipu.cli.view_model import GraphViewModel
from quipu.spec.models.graph import QuipuNode
from test_view_model import MockHistoryReader


@pytest.fixture
def view_model_factory():
    def _factory(nodes, current_hash=None, ancestors=None, private_data=None):
        reader = MockHistoryReader(nodes, ancestors=ancestors, private_data=private_data)
        vm = GraphViewModel(reader, current_output_tree_hash=current_hash)
        vm.initialize()
        return vm

    return _factory


class TestUiLogic:
    def test_graph_renderer_simple_linear(self, view_model_factory):
        node_a = QuipuNode("c1", "a", "root", datetime(2023, 1, 1), Path("f1"), "plan", summary="A")
        node_b = QuipuNode("c2", "b", "a", datetime(2023, 1, 2), Path("f2"), "plan", summary="B")
        node_c = QuipuNode("c3", "c", "b", datetime(2023, 1, 3), Path("f3"), "plan", summary="C")

        view_model = view_model_factory([node_a, node_b, node_c])
        app = QuipuUiApp(work_dir=Path("."))
        app.view_model = view_model

        assert app.view_model.total_nodes == 3

    def test_graph_renderer_branching(self, view_model_factory):
        node_a = QuipuNode("c1", "a", "root", datetime(2023, 1, 1), Path("f1"), "plan", summary="A")
        node_b = QuipuNode("c2", "b", "a", datetime(2023, 1, 2), Path("f2"), "plan", summary="B")
        node_c = QuipuNode("c3", "c", "a", datetime(2023, 1, 3), Path("f3"), "plan", summary="C")

        view_model = view_model_factory([node_a, node_b, node_c])
        app = QuipuUiApp(work_dir=Path("."))
        app.view_model = view_model

        assert app.view_model.total_nodes == 3

    def test_get_node_summary(self, view_model_factory):
        view_model = view_model_factory([])
        app = QuipuUiApp(work_dir=Path("."))
        app.view_model = view_model

        # Case 1: Node with a pre-set summary
        node_with_summary = QuipuNode(
            "c1", "b", "a", datetime.now(), Path("f1"), "plan", summary="This is a pre-calculated summary."
        )
        assert app._get_node_summary(node_with_summary) == "This is a pre-calculated summary."

        # Case 2: Node with an empty summary
        node_without_summary = QuipuNode(
            "c2",
            "d",
            "c",
            datetime.now(),
            Path("f2"),
            "capture",
            summary="",  # Explicitly empty
        )
        assert app._get_node_summary(node_without_summary) == "No description"

    def test_head_badge_rendered_in_table(self, view_model_factory):
        node_head = QuipuNode("c1", "tree_head", "root", datetime(2023, 1, 1), Path("f1"), "plan", summary="Head Node")
        node_other = QuipuNode(
            "c2", "tree_other", "tree_head", datetime(2023, 1, 2), Path("f2"), "plan", summary="Other Node"
        )

        view_model = view_model_factory([node_head, node_other], current_hash="tree_head")
        app = QuipuUiApp(work_dir=Path("."))
        app.view_model = view_model

        # 1. 测试干净工作区 (Clean State): 显示绿底 HEAD，不带 *
        app.is_workspace_dirty = False
        mock_table_clean = MagicMock()
        app._populate_table(mock_table_clean, [node_head, node_other])
        head_row_clean = mock_table_clean.add_row.call_args_list[0].args[2]
        assert "HEAD" in head_row_clean
        assert "HEAD*" not in head_row_clean

        # 2. 测试漂移工作区 (Dirty State): 显示 HEAD* 徽章
        app.is_workspace_dirty = True
        mock_table_dirty = MagicMock()
        app._populate_table(mock_table_dirty, [node_head, node_other])
        head_row_dirty = mock_table_dirty.add_row.call_args_list[0].args[2]
        assert "HEAD*" in head_row_dirty

        # 其它非 HEAD 节点绝不包含任何 HEAD 标记
        other_row = mock_table_dirty.add_row.call_args_list[1].args[2]
        assert "HEAD" not in other_row

    def test_on_mount_state_centric_alignment(self, monkeypatch):
        # 模拟外部 git checkout 切换到已知历史节点 hash_a，而旧 HEAD 指针仍停留在 hash_c
        app = QuipuUiApp(work_dir=Path("."))
        mock_engine = MagicMock()
        mock_engine.git_db.get_tree_hash.return_value = "tree_a"
        mock_engine._read_head.return_value = "tree_c"
        mock_engine.reader.get_node_position.side_effect = lambda h: 0 if h == "tree_a" else -1
        mock_engine.reader.get_node_count.return_value = 2

        monkeypatch.setattr("quipu.cli.tui.create_engine", lambda *args, **kwargs: mock_engine)
        monkeypatch.setattr(app, "query_one", lambda *args, **kwargs: MagicMock())
        monkeypatch.setattr(app, "_load_page", lambda *args, **kwargs: None)

        app.on_mount()

        # 验证物理状态精准命中历史节点时：自动对齐为 CLEAN，且持久化指针被更新
        assert app.is_workspace_dirty is False
        assert app.view_model.current_output_tree_hash == "tree_a"
        mock_engine._write_head.assert_called_once_with("tree_a")

    def test_on_mount_drift_detection(self, monkeypatch):
        # 模拟工作区被修改为未知内容（未在历史中找到的 tree_dirty）
        app = QuipuUiApp(work_dir=Path("."))
        mock_engine = MagicMock()
        mock_engine.git_db.get_tree_hash.return_value = "tree_dirty"
        mock_engine._read_head.return_value = "tree_c"
        mock_engine.reader.get_node_position.return_value = -1  # 未匹配
        mock_engine.reader.get_node_count.return_value = 2

        monkeypatch.setattr("quipu.cli.tui.create_engine", lambda *args, **kwargs: mock_engine)
        monkeypatch.setattr(app, "query_one", lambda *args, **kwargs: MagicMock())
        monkeypatch.setattr(app, "_load_page", lambda *args, **kwargs: None)
        monkeypatch.setattr(app, "notify", MagicMock())

        app.on_mount()

        # 验证工作区确实发生漂移时：标记为 DIRTY，基准停留在原 HEAD
        assert app.is_workspace_dirty is True
        assert app.view_model.current_output_tree_hash == "tree_c"
        mock_engine._write_head.assert_not_called()
