好的，我们继续执行计划。

下一个重构目标是 `tests/cli/test_query_commands.py`。这个文件中的多个测试用例都通过直接调用 `engine.capture_drift` 或 `engine.create_plan_node` 来内联地创建测试数据。这是典型的过程化设置，我们可以通过将其替换为对 `tests/helpers.py` 的声明式调用来极大地改善它。

我将生成一个计划，在 `tests/helpers.py` 中创建两个新的、语义化的辅助函数，专门用于生成查询测试所需的线性和分支历史，然后重构 `test_query_commands.py` 来使用它们。

## [WIP] refactor(tests): 标准化 query 命令的测试数据创建

### 用户需求

继续进行测试重构，将 `tests/cli/test_query_commands.py` 中内联创建历史记录的逻辑，替换为对 `tests/helpers.py` 中标准化辅助函数的调用。

### 评论

这是本次重构的核心收益所在。通过将测试数据创建的逻辑（例如，“创建一个捕获节点，然后创建一个计划节点”）抽象成一个单一的辅助函数调用，我们让测试用例本身变得极其清晰。测试代码的读者可以立即理解测试的初始状态（“给定一个包含捕获和计划节点的历史”），而无需解析多行底层的 `engine` API 调用。这使得测试的意图更加突出，维护也更加容易。

### 目标

1.  在 `tests/helpers.py` 中创建两个新的辅助函数：
    *   `create_linear_history_from_specs`: 一个灵活的函数，可以根据一个简单的规格列表（例如 `[{'type': 'capture', 'summary': 'Fix bug'}]`）创建线性历史。
    *   `create_query_branching_history`: 一个专用的函数，用于创建 `test_log_reachable_only` 所需的特定分支结构。
2.  重构 `tests/cli/test_query_commands.py` 中的所有测试用例，移除所有内联的 `engine.capture_drift` 和 `engine.create_plan_node` 调用。
3.  让这些测试用例转而调用上述新的辅助函数来声明式地构建其所需的历史数据。

### 基本原理

我们采用“声明式测试设置”的原则。测试的设置（Arrange）阶段应该像一份清单，清晰地描述所需的初始状态，而不是一堆如何达到该状态的指令。

新的 `create_linear_history_from_specs` 函数就是这个原则的体现。它接受一个高级的、人类可读的规格说明，并将其转化为底层的引擎操作。这不仅消除了 `test_query_commands.py` 中的代码重复，更重要的是，它将测试的“意图”和“实现”清晰地分离开来。

### 标签

#intent/refine #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/helpers #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 在 `tests/helpers.py` 中添加更灵活的历史生成器

我将在 `tests/helpers.py` 的末尾添加两个新的、功能更强大的历史创建函数，以满足 `query` 命令测试的特定需求。

~~~~~act
patch_file
tests/helpers.py
~~~~~
~~~~~python.old
    # Dirty State
    file_path.write_text("v3")

    return engine, hash_a
~~~~~
~~~~~python.new
    # Dirty State
    file_path.write_text("v3")

    return engine, hash_a


def create_linear_history_from_specs(engine: Engine, specs: List[Dict[str, Any]]):
    """
    Creates a linear history based on a list of specifications.
    Each spec is a dict: {'type': 'plan'|'capture', 'summary': str, 'content': Optional[str]}
    """
    parent_hash = EMPTY_TREE_HASH
    if engine.history_graph:
        # If history is not empty, start from the latest node
        latest_node = sorted(engine.history_graph.values(), key=lambda n: n.timestamp)[-1]
        parent_hash = latest_node.output_tree

    for i, spec in enumerate(specs):
        # Create a unique file change for each node to ensure a new tree hash
        (engine.root_dir / f"file_{time.time()}_{i}.txt").touch()
        new_hash = engine.git_db.get_tree_hash()

        if spec["type"] == "plan":
            engine.create_plan_node(
                input_tree=parent_hash,
                output_tree=new_hash,
                plan_content=spec.get("content", ""),
                summary_override=spec["summary"],
            )
        elif spec["type"] == "capture":
            engine.capture_drift(new_hash, message=spec["summary"])

        parent_hash = new_hash
    # Re-align to ensure the engine's internal graph is fully updated
    engine.align()


def create_query_branching_history(engine: Engine) -> Tuple[Engine, str]:
    """
    Creates a specific branching history for query reachability tests.
    History: root -> A -> B (HEAD)
                   \\-> C (unreachable)
    Returns the engine and the hash of state B (the HEAD).
    """
    ws = engine.root_dir
    # root -> A
    (ws / "f_a").touch()
    h_a = engine.git_db.get_tree_hash()
    node_a = engine.capture_drift(h_a, "Node A")

    # A -> B (This will become the main branch)
    (ws / "f_b").touch()
    h_b = engine.git_db.get_tree_hash()
    engine.capture_drift(h_b, "Node B")

    # Go back to A to create the branch
    engine.visit(node_a.output_tree)

    # A -> C
    (ws / "f_c").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), "Node C")

    # Checkout back to B to set it as the current HEAD for the test
    engine.visit(h_b)
    engine.align()
    return engine, h_b
