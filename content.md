好的，我们继续进行测试重构。

正如我们所讨论的，下一步是系统性地审查 `tests/cli` 和 `tests/engine` 目录，将其中重复的、用于搭建测试环境的逻辑提取到 `tests/helpers.py` 中。

经过审查，`tests/cli/test_export_command.py` 是最理想的重构目标。它包含了两个非常复杂的 `pytest` fixture (`populated_history` 和 `history_for_all_links`)，这些 fixture 手动、过程化地创建了复杂的历史图谱。这正是我们应该集中管理和标准化的逻辑。

我将生成一个计划，将这两个 fixture 的实现逻辑迁移到 `tests/helpers.py` 中，并让 `test_export_command.py` 调用这些新的、标准化的辅助函数。

## [WIP] refactor(tests): 标准化历史创建逻辑并迁移至 helpers

### 用户需求

继续审查 `tests/cli` 和 `tests/engine` 目录，将其中重复的 fixture 和本地辅助函数，用 `tests/helpers.py` 中的标准化函数进行替换，以提高代码的复用性和可维护性。

### 评论

这是提升测试套件质量的关键一步。`tests/cli/test_export_command.py` 中的 `populated_history` 和 `history_for_all_links` fixture 是典型的“测试异味”——它们包含了复杂的、命令式的实现细节，掩盖了测试本身的意图。

将这些复杂的历史创建逻辑封装成 `tests/helpers.py` 中的声明式函数（例如 `create_branching_history`），可以极大地净化测试文件。测试代码将从“如何构建这个复杂的历史”转变为“给我一个标准的分支历史”，这使得测试用例本身更加清晰、专注，并且极大地提高了可维护性。

### 目标

1.  在 `tests/helpers.py` 中创建两个新的辅助函数：`create_branching_history` 和 `create_complex_link_history`。
2.  将 `tests/cli/test_export_command.py` 中 `populated_history` 和 `history_for_all_links` 两个 fixture 的实现代码，分别迁移到上述两个新的辅助函数中。
3.  重构 `tests/cli/test_export_command.py`，移除本地的复杂实现，转而调用 `tests/helpers.py` 中的新函数来构建测试环境。

### 基本原理

我们遵循“分离关注点”原则。测试文件 (`test_*.py`) 的职责是**定义测试场景并执行断言**。辅助模块 (`helpers.py`) 的职责是**提供构建这些场景所需的工具和数据**。

通过将创建复杂历史记录的“如何做”的细节从测试文件中剥离，并将其放入 `helpers.py`，我们创建了一套可复用的“测试构建块”。未来任何需要类似历史结构的测试，都可以直接调用这些辅助函数，而无需重复编写或复制粘贴复杂的 `engine` 操作序列。

### 标签

#intent/refine #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/helpers #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 在 `tests/helpers.py` 中创建标准化的历史生成器

我将把 `test_export_command.py` 中的两个 fixture 的核心逻辑提取出来，并作为新的函数添加到 `tests/helpers.py` 的末尾。

~~~~~act
patch_file
tests/helpers.py
~~~~~
~~~~~python.old
    raise AssertionError(f"Could not identify Plan node among {len(new_heads)} new heads: {new_heads}")
~~~~~
~~~~~python.new
    raise AssertionError(f"Could not identify Plan node among {len(new_heads)} new heads: {new_heads}")


# --- Engine/Component Test Helpers ---


def create_branching_history(engine: Engine) -> Engine:
    """
    Creates a common branching history for testing.
    History:
    - n0 (root) -> n1 -> n2 (branch point) -> n3a (branch A) -> n4 (summary)
                                          \\-> n3b (branch B)
    """
    ws = engine.root_dir
    (ws / "file.txt").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h0, "plan 0", summary_override="Root Node")
    (ws / "file.txt").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h0, h1, "plan 1", summary_override="Linear Node 1")
    (ws / "file.txt").write_text("v2")
    h2 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2, "plan 2", summary_override="Branch Point")
    engine.visit(h2)
    (ws / "branch_a.txt").touch()
    h3a = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2, h3a, "plan 3a", summary_override="Branch A change")
    engine.visit(h3a)
    engine.create_plan_node(h3a, h3a, "plan 4", summary_override="Summary Node")
    engine.visit(h2)
    (ws / "branch_b.txt").touch()
    h3b = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2, h3b, "plan 3b", summary_override="Branch B change")
    return engine


def create_complex_link_history(engine: Engine) -> Engine:
    """
    Creates a complex history to ensure a specific node has all navigation link types.
    Node n3 will have: a parent (n2b), a child (n4), an ancestor branch point (n1),
    and an ancestor summary node (n_summary).
    """
    ws = engine.root_dir
    engine.create_plan_node(EMPTY_TREE_HASH, EMPTY_TREE_HASH, "plan sum", summary_override="Ancestor_Summary")
    (ws / "f").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h0, "plan 0", summary_override="Root")
    (ws / "f").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h0, h1, "plan 1", summary_override="Branch_Point")
    engine.visit(h1)
    (ws / "a").touch()
    h2a = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2a, "plan 2a", summary_override="Branch_A")
    engine.visit(h1)
    (ws / "b").touch()
    h2b = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2b, "plan 2b", summary_override="Parent_Node")
    engine.visit(h2b)
    (ws / "c").touch()
    h3 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2b, h3, "plan 3", summary_override="Test_Target_Node")
    engine.visit(h3)
    (ws / "d").touch()
    h4 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h3, h4, "plan 4", summary_override="Child_Node")
    return engine
