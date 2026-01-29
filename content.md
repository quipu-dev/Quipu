好的，我们现在进行最后的大规模清理。这一步将通过替换测试套件和核心逻辑中残留的硬编码哈希值，彻底完成 `EMPTY_TREE_HASH` 的常量化迁移。

## [WIP] refactor: 全面清理测试中的硬编码 EMPTY_TREE_HASH

### 用户需求

根据 `rg` 扫描结果，将 `pyquipu-engine` 下所有测试文件以及逻辑文件中残留的 `"4b825dc642cb6eb9a060e54bf8d69288fbee4904"` 字符串替换为 `quipu.spec.constants.EMPTY_TREE_HASH`。

### 评论

这是重构中“消除魔术值”阶段的收尾工作。虽然这些硬编码值大多存在于测试中，但统一它们对于保持代码库的专业性和可维护性至关重要。

### 目标

1.  更新 `pyquipu-engine` 下的集成测试和单元测试文件，导入并使用 `EMPTY_TREE_HASH`。
2.  清理 `git_object_storage.py` 和 `state_machine.py` 中剩余的硬编码实例。

### 基本原理

*   **单一事实来源 (SSoT)**: 通过将所有对空树哈希的引用指向 `spec.constants`，我们确保了系统底座的唯一性。
*   **代码整洁**: 移除散落在各处的本地常量定义（如 `genesis_hash`, `genesis_tree`），使用统一的命名。

### 标签

#intent/refine #flow/ready #priority/medium #comp/spec #comp/engine #comp/tests #scope/api #ai/instruct #task/domain/architecture #task/object/unification #task/action/cleanup #task/state/continue

---

### Script

