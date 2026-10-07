import pytest
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.engine.state_machine import Engine


class TestHeadTracking:
    @pytest.fixture
    def engine_with_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        import subprocess

        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        # Config git user
        subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo, check=True)

        from quipu.engine.git_db import GitDB

        git_db = GitDB(repo)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        return Engine(repo, db=git_db, reader=reader, writer=writer)

    def test_head_persistence(self, engine_with_repo):
        engine = engine_with_repo

        # 1. 初始状态，无 HEAD
        assert not engine.head_file.exists()
        assert engine._read_head() is None

        # 2. 创建一个 Plan 节点
        # 这会自动更新 HEAD
        (engine.root_dir / "a.txt").touch()
        tree1 = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", tree1, "plan content")

        assert engine.head_file.exists()
        assert engine._read_head() == tree1

        # 3. Align 应该保持 HEAD
        engine.align()
        assert engine._read_head() == tree1

    def test_drift_uses_head(self, engine_with_repo):
        engine = engine_with_repo

        # 1. 建立 State A 并确立 HEAD
        (engine.root_dir / "f.txt").write_text("v1")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "setup")
        assert engine._read_head() == hash_a

        # 2. 制造漂移 (State B)
        (engine.root_dir / "f.txt").write_text("v2")
        hash_b = engine.git_db.get_tree_hash()

        # 3. 捕获漂移
        # 此时 engine 应该读取 HEAD (hash_a) 作为 input_tree
        capture_node = engine.capture_drift(hash_b)

        assert capture_node.input_tree == hash_a
        assert capture_node.output_tree == hash_b

        # 4. 验证 capture 后 HEAD 更新
        assert engine._read_head() == hash_b

    def test_checkout_updates_head(self, engine_with_repo):
        engine = engine_with_repo

        # 1. Create State A (Plan)
        (engine.root_dir / "f.txt").write_text("v1")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "State A")

        # 2. Create State B (Plan)
        (engine.root_dir / "f.txt").write_text("v2")
        hash_b = engine.git_db.get_tree_hash()
        engine.create_plan_node(hash_a, hash_b, "State B")

        assert engine._read_head() == hash_b

        # 3. Checkout to State A
        engine.checkout(hash_a)

        # 4. Assert Physical State
        assert (engine.root_dir / "f.txt").read_text() == "v1"

        # 5. Assert Logical State (HEAD)
        assert engine._read_head() == hash_a

    def test_capture_drift_on_detached_head(self, engine_with_repo):
        engine = engine_with_repo
        engine.align()

        # 1. Create linear history A -> B
        (engine.root_dir / "f.txt").write_text("state A")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "State A")

        (engine.root_dir / "f.txt").write_text("state B")
        hash_b = engine.git_db.get_tree_hash()
        engine.create_plan_node(hash_a, hash_b, "State B")
        engine.align()  # History graph is now loaded, B is the latest node

        # 2. Checkout to the older node A. This moves the HEAD pointer.
        engine.checkout(hash_a)
        assert engine._read_head() == hash_a

        # 3. Create a new change (State C) based on State A
        (engine.root_dir / "f.txt").write_text("state C")
        hash_c = engine.git_db.get_tree_hash()

        # 4. Capture the drift. This should create Node C parented to A.
        node_c = engine.capture_drift(hash_c, message="State C")

        # 5. Assertions
        # The parent MUST be A, not B. This proves the logic reads HEAD
        # and doesn't just fall back to the "latest" node.
        assert node_c.input_tree == hash_a
        assert node_c.input_tree != hash_b
        assert node_c.output_tree == hash_c
        assert engine._read_head() == hash_c

    def test_set_head_preserves_workspace_files(self, engine_with_repo):
        engine = engine_with_repo

        # 1. 建立状态 A
        (engine.root_dir / "f.txt").write_text("v1")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "Node A")

        # 2. 建立状态 B
        (engine.root_dir / "f.txt").write_text("v2")
        hash_b = engine.git_db.get_tree_hash()
        engine.create_plan_node(hash_a, hash_b, "Node B")
        assert engine._read_head() == hash_b

        # 3. 模拟本地在状态 B 之后做了未提交修改 v3
        (engine.root_dir / "f.txt").write_text("v3-dirty")

        # 4. 执行 set_head 到 A (软重置)
        target_node = engine.set_head(hash_a[:7])

        # 5. 验证：物理工作区文件完全没有被覆盖！
        assert (engine.root_dir / "f.txt").read_text() == "v3-dirty"
        assert engine._read_head() == hash_a
        assert target_node.output_tree == hash_a

        # 6. 下次捕获漂移时，父节点应当是 A 而不是 B
        hash_c = engine.git_db.get_tree_hash()
        node_c = engine.capture_drift(hash_c, message="Drift from A")
        assert node_c.input_tree == hash_a

    def test_set_head_in_lazy_unaligned_engine(self, tmp_path):
        import subprocess

        from quipu.engine.git_db import GitDB
        from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter

        repo = tmp_path / "lazy_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo, check=True)

        git_db = GitDB(repo)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)

        # 1. 产生一个节点
        (repo / "f.txt").write_text("v1")
        hash_1 = git_db.get_tree_hash()
        writer.create_node("plan", "genesis", hash_1, "Node 1")

        # 2. 模拟全新无缓存/无对齐启动的 Engine 实例 (history_graph 为空)
        lazy_engine = Engine(repo, db=git_db, reader=reader, writer=writer)
        assert len(lazy_engine.history_graph) == 0

        # 3. 在未 align 的情况下直接执行 set_head (必须正常工作，不报错)
        target_node = lazy_engine.set_head(hash_1[:7])
        assert target_node.output_tree == hash_1
        assert lazy_engine._read_head() == hash_1