~~~~~

#### Acts 2: 使用新的辅助函数重构 `test_query_commands.py`

现在，我将用一个完全重构的版本替换 `test_query_commands.py`。新的版本将不再包含任何底层的 `engine` 操作，而是完全依赖于 `helpers` 模块。

~~~~~act
write_file
tests/cli/test_query_commands.py
~~~~~
~~~~~python
import json
from unittest.mock import MagicMock

from pyquipu.cli.main import app

from ..helpers import create_linear_history_from_specs, create_query_branching_history


def test_log_empty(runner, quipu_workspace, monkeypatch):
    work_dir, _, _ = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_once_with("query.info.emptyHistory")


def test_log_output(runner, quipu_workspace, monkeypatch):
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    specs = [
        {"type": "capture", "summary": "Node 1"},
        {"type": "capture", "summary": "Node 2"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_once_with("query.log.ui.header")
    # The log is in reverse chronological order, so Node 2 comes first.
    assert "Node 2" in mock_bus.data.call_args_list[0].args[0]
    assert "Node 1" in mock_bus.data.call_args_list[1].args[0]


def test_find_command(runner, quipu_workspace, monkeypatch):
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    specs = [
        {"type": "capture", "summary": "Fix bug"},
        {"type": "plan", "summary": "Implement feature", "content": "content"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["find", "-s", "Fix", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_once_with("query.find.ui.header")
    mock_bus.data.assert_called_once()
    assert "Fix bug" in mock_bus.data.call_args.args[0]


def test_log_json_output(runner, quipu_workspace, monkeypatch):
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    create_linear_history_from_specs(engine, [{"type": "capture", "summary": "Node 1"}])

    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.data.assert_called_once()

    # Verify the data passed to bus.data is valid JSON with expected content
    json_data = json.loads(mock_bus.data.call_args.args[0])
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert "Node 1" in json_data[0]["summary"]


def test_find_json_output(runner, quipu_workspace, monkeypatch):
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    specs = [
        {"type": "capture", "summary": "Feature A"},
        {"type": "capture", "summary": "Bugfix B"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["find", "--summary", "Bugfix", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.data.assert_called_once()

    json_data = json.loads(mock_bus.data.call_args.args[0])
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert "Bugfix B" in json_data[0]["summary"]


def test_log_json_empty(runner, quipu_workspace, monkeypatch):
    work_dir, _, _ = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.data.assert_called_once_with("[]")


def test_log_filtering(runner, quipu_workspace, monkeypatch):
    """Test limit and time filtering logic for log command."""
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    specs = [
        {"type": "capture", "summary": "Node 1"},
        {"type": "capture", "summary": "Node 2"},
        {"type": "capture", "summary": "Node 3"},
    ]
    create_linear_history_from_specs(engine, specs)

    # 1. Test Limit
    result = runner.invoke(app, ["log", "-n", "1", "-w", str(work_dir)])
    assert result.exit_code == 0
    # Should only print header + 1 node
    assert mock_bus.data.call_count == 1
    assert "Node 3" in mock_bus.data.call_args_list[0].args[0]  # Newest

    # 2. Test Filtering Result Empty
    mock_bus.reset_mock()
    # Using a future date
    result = runner.invoke(app, ["log", "--since", "2099-01-01 00:00", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("query.info.noResults")


def test_log_reachable_only(runner, quipu_workspace, monkeypatch):
    """Test --reachable-only filtering for the log command."""
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    create_query_branching_history(engine)

    result = runner.invoke(app, ["log", "--reachable-only", "-w", str(work_dir)])
    assert result.exit_code == 0

    output = "".join(call.args[0] for call in mock_bus.data.call_args_list)
    assert "Node B" in output  # HEAD is reachable
    assert "Node A" in output  # Ancestor is reachable
    assert "Node C" not in output  # Unrelated branch is not reachable
~~~~~

### 下一步建议

我们已经成功地将所有主要的、重复的测试设置逻辑都提取到了 `tests/helpers.py` 中。测试代码现在更加清晰、声明式且易于维护。

本次重构任务的核心目标已经达成。我建议将此作为一个 `[COMMIT]` 点，标志着这项工作的完成。

如果你同意，我将生成一个包含 `git add` 和 `git commit` 指令的计划，来正式提交这些改进。
