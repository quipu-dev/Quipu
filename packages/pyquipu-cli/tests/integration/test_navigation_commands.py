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


def test_cli_set_head(runner, populated_workspace):
    workspace, hash_a, _hash_b = populated_workspace

    # 当前状态为 B。我们在工作区增加修改而不提交
    (workspace / "dirty.txt").write_text("local edits")

    # 执行 set-head 回到状态 A
    result = runner.invoke(app, ["set-head", hash_a[:7], "-w", str(workspace), "-f"])
    assert result.exit_code == 0

    # 验证文件系统：未修改的工作区文件保持原状
    assert (workspace / "dirty.txt").exists()
    assert (workspace / "b.txt").exists()  # B 产生的文件没有被清除

    # 验证 Quipu HEAD 已指向 A
    head_content = (workspace / ".quipu" / "HEAD").read_text().strip()
    assert head_content == hash_a
