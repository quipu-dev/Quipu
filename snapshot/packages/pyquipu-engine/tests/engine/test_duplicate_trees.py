import pytest
from quipu.spec.constants import EMPTY_TREE_HASH

def test_engine_align_priority_with_identical_trees(engine_instance):
    """验证 align 逻辑是否优先选择连通性更好的节点。"""
    ws = engine_instance.root_dir
    git_db = engine_instance.git_db
    
    # 1. 构造一个正常的骨干分支: Root -> Node A
    (ws / "file.txt").write_text("v1")
    tree_v1 = git_db.get_tree_hash()
    node_a = engine_instance.create_plan_node(
        EMPTY_TREE_HASH, tree_v1, "Normal Node A", summary_override="Bone Node"
    )
    
    # 2. 手动构造一个同态但孤立的节点: Node B (Tree 也是 tree_v1, 但 parent 是空)
    # 我们直接通过底层 writer 创建一个不带父节点的同态节点
    node_b = engine_instance.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=tree_v1,
        content="Isolated Node B",
        summary_override="Isolated Node"
    )
    
    # 重新加载 graph 模拟重启或同步后的状态
    engine_instance.align()
    
    # 验证: 虽然有两个节点都指向 tree_v1，但 align 应该选择有 parent 的 node_a
    assert engine_instance.current_node is not None
    assert engine_instance.current_node.commit_hash == node_a.commit_hash
    assert engine_instance.current_node.parent is not None

def test_storage_reachability_aggregation(engine_instance):
    """验证可达性计算是否跨越同态节点进行了联合。"""
    ws = engine_instance.root_dir
    git_db = engine_instance.git_db
    
    # 分支 1: Root -> A -> B (Tree X)
    (ws / "f").write_text("1")
    h_root = engine_instance.create_plan_node(EMPTY_TREE_HASH, git_db.get_tree_hash(), "1").output_tree
    
    (ws / "f").write_text("2")
    h_a = engine_instance.create_plan_node(h_root, git_db.get_tree_hash(), "2").output_tree
    
    (ws / "f").write_text("X")
    h_x = git_db.get_tree_hash()
    node_b = engine_instance.create_plan_node(h_a, h_x, "3")
    
    # 分支 2: C (Tree X) - 孤立同态点
    node_c = engine_instance.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=h_x,
        content="Isolated"
    )
    
    # 刷新引擎
    engine_instance.align()
    
    # 验证祖先聚合: 从 h_x 开始找，应该能找到 h_root 和 h_a
    ancestors = engine_instance.reader.get_ancestor_output_trees(h_x)
    assert h_root in ancestors
    assert h_a in ancestors
    
    # 验证后代聚合: 从 h_root 开始找，应该能找到 h_x (不论是通过 node_b 还是 node_c 触达)
    descendants = engine_instance.reader.get_descendant_output_trees(h_root)
    assert h_x in descendants