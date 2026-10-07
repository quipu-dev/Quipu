import pytest
from quipu.cli.main import app
from quipu.test_utils.helpers import create_linear_history


@pytest.fixture
def populated_workspace(quipu_workspace):
    ws, _, engine = quipu_workspace
    _, hashes = create_linear_history(engine)
    return ws, hashes["a"], hashes["b"]


def test_cli_back_forward_flow(runner, populated_workspace):
    workspace, hash_a, _hash_b = populated_workspace

    # Initial state is B. Let's checkout to A.
    res_checkout = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])
    assert res_checkout.exit_code == 0
    assert (workspace / "a.txt").exists()
    assert not (workspace / "b.txt").exists()

    # Now we are at A. Let's go back. It should go to the previous state (B).
    result_back = runner.invoke(app, ["back", "-w", str(workspace)])
    assert result_back.exit_code == 0
    assert (workspace / "b.txt").exists()
    assert not (workspace / "a.txt").exists()

    # Now we are back at B. Let's go forward to A again.
    result_fwd = runner.invoke(app, ["forward", "-w", str(workspace)])
    assert result_fwd.exit_code == 0
    assert (workspace / "a.txt").exists()
    assert not (workspace / "b.txt").exists()


def test_cli_boundary_messages(runner, populated_workspace):
    workspace, hash_a, _hash_b = populated_workspace

    # Go to a known state
    runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])

    # Back until the beginning
    runner.invoke(app, ["back", "-w", str(workspace)])  # to B
    runner.invoke(app, ["back", "-w", str(workspace)])
    result2 = runner.invoke(app, ["back", "-w", str(workspace)])  # one more should hit boundary
    assert result2.exit_code == 0

    # Forward until the end
    runner.invoke(app, ["forward", "-w", str(workspace)])  # to B
    runner.invoke(app, ["forward", "-w", str(workspace)])  # to A
    result3 = runner.invoke(app, ["forward", "-w", str(workspace)])
    assert result3.exit_code == 0


def test_checkout_not_found(runner, populated_workspace):
    workspace, _, _ = populated_workspace

    result = runner.invoke(app, ["checkout", "nonexistent", "-w", str(workspace)])
    assert result.exit_code == 1


def test_checkout_duplicate_tree_hashes(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    # 创建状态 A
    (work_dir / "file.txt").write_text("v1")
    hash_a = engine.git_db.get_tree_hash()

    # 产生两个拥有相同 output_tree (hash_a) 但不同 commit 的节点
    engine.create_plan_node("genesis", hash_a, "Plan 1", summary_override="Node 1")
    engine.create_plan_node(hash_a, hash_a, "Plan 2", summary_override="Node 2")

    # 执行 checkout 哈希前缀
    result = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(work_dir), "-f"])
    assert result.exit_code == 0
    assert (work_dir / "file.txt").read_text() == "v1"
