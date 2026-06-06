import pytest
from quipu.cli.main import app
from quipu.spec.constants import EMPTY_TREE_HASH

def test_checkout_identical_tree_ambiguity_bypass(runner, quipu_workspace):
    """验证 checkout 在遇到同态树时是否能自动规避歧义。"""
    ws, git_db, engine = quipu_workspace
    
    # 1. 创建两个同态节点
    (ws / "data.txt").write_text("Hello")
    tree_h = git_db.get_tree_hash()
    
    node_1 = engine.create_plan_node(EMPTY_TREE_HASH, tree_h, "Plan 1")
    node_2 = engine.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=tree_h,
        content="Capture 2"
    )
    
    # 2. 尝试使用 tree hash 前缀进行检出
    # 以前这会因为匹配到两个节点而报错
    prefix = tree_h[:8]
    result = runner.invoke(app, ["checkout", prefix, "--work-dir", str(ws), "-f"])
    
    assert result.exit_code == 0
    assert "Workspace reset to target state" in result.output or "noAction" in result.output

def test_checkout_by_commit_hash(runner, quipu_workspace):
    """验证是否可以通过精确的 commit_hash 进行检出。"""
    ws, git_db, engine = quipu_workspace
    
    (ws / "data.txt").write_text("Target")
    node = engine.create_plan_node(EMPTY_TREE_HASH, git_db.get_tree_hash(), "Target Plan")
    commit_hash = node.commit_hash
    
    # 先切回起点
    engine.visit(EMPTY_TREE_HASH)
    assert not (ws / "data.txt").exists()
    
    # 通过 commit_hash 检出
    result = runner.invoke(app, ["checkout", commit_hash[:10], "--work-dir", str(ws), "-f"])
    assert result.exit_code == 0
    assert (ws / "data.txt").read_text() == "Target"