#### Acts 2: 更新集成测试（Git Backend）

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_branching.py
~~~~~
~~~~~python.old
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
~~~~~
~~~~~python.new
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_branching.py
~~~~~
~~~~~python.old
    # 1. Base Node A
    (repo / "f.txt").write_text("v1")
    hash_a = git_db.get_tree_hash()
    writer.create_node("plan", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", hash_a, "Node A")
~~~~~
~~~~~python.new
    # 1. Base Node A
    (repo / "f.txt").write_text("v1")
    hash_a = git_db.get_tree_hash()
    writer.create_node("plan", EMPTY_TREE_HASH, hash_a, "Node A")
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_writer.py
~~~~~
~~~~~python.old
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryWriter
~~~~~
~~~~~python.new
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_writer.py
~~~~~
~~~~~python.old
        # 2. 调用 create_node
        plan_content = "# feat: Initial implementation\nThis is the first version."
        node = writer.create_node(
            node_type="plan",
            input_tree="4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # Empty tree
            output_tree=output_tree,
            content=plan_content,
        )
~~~~~
~~~~~python.new
        # 2. 调用 create_node
        plan_content = "# feat: Initial implementation\nThis is the first version."
        node = writer.create_node(
            node_type="plan",
            input_tree=EMPTY_TREE_HASH,  # Empty tree
            output_tree=output_tree,
            content=plan_content,
        )
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_reader.py
~~~~~
~~~~~python.old
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
~~~~~
~~~~~python.new
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_reader.py
~~~~~
~~~~~python.old
    def test_load_linear_history(self, reader_setup):
        reader, writer, git_db, repo = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        (repo / "a").touch()
~~~~~
~~~~~python.new
    def test_load_linear_history(self, reader_setup):
        reader, writer, git_db, repo = reader_setup

        h0 = EMPTY_TREE_HASH

        (repo / "a").touch()
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_reader.py
~~~~~
~~~~~python.old
    def test_load_forked_history(self, reader_setup):
        reader, writer, git_db, repo = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        (repo / "base").touch()
~~~~~
~~~~~python.new
    def test_load_forked_history(self, reader_setup):
        reader, writer, git_db, repo = reader_setup

        h0 = EMPTY_TREE_HASH
        (repo / "base").touch()
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_git_reader.py
~~~~~
~~~~~python.old
    def test_parent_linking_with_gap(self, reader_setup):
        reader, writer, git_db, _ = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # Helper to create a valid tree object in the ODB
~~~~~
~~~~~python.new
    def test_parent_linking_with_gap(self, reader_setup):
        reader, writer, git_db, _ = reader_setup

        h0 = EMPTY_TREE_HASH

        # Helper to create a valid tree object in the ODB
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_engine.py
~~~~~
~~~~~python.old
import pytest
from quipu.engine.state_machine import Engine
~~~~~
~~~~~python.new
import pytest
from quipu.engine.state_machine import Engine
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_engine.py
~~~~~
~~~~~python.old
    # 1. Create initial state and corresponding node
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    initial_node = engine.writer.create_node(
        "plan", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", initial_hash, "Initial content"
    )
    engine.align()  # Load the new node into the engine's graph
~~~~~
~~~~~python.new
    # 1. Create initial state and corresponding node
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    initial_node = engine.writer.create_node(
        "plan", EMPTY_TREE_HASH, initial_hash, "Initial content"
    )
    engine.align()  # Load the new node into the engine's graph
~~~~~

#### Acts 3: 更新集成测试（SQLite Backend）

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
~~~~~
~~~~~python.old
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryReader
~~~~~
~~~~~python.new
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryReader
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
~~~~~
~~~~~python.old
        # 1. 在 Git 中创建两个节点
        (repo / "a.txt").touch()
        hash_a = git_db.get_tree_hash()
        git_writer.create_node("plan", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", hash_a, "Content A")
~~~~~
~~~~~python.new
        # 1. 在 Git 中创建两个节点
        (repo / "a.txt").touch()
        hash_a = git_db.get_tree_hash()
        git_writer.create_node("plan", EMPTY_TREE_HASH, hash_a, "Content A")
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
~~~~~
~~~~~python.old
        # 1. 在 Git 中创建节点
        (repo / "c.txt").touch()
        hash_c = git_db.get_tree_hash()
        node_c_git = git_writer.create_node(
            "plan", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", hash_c, "Cache Test Content"
        )
        commit_hash_c = node_c_git.commit_hash
~~~~~
~~~~~python.new
        # 1. 在 Git 中创建节点
        (repo / "c.txt").touch()
        hash_c = git_db.get_tree_hash()
        node_c_git = git_writer.create_node(
            "plan", EMPTY_TREE_HASH, hash_c, "Cache Test Content"
        )
        commit_hash_c = node_c_git.commit_hash
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
~~~~~
~~~~~python.old
    # --- Data population logic ---
    parent_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    commit_hashes = []
~~~~~
~~~~~python.new
    # --- Data population logic ---
    parent_hash = EMPTY_TREE_HASH
    commit_hashes = []
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_writer.py
~~~~~
~~~~~python.old
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryWriter
~~~~~
~~~~~python.new
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_writer.py
~~~~~
~~~~~python.old
    def test_dual_write_and_link(self, sqlite_setup):
        writer, db_manager, git_db, ws = sqlite_setup

        EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # --- Action 1: Create first node (Node A) ---
~~~~~
~~~~~python.new
    def test_dual_write_and_link(self, sqlite_setup):
        writer, db_manager, git_db, ws = sqlite_setup

        EMPTY_TREE = EMPTY_TREE_HASH

        # --- Action 1: Create first node (Node A) ---
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_writer_idempotency.py
~~~~~
~~~~~python.old
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryWriter
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryWriter
~~~~~
~~~~~python.new
import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryWriter
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/sqlite/test_writer_idempotency.py
~~~~~
~~~~~python.old
    # 2. Get initial state (Genesis)
    genesis_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    # 3. Create Node 1 (State A)
~~~~~
~~~~~python.new
    # 2. Get initial state (Genesis)
    genesis_tree = EMPTY_TREE_HASH

    # 3. Create Node 1 (State A)
~~~~~

### 下一步建议

我们已经完成了所有显著位置的硬编码清理。这是重构路线图中的最后一个大型物理操作。

建议现在执行 `pytest`。如果所有测试依然通过，请告知我，我将生成最终的 `[COMMIT]` 计划，标志着整个 **“Quipu 架构重构：从 Interfaces 到 Spec”** 宏观任务的圆满完成。
