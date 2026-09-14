from pathlib import Path

from quipu.application.factory import create_engine
from quipu.engine.git_storage import GitSnapshotStorage
from quipu.engine.memory_index import InMemoryGraphIndex
from quipu.spec.constants import EMPTY_TREE_HASH


def test_engine_ci_mode_no_cache_zero_io(git_workspace: Path):
    db_file = git_workspace / ".quipu" / "history.sqlite"
    assert not db_file.exists(), "初始状态不应存在 sqlite 数据库"

    # 1. 以无缓存模式启动引擎 (专为 CI/CD 设计)
    engine = create_engine(git_workspace, lazy=False, use_cache=False)

    # 验证索引类型
    assert isinstance(engine.index, InMemoryGraphIndex)
    assert engine.db_manager is None
    assert not db_file.exists(), "初始化后不应创建 sqlite 文件"

    # 2. 捕获漂移
    (git_workspace / "ci_artifact.txt").write_text("build-123")
    tree_hash_1 = engine.storage.get_tree_hash()
    capture_node = engine.capture_drift(tree_hash_1, message="CI drift capture")

    assert capture_node is not None
    assert not db_file.exists(), "捕获漂移后绝对不应生成 sqlite 文件"

    # 3. 创建 Plan 节点
    (git_workspace / "ci_artifact.txt").write_text("build-456")
    tree_hash_2 = engine.storage.get_tree_hash()
    plan_node = engine.create_plan_node(tree_hash_1, tree_hash_2, "# CI Test Plan")

    assert plan_node is not None
    assert not db_file.exists(), "创建 Plan 节点后绝对不应生成 sqlite 文件"

    # 4. 验证 Git 底层物理事实已正确落盘
    heads = engine.git_db.get_all_ref_heads("refs/quipu/local/heads/")
    head_hashes = {h[0] for h in heads}
    assert capture_node.commit_hash in head_hashes
    assert plan_node.commit_hash in head_hashes

    # 5. 内存中拓扑正常维系
    assert plan_node.parent == capture_node
    assert capture_node.children == [plan_node]


def test_cache_projector_rebuild_from_scratch(git_workspace: Path):
    db_file = git_workspace / ".quipu" / "history.sqlite"

    # 1. 正常运行并落盘一些历史到 Git 与 SQLite
    engine = create_engine(git_workspace, lazy=False, use_cache=True)
    (git_workspace / "file.txt").write_text("v1")
    h1 = engine.storage.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h1, "Plan 1")

    (git_workspace / "file.txt").write_text("v2")
    h2 = engine.storage.get_tree_hash()
    n2 = engine.create_plan_node(h1, h2, "Plan 2")

    assert db_file.exists()
    assert engine.index.get_node_count() == 2

    # 关闭引擎连接
    engine.close()

    # 2. 模拟灾难或缓存丢弃：物理删除 SQLite 数据库
    db_file.unlink()
    assert not db_file.exists()

    # 3. 重新以有缓存模式启动引擎 (触发自动投影)
    new_engine = create_engine(git_workspace, lazy=False, use_cache=True)
    try:
        assert db_file.exists(), "数据库应当被自动重建"
        assert new_engine.index.get_node_count() == 2, "所有节点应当被完整投影"

        rebuilt_node = new_engine.index.get_node(n2.commit_hash)
        assert rebuilt_node is not None
        assert rebuilt_node.output_tree == h2
        assert rebuilt_node.summary == "Plan 2"
    finally:
        new_engine.close()


def test_git_snapshot_storage_isolated(git_workspace: Path):
    storage = GitSnapshotStorage(git_workspace)

    (git_workspace / "app.py").write_text("print('hello')")
    tree_hash = storage.capture_workspace()
    assert len(tree_hash) == 40

    node, meta_json = storage.create_snapshot_commit(
        node_type="plan",
        input_tree=EMPTY_TREE_HASH,
        output_tree=tree_hash,
        content="# My Plan",
    )

    assert node.commit_hash is not None
    assert "My Plan" in meta_json

    # 验证工作区检出恢复
    (git_workspace / "app.py").write_text("print('modified')")
    assert storage.get_tree_hash() != tree_hash

    storage.restore_workspace(tree_hash)
    assert (git_workspace / "app.py").read_text() == "print('hello')"


def test_in_memory_graph_index_isolated():
    index = InMemoryGraphIndex()
    assert index.get_node_count() == 0

    from datetime import datetime

    from quipu.spec.models.graph import QuipuNode

    n1 = QuipuNode(
        commit_hash="c1",
        input_tree=EMPTY_TREE_HASH,
        output_tree="t1",
        timestamp=datetime.now(),
        filename=Path("c1"),
        node_type="plan",
        summary="Initial Plan",
    )
    n2 = QuipuNode(
        commit_hash="c2",
        input_tree="t1",
        output_tree="t2",
        timestamp=datetime.now(),
        filename=Path("c2"),
        node_type="plan",
        summary="Second Plan",
        parent=n1,
    )

    index.record_node(n1)
    index.record_node(n2)

    assert index.get_node_count() == 2
    assert index.get_ancestor_output_trees("t2") == {"t1"}
    assert index.get_descendant_output_trees("t1") == {"t2"}
    assert len(index.find_nodes(summary_regex="Initial")) == 1