~~~~~

#### Acts 2: 重构 `test_export_command.py`

现在，我将用一个更简洁的版本重写 `test_export_command.py`。它将导入新的辅助函数，并通过简单的调用来设置 fixture，从而使测试代码的意图更加清晰。

~~~~~act
write_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
import zipfile
from unittest.mock import ANY, MagicMock

import pytest
from pyquipu.cli.main import app
from pyquipu.engine.state_machine import Engine

from ..helpers import create_branching_history, create_complex_link_history


@pytest.fixture
def populated_history(engine_instance: Engine):
    """Provides a common branching history for export tests."""
    return create_branching_history(engine_instance)


@pytest.fixture
def history_for_all_links(engine_instance: Engine):
    """Provides a complex history for testing all navigation link types."""
    return create_complex_link_history(engine_instance)


def test_export_basic(runner, populated_history, monkeypatch):
    """测试基本的导出功能。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    mock_bus.success.assert_called_once_with("export.success.dir")

    assert output_dir.exists()
    files = list(output_dir.glob("*.md"))
    assert len(files) == 6
    target_file = next((f for f in files if "Branch_A_change" in f.name), None)
    assert target_file is not None
    content = target_file.read_text()
    assert content.startswith("---") and "> [!nav] 节点导航" in content


def test_export_filtering(runner, populated_history, monkeypatch):
    """测试过滤选项。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_filter"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "-n", "2"])

    assert result.exit_code == 0
    mock_bus.success.assert_called_once_with("export.success.dir")
    assert len(list(output_dir.glob("*.md"))) == 2


def test_export_edge_cases(runner, quipu_workspace, monkeypatch):
    """测试边界情况。"""
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    # Empty history
    result = runner.invoke(app, ["export", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("export.info.emptyHistory")

    # No matching nodes
    (work_dir / "f").touch()
    engine.capture_drift(engine.git_db.get_tree_hash())

    # Reset mock for second call
    mock_bus.reset_mock()

    result = runner.invoke(app, ["export", "-w", str(work_dir), "--since", "2099-01-01 00:00"])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("export.info.noMatchingNodes")


def test_export_no_frontmatter(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_fm"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-frontmatter", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert not a_file.read_text().startswith("---")


def test_export_no_nav(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_nav"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-nav", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert "> [!nav] 节点导航" not in a_file.read_text()


def test_export_zip(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_zip"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--zip"])

    assert result.exit_code == 0
    mock_bus.info.assert_any_call("export.info.zipping")
    mock_bus.success.assert_called_with("export.success.zip", path=ANY)

    zip_path = output_dir.with_suffix(".zip")
    assert not output_dir.exists() and zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert len(zf.namelist()) == 6


@pytest.mark.parametrize(
    "link_type_to_hide, text_not_expected, text_still_expected",
    [
        ("summary", "↑ [总结节点]", "↓ [上一分支点]"),
        ("branch", "↓ [上一分支点]", "← [父节点]"),
        ("parent", "← [父节点]", "→ [子节点]"),
        ("child", "→ [子节点]", "↑ [总结节点]"),
    ],
)
def test_export_hide_link_type(
    runner, history_for_all_links, link_type_to_hide, text_not_expected, text_still_expected, monkeypatch
):
    """验证 --hide-link-type 选项能成功禁用特定类型的导航链接。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_links"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(
        app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--hide-link-type", link_type_to_hide]
    )
    assert result.exit_code == 0
    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()
    assert text_not_expected not in content
    assert text_still_expected in content


def test_export_hide_multiple_link_types(runner, history_for_all_links, monkeypatch):
    """验证可以同时禁用多种链接类型。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_multi"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(
        app,
        [
            "export",
            "-w",
            str(engine.root_dir),
            "-o",
            str(output_dir),
            "--hide-link-type",
            "summary",
            "--hide-link-type",
            "child",
        ],
    )
    assert result.exit_code == 0
    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()
    assert "↑ [总结节点]" not in content and "→ [子节点]" not in content
    assert "↓ [上一分支点]" in content and "← [父节点]" in content


def test_export_reachable_only(runner, populated_history, monkeypatch):
    """测试 --reachable-only 选项是否能过滤掉无关分支。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_reachable"
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.export.bus", mock_bus)

    # The fixture leaves HEAD on branch B. We'll checkout a node on branch A.
    summary_node = next(n for n in engine.history_graph.values() if n.summary == "Summary Node")
    engine.visit(summary_node.output_tree)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--reachable-only"])
    assert result.exit_code == 0

    files = list(output_dir.glob("*.md"))
    # Branch A path: Root -> Linear 1 -> Branch Point -> Branch A -> Summary (5 nodes)
    # Branch B is now unreachable and should be excluded.
    assert len(files) == 5

    filenames = {f.name for f in files}
    assert not any("Branch_B_change" in name for name in filenames)
    assert any("Branch_A_change" in name for name in filenames)
~~~~~

### 下一步建议

我们已经成功地将最复杂的历史创建逻辑标准化了。

现在，我们可以继续审查其他的测试文件，例如 `tests/cli/test_navigation_commands.py` 中的 `populated_workspace` fixture。虽然它比刚才处理的要简单得多，但遵循同样的原则将其迁移到 `tests/helpers.py` 中，将进一步统一我们的测试代码风格，使整个测试套件更加一致和可预测。
