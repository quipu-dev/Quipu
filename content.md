好的，我将为你创建一个健壮的测试计划，以确保 `quipu cache prune-refs` 命令的行为符合预期，能够正确识别并清理冗余引用，同时保留必要的分支末端引用。

## [WIP] test: 为 `quipu cache prune-refs` 命令添加测试用例

### 用户需求
为 `quipu cache prune-refs` 命令编写一套完整的测试用例，覆盖以下场景：
1.  存在冗余引用的标准场景。
2.  没有冗余引用的场景。
3.  在空仓库中运行的场景。

### 评论
为 `prune-refs` 添加测试是至关重要的，它能确保这个手动清理工具的正确性和安全性，防止因逻辑错误导致的数据丢失。

### 目标
1.  在 `tests/cli/test_cache_commands.py` 中添加一个新的测试类或一组测试函数。
2.  创建一个包含线性和分支历史的 pytest fixture，以模拟一个包含冗余引用的复杂仓库状态。
3.  编写测试用例，验证修剪前后的引用状态以及 `MessageBus` 的输出。

### 基本原理
测试的核心是构建一个已知的、可复现的 Git ref 状态。通过 `engine_instance` 创建一个包含多个节点的历史图谱（包括线性链和分支），由于 `GitObjectHistoryWriter` 的默认行为是为每个节点创建 head，这将自然地产生冗余引用。然后，我们运行 `prune-refs` 命令，并断言文件系统中的 ref 文件数量和 `bus` 的输出是否符合预期。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #comp/cli #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/prune-refs-command #task/action/implement #task/state/continue

---

### Script

#### Acts 1: 创建测试用的历史图谱 Fixture

我们将在 `test_cache_commands.py` 中添加一个 fixture，它会创建一个包含 5 个节点和 5 个 head 引用的历史记录。其中 3 个引用是冗余的。

**历史结构**: `root -> n1 -> n2 (分支点) -> n3a` 且 `n2 -> n3b`
**预期结果**: 只有 `n3a` 和 `n3b` 的引用被保留。

~~~~~act
patch_file
tests/cli/test_cache_commands.py
~~~~~
~~~~~python
from unittest.mock import MagicMock

from pyquipu.cli.main import app


def test_cache_sync(runner, quipu_workspace, monkeypatch):
~~~~~
~~~~~python
from unittest.mock import MagicMock

import pytest
from pyquipu.cli.main import app
from pyquipu.engine.state_machine import Engine


@pytest.fixture
def history_with_redundant_refs(engine_instance: Engine):
    """
    创建一个包含线性和分支历史的仓库，这将生成冗余的 head 引用。
    History: root -> n1 -> n2 (branch point) -> n3a (leaf)
                                            \\-> n3b (leaf)
    Expected redundant refs: root, n1, n2
    Expected preserved refs: n3a, n3b
    """
    engine = engine_instance
    ws = engine.root_dir

    # root
    (ws / "file.txt").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    n_root = engine.capture_drift(h0, "root")

    # n1
    (ws / "file.txt").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    n1 = engine.capture_drift(h1, "n1")

    # n2 (branch point)
    (ws / "file.txt").write_text("v2")
    h2 = engine.git_db.get_tree_hash()
    n2 = engine.capture_drift(h2, "n2")

    # n3a (leaf A)
    engine.visit(n2.output_tree)
    (ws / "a.txt").touch()
    h3a = engine.git_db.get_tree_hash()
    engine.capture_drift(h3a, "n3a")

    # n3b (leaf B)
    engine.visit(n2.output_tree)
    (ws / "b.txt").touch()
    h3b = engine.git_db.get_tree_hash()
    engine.capture_drift(h3b, "n3b")

    return engine


def test_cache_sync(runner, quipu_workspace, monkeypatch):
~~~~~

#### Acts 2: 添加 `prune-refs` 的核心测试用例

现在我们利用上面创建的 fixture 来编写测试。

~~~~~act
patch_file
tests/cli/test_cache_commands.py
~~~~~
~~~~~python
    result = runner.invoke(app, ["cache", "rebuild", "-w", str(work_dir)])

    assert result.exit_code == 0
    mock_bus.warning.assert_called_once_with("cache.rebuild.info.dbNotFound")
    mock_bus.info.assert_called_once_with("cache.sync.info.hydrating")
    mock_bus.success.assert_called_once_with("cache.sync.success")
~~~~~
~~~~~python
    result = runner.invoke(app, ["cache", "rebuild", "-w", str(work_dir)])

    assert result.exit_code == 0
    mock_bus.warning.assert_called_once_with("cache.rebuild.info.dbNotFound")
    mock_bus.info.assert_called_once_with("cache.sync.info.hydrating")
    mock_bus.success.assert_called_once_with("cache.sync.success")


def test_cache_prune_refs_with_redundancy(runner, history_with_redundant_refs, monkeypatch):
    """
    测试 prune-refs 命令是否能正确识别并删除冗余引用。
    """
    engine = history_with_redundant_refs
    work_dir = engine.root_dir
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.cache.bus", mock_bus)

    refs_dir = work_dir / ".git" / "refs" / "quipu" / "local" / "heads"
    assert len(list(refs_dir.iterdir())) == 5, "Pre-condition: 5 refs should exist before pruning"

    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
    mock_bus.info.assert_any_call("cache.prune.info.scanning")
    mock_bus.info.assert_any_call("cache.prune.info.found", count=3, total=5)
    mock_bus.success.assert_called_with("cache.prune.success", count=3)
    assert len(list(refs_dir.iterdir())) == 2, "Post-condition: 2 refs should remain after pruning"


def test_cache_prune_refs_no_redundancy(runner, history_with_redundant_refs, monkeypatch):
    """
    测试在没有冗余引用的情况下运行 prune-refs。
    """
    engine = history_with_redundant_refs
    work_dir = engine.root_dir
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.cache.bus", mock_bus)

    # 第一次运行以清理
    runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])
    mock_bus.reset_mock()  # 重置 mock 以进行第二次断言

    # 第二次运行，此时应没有冗余
    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
    mock_bus.info.assert_called_once_with("cache.prune.info.scanning")
    mock_bus.success.assert_called_once_with("cache.prune.info.noRedundant")


def test_cache_prune_refs_empty_repo(runner, quipu_workspace, monkeypatch):
    """
    测试在空仓库（无任何 quipu 引用）上运行 prune-refs。
    """
    work_dir, _, _ = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.cache.bus", mock_bus)

    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
    mock_bus.info.assert_called_once_with("cache.prune.info.scanning")
    mock_bus.success.assert_called_once_with("cache.prune.info.noRedundant")
~~~~~

### 下一步建议
现在你可以运行 `qd` 的测试套件了。这些新增的测试将全面覆盖 `prune-refs` 命令的功能，确保其在各种情况下的行为都符合预期。
