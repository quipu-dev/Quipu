## [WIP] refactor: 净化引擎层测试 (第三阶段)

### 用户需求
1.  **解耦**: `tests/engine/sqlite/test_writer.py` 目前依赖应用层的 `run_quipu`，这违反了分层原则。需要改用底层的 `SQLiteHistoryWriter` 进行测试。
2.  **迁移**: `tests/integration/test_idempotent_node.py` 实质上是测试引擎的去重/幂等逻辑，而非集成场景。需要将其迁移至 `tests/engine/test_deduplication.py` 并使用 `Engine` API 重写。
3.  **清理**: 删除旧的集成测试文件。

### 目标
1.  重写 `tests/engine/sqlite/test_writer.py`。
2.  创建 `tests/engine/test_deduplication.py`。
3.  删除 `tests/integration/test_idempotent_node.py`。

### 基本原理
引擎层的测试应当是自包含的，仅依赖 `quipu-engine` 包内部的组件（如 `GitDB`, `DatabaseManager`）和共享的测试辅助工具。移除对 `application` 层的依赖可以打破循环依赖，提高测试速度和稳定性。

### 标签
#intent/refine #flow/ready #priority/high #comp/tests #comp/engine #ai/instruct #task/domain/testing #task/object/test-suite #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构 `tests/engine/sqlite/test_writer.py`

我们不再使用 `run_quipu` 来“黑盒”地测试写入逻辑，而是显式地组装 `GitObjectHistoryWriter` 和 `SQLiteHistoryWriter`，验证数据是否正确地同时写入了 Git 和 SQLite。

~~~~~act
write_file tests/engine/sqlite/test_writer.py
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest
from pyquipu.engine.git_db import GitDB
from pyquipu.engine.git_object_storage import GitObjectHistoryWriter
from pyquipu.engine.sqlite_db import DatabaseManager
from pyquipu.engine.sqlite_storage import SQLiteHistoryWriter


@pytest.fixture
def sqlite_setup(tmp_path: Path):
    """创建一个配置为使用 SQLite 后端的 Git 环境。"""
    ws = tmp_path / "ws_sqlite"
    ws.mkdir()

    # Init Git
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=ws, check=True)

    git_db = GitDB(ws)
    db_manager = DatabaseManager(ws)
    db_manager.init_schema()
    
    # 组装 Writer 栈：SQLiteWriter -> GitWriter -> GitDB
    git_writer = GitObjectHistoryWriter(git_db)
    sqlite_writer = SQLiteHistoryWriter(git_writer, db_manager)

    return sqlite_writer, db_manager, git_db, ws


class TestSQLiteWriterIntegration:
    def test_dual_write_and_link(self, sqlite_setup):
        """
        验证 SQLiteHistoryWriter 是否能正确地双写到 Git 和 DB，并建立父子关系。
        不依赖 application 层的 run_quipu。
        """
        writer, db_manager, git_db, ws = sqlite_setup
        
        EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # --- Action 1: Create first node (Node A) ---
        # 模拟文件变更 A
        (ws / "a.txt").write_text("File A content")
        hash_a = git_db.get_tree_hash()
        
        node_a = writer.create_node(
            node_type="plan",
            input_tree=EMPTY_TREE,
            output_tree=hash_a,
            content="Plan A Content",
            summary_override="Write: a.txt"
        )
        commit_hash_a = node_a.commit_hash

        # --- Action 2: Create second node (Node B) ---
        # 模拟文件变更 B
        (ws / "b.txt").write_text("File B content")
        hash_b = git_db.get_tree_hash()
        
        node_b = writer.create_node(
            node_type="plan",
            input_tree=hash_a,  # Parent is A
            output_tree=hash_b,
            content="Plan B Content",
            summary_override="Write: b.txt"
        )
        commit_hash_b = node_b.commit_hash

        # --- Verification ---
        
        # 1. Verify Git plumbing
        # 确保两个 commit 都存在
        assert git_db.cat_file(commit_hash_a, "commit")
        assert git_db.cat_file(commit_hash_b, "commit")
        
        # 2. Verify SQLite Data
        conn = db_manager._get_conn()

        # Check Node B metadata
        cursor_node = conn.execute("SELECT * FROM nodes WHERE commit_hash = ?", (commit_hash_b,))
        node_row = cursor_node.fetchone()
        assert node_row is not None
        assert node_row["summary"] == "Write: b.txt"
        # 验证缓存已被写入 (Hot Path)
        assert node_row["plan_md_cache"] == "Plan B Content"

        # Check Edge A -> B
        cursor_edge = conn.execute("SELECT * FROM edges WHERE child_hash = ?", (commit_hash_b,))
        edge_row = cursor_edge.fetchone()
        assert edge_row is not None, "Edge for the second node was not created."
        assert edge_row["parent_hash"] == commit_hash_a, "The edge should point to Node A."

        db_manager.close()
~~~~~

#### Acts 2: 迁移并重写 `test_idempotent_node.py`

迁移至 `tests/engine/test_deduplication.py`，并使用 `engine_instance` fixture 进行更直接的测试。

~~~~~act
write_file tests/engine/test_deduplication.py
~~~~~
~~~~~python
from pyquipu.engine.state_machine import Engine
from tests.helpers import EMPTY_TREE_HASH


class TestDeduplication:
    def test_idempotent_plan_creation(self, engine_instance: Engine):
        """
        验证当 output_tree == input_tree 时（即操作未产生文件变更），
        Engine 仍然能够生成一个新的 Plan 节点，并在历史图谱中正确链接。
        """
        engine = engine_instance
        root_dir = engine.root_dir

        # 1. State A: Create a file
        (root_dir / "a.txt").write_text("A")
        hash_a = engine.git_db.get_tree_hash()
        
        # 通过 Engine 创建第一个节点
        node_a = engine.create_plan_node(
            input_tree=EMPTY_TREE_HASH,
            output_tree=hash_a,
            plan_content="Create A",
            summary_override="Plan A"
        )

        # 验证初始状态
        assert len(engine.history_graph) == 1
        assert engine.current_node == node_a

        # 2. State A (Idempotent): No changes
        # 我们再次调用 create_plan_node，传入相同的 hash_a
        node_b = engine.create_plan_node(
            input_tree=hash_a,
            output_tree=hash_a,  # Same as input!
            plan_content="Read A (No Change)",
            summary_override="Plan B (Idempotent)"
        )

        # 3. 验证
        # 图谱中应该有两个节点
        assert len(engine.history_graph) == 2
        
        # 验证最新的节点
        assert node_b.commit_hash != node_a.commit_hash
        assert node_b.input_tree == hash_a
        assert node_b.output_tree == hash_a
        assert node_b.node_type == "plan"
        
        # 验证父子关系
        assert node_b.parent == node_a
        assert node_a.children == [node_b]
~~~~~

#### Acts 3: 删除旧的集成测试文件

~~~~~act
delete_file tests/integration/test_idempotent_node.py
~~~~~

### 下一步建议
我们已经完成了前三个阶段（基础设施、应用层迁移、引擎层净化）。第四阶段是“集成层重新定义”，我们需要审计 `tests/integration/` 下的剩余文件，确保它们是真正的端到端测试。当前 `tests/integration` 下应主要保留 `test_sync_workflow.py`, `test_cli_workflow.py` 等。
