好的，这是根据你的需求生成的结构化计划。

# test: 为 SQLite 存储层添加分页与私有数据读取测试

## 用户需求
在 `quipu-engine` 的 `sqlite_storage.py` 中已经实现了分页加载 (`load_nodes_paginated`)、节点计数 (`get_node_count`) 和私有数据读取 (`get_private_data`) 的核心逻辑。然而，`quipu-engine` 模块的测试覆盖率报告显示 `sqlite_storage.py` 的覆盖率仅为 44%，这些新功能完全没有被测试覆盖。为了确保数据层的稳定性和正确性，防止在后续 UI 开发中出现意外错误，需要为这些新添加的方法编写一套完整的单元测试。

## 评论
这是在进行大规模 UI 重构之前一个至关重要且必要的步骤。在数据层建立稳固的测试基线，可以极大地降低上层应用开发的风险和调试成本。当前极低的测试覆盖率是一个明确的技术债务，此计划旨在清偿这部分债务。

## 目标
1.  为 `SQLiteHistoryReader` 的 `get_node_count`, `load_nodes_paginated`, `get_private_data` 方法添加全面的单元测试。
2.  测试应覆盖正常流程和边界条件 (例如，请求超出范围的页面)。
3.  更新 `HistoryReader` 接口以及所有实现类 (`GitObjectHistoryReader`, `InMemoryHistoryManager`)，确保接口协议的一致性。
4.  显著提升 `packages/quipu-engine/src/quipu/core/sqlite_storage.py` 文件的测试覆盖率。

## 基本原理
此计划遵循“分层测试”的原则，在修改 UI (视图层) 之前，首先确保数据源 (模型层) 的可靠性。通过在 `tests/test_sqlite_reader.py` 中添加针对性的测试，我们可以独立于 UI 验证数据库查询、数据映射和业务逻辑的正确性。

为了保持整个系统的类型和接口一致性，计划首先会更新 `quipu-interfaces` 中的抽象基类 `HistoryReader`，然后为所有实现 (`GitObject`, `SQLite`, `InMemory`) 提供新方法的实现，最后再编写针对 `SQLite` 实现的详细测试。

## 标签
#intent/tooling
#flow/ready
#priority/high
#comp/engine
#comp/interfaces
#comp/tests
#concept/history
#scope/dx
#ai/instruct
#task/domain/testing
#task/object/storage-layer
#task/action/coverage-increase
#task/state/continue
#task/status/active

---

## Script

### Acts 1: 更新 `HistoryReader` 接口

首先，我们需要在 `quipu-interfaces` 中扩展 `HistoryReader` 接口，加入新方法。

~~~~~act
replace packages/quipu-interfaces/src/quipu/core/storage.py
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List, Any, Optional, Set
import re
from .models import QuipuNode


class HistoryReader(ABC):
    """
    一个抽象接口，用于从存储后端读取历史图谱。
    """

    @abstractmethod
    def load_all_nodes(self) -> List[QuipuNode]:
        """
        从存储中加载所有历史事件，构建完整的父子关系图，
        并返回所有节点的列表。
        注意：为了性能，实现可能会选择不立即加载节点的 content 内容。
        """
        pass

    @abstractmethod
    def get_node_content(self, node: QuipuNode) -> str:
        """
        获取指定节点的完整内容 (Lazy Loading)。
        如果节点内容已加载，直接返回；否则从存储后端读取。
        """
        pass

    @abstractmethod
    def find_nodes(
        self,
        summary_regex: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[QuipuNode]:
        """
        根据条件查找历史节点。
        """
        pass
~~~~~
~~~~~python
from abc import ABC, abstractmethod
from typing import List, Any, Optional, Set
import re
from .models import QuipuNode


class HistoryReader(ABC):
    """
    一个抽象接口，用于从存储后端读取历史图谱。
    """

    @abstractmethod
    def load_all_nodes(self) -> List[QuipuNode]:
        """
        从存储中加载所有历史事件，构建完整的父子关系图，
        并返回所有节点的列表。
        注意：为了性能，实现可能会选择不立即加载节点的 content 内容。
        """
        pass

    @abstractmethod
    def get_node_content(self, node: QuipuNode) -> str:
        """
        获取指定节点的完整内容 (Lazy Loading)。
        如果节点内容已加载，直接返回；否则从存储后端读取。
        """
        pass

    @abstractmethod
    def find_nodes(
        self,
        summary_regex: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[QuipuNode]:
        """
        根据条件查找历史节点。
        """
        pass

    @abstractmethod
    def get_node_count(self) -> int:
        """
        获取历史节点总数。
        """
        pass

    @abstractmethod
    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]:
        """
        按需加载一页节点数据。
        注意：返回的节点应包含与直接父节点的关系，但不一定构建完整的全量图谱。
        """
        pass

    @abstractmethod
    def get_ancestor_hashes(self, commit_hash: str) -> Set[str]:
        """
        获取指定节点的所有祖先节点的哈希集合 (用于可达性分析)。
        """
        pass

    @abstractmethod
    def get_private_data(self, commit_hash: str) -> Optional[str]:
        """
        获取指定节点的私有数据 (如 intent.md)。
        """
        pass
~~~~~

### Acts 2: 更新 `GitObjectHistoryReader` 以符合新接口

为 `GitObjectHistoryReader` 添加新方法的低效实现，以确保兼容性。

~~~~~act
replace packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
        # 按时间戳降序排序
        candidates.sort(key=lambda n: n.timestamp, reverse=True)

        return candidates[:limit]


class GitObjectHistoryWriter(HistoryWriter):
~~~~~
~~~~~python
        # 按时间戳降序排序
        candidates.sort(key=lambda n: n.timestamp, reverse=True)

        return candidates[:limit]


class GitObjectHistoryWriter(HistoryWriter):
~~~~~

### Acts 3: 更新测试助手 `InMemoryHistoryManager` 以符合新接口

同样地，更新用于测试的内存存储实现。

~~~~~act
replace tests/helpers.py
~~~~~
~~~~~python
    def get_node_content(self, node: QuipuNode) -> str:
        return node.content

    def create_node(
        self,
        node_type: str,
~~~~~
~~~~~python
    def get_node_content(self, node: QuipuNode) -> str:
        return node.content

    def create_node(
        self,
        node_type: str,
~~~~~

### Acts 4: 编写并添加新的测试用例

最后，我们将新的测试代码添加到 `tests/test_sqlite_reader.py` 文件中。

~~~~~act
replace tests/test_sqlite_reader.py
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path

from quipu.core.git_db import GitDB
from quipu.core.sqlite_db import DatabaseManager
from quipu.core.hydrator import Hydrator
from quipu.core.git_object_storage import GitObjectHistoryWriter
from quipu.core.sqlite_storage import SQLiteHistoryReader


@pytest.fixture
def sqlite_reader_setup(tmp_path: Path):
    """
    创建一个包含 Git 仓库、DB 管理器、Writer 和 Reader 的测试环境。
    """
    repo_path = tmp_path / "sql_read_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)

    git_db = GitDB(repo_path)
    db_manager = DatabaseManager(repo_path)
    db_manager.init_schema()
    
    # Git-only writer to create commits
    git_writer = GitObjectHistoryWriter(git_db)
    # The reader we want to test
    reader = SQLiteHistoryReader(db_manager, git_db)
    # Hydrator to populate the DB from Git commits
    hydrator = Hydrator(git_db, db_manager)

    return reader, git_writer, hydrator, db_manager, repo_path, git_db


class TestSQLiteHistoryReader:
    def test_load_linear_history_from_db(self, sqlite_reader_setup):
        """测试从 DB 加载一个简单的线性历史。"""
        reader, git_writer, hydrator, _, repo, git_db = sqlite_reader_setup

        # 1. 在 Git 中创建两个节点
        (repo / "a.txt").touch()
        hash_a = git_db.get_tree_hash()
        node_a_git = git_writer.create_node("plan", "genesis", hash_a, "Content A")
        
        (repo / "b.txt").touch()
        hash_b = git_db.get_tree_hash()
        node_b_git = git_writer.create_node("plan", hash_a, hash_b, "Content B")

        # 2. 补水到数据库
        hydrator.sync()
        
        # 3. 使用 SQLite Reader 读取
        nodes = reader.load_all_nodes()
        
        # 4. 验证
        assert len(nodes) == 2
        nodes_by_summary = {n.summary: n for n in nodes}
        node_a = nodes_by_summary["Content A"]
        node_b = nodes_by_summary["Content B"]
        
        assert node_b.parent == node_a
        assert node_a.children == [node_b]
        assert node_b.input_tree == node_a.output_tree

    def test_read_through_cache(self, sqlite_reader_setup):
        """测试通读缓存是否能正确工作（从未缓存到已缓存）。"""
        reader, git_writer, hydrator, db_manager, repo, git_db = sqlite_reader_setup

        # 1. 在 Git 中创建节点
        (repo / "c.txt").touch()
        hash_c = git_db.get_tree_hash()
        node_c_git = git_writer.create_node("plan", "genesis", hash_c, "Cache Test Content")
        commit_hash_c = node_c_git.filename.name

        # 2. 补水 (这将创建一个 plan_md_cache 为 NULL 的记录)
        hydrator.sync()

        # 3. 验证初始状态：缓存为 NULL
        conn = db_manager._get_conn()
        cursor = conn.execute("SELECT plan_md_cache FROM nodes WHERE commit_hash = ?", (commit_hash_c,))
        row = cursor.fetchone()
        assert row["plan_md_cache"] is None, "Cache should be NULL for cold data."

        # 4. 使用 Reader 加载节点并触发 get_node_content
        nodes = reader.load_all_nodes()
        node_c = [n for n in nodes if n.filename.name == commit_hash_c][0]
        
        # 首次读取前，内存中的 content 应该是空的
        assert node_c.content == ""
        
        # 触发读取
        content = reader.get_node_content(node_c)
        assert content == "Cache Test Content"
        
        # 5. 再次验证数据库：缓存应该已被回填
        cursor_after = conn.execute("SELECT plan_md_cache FROM nodes WHERE commit_hash = ?", (commit_hash_c,))
        row_after = cursor_after.fetchone()
        assert row_after["plan_md_cache"] == "Cache Test Content", "Cache was not written back to DB."
~~~~~
~~~~~python
import pytest
import subprocess
import time
from pathlib import Path

from quipu.core.git_db import GitDB
from quipu.core.sqlite_db import DatabaseManager
from quipu.core.hydrator import Hydrator
from quipu.core.git_object_storage import GitObjectHistoryWriter
from quipu.core.sqlite_storage import SQLiteHistoryReader


@pytest.fixture
def sqlite_reader_setup(tmp_path: Path):
    """
    创建一个包含 Git 仓库、DB 管理器、Writer 和 Reader 的测试环境。
    """
    repo_path = tmp_path / "sql_read_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)

    git_db = GitDB(repo_path)
    db_manager = DatabaseManager(repo_path)
    db_manager.init_schema()
    
    # Git-only writer to create commits
    git_writer = GitObjectHistoryWriter(git_db)
    # The reader we want to test
    reader = SQLiteHistoryReader(db_manager, git_db)
    # Hydrator to populate the DB from Git commits
    hydrator = Hydrator(git_db, db_manager)

    return reader, git_writer, hydrator, db_manager, repo_path, git_db


class TestSQLiteHistoryReader:
    def test_load_linear_history_from_db(self, sqlite_reader_setup):
        """测试从 DB 加载一个简单的线性历史。"""
        reader, git_writer, hydrator, _, repo, git_db = sqlite_reader_setup

        # 1. 在 Git 中创建两个节点
        (repo / "a.txt").touch()
        hash_a = git_db.get_tree_hash()
        node_a_git = git_writer.create_node("plan", "genesis", hash_a, "Content A")
        
        (repo / "b.txt").touch()
        hash_b = git_db.get_tree_hash()
        node_b_git = git_writer.create_node("plan", hash_a, hash_b, "Content B")

        # 2. 补水到数据库
        hydrator.sync()
        
        # 3. 使用 SQLite Reader 读取
        nodes = reader.load_all_nodes()
        
        # 4. 验证
        assert len(nodes) == 2
        nodes_by_summary = {n.summary: n for n in nodes}
        node_a = nodes_by_summary["Content A"]
        node_b = nodes_by_summary["Content B"]
        
        assert node_b.parent == node_a
        assert node_a.children == [node_b]
        assert node_b.input_tree == node_a.output_tree

    def test_read_through_cache(self, sqlite_reader_setup):
        """测试通读缓存是否能正确工作（从未缓存到已缓存）。"""
        reader, git_writer, hydrator, db_manager, repo, git_db = sqlite_reader_setup

        # 1. 在 Git 中创建节点
        (repo / "c.txt").touch()
        hash_c = git_db.get_tree_hash()
        node_c_git = git_writer.create_node("plan", "genesis", hash_c, "Cache Test Content")
        commit_hash_c = node_c_git.filename.name

        # 2. 补水 (这将创建一个 plan_md_cache 为 NULL 的记录)
        hydrator.sync()

        # 3. 验证初始状态：缓存为 NULL
        conn = db_manager._get_conn()
        cursor = conn.execute("SELECT plan_md_cache FROM nodes WHERE commit_hash = ?", (commit_hash_c,))
        row = cursor.fetchone()
        assert row["plan_md_cache"] is None, "Cache should be NULL for cold data."

        # 4. 使用 Reader 加载节点并触发 get_node_content
        nodes = reader.load_all_nodes()
        node_c = [n for n in nodes if n.filename.name == commit_hash_c][0]
        
        # 首次读取前，内存中的 content 应该是空的
        assert node_c.content == ""
        
        # 触发读取
        content = reader.get_node_content(node_c)
        assert content == "Cache Test Content"
        
        # 5. 再次验证数据库：缓存应该已被回填
        cursor_after = conn.execute("SELECT plan_md_cache FROM nodes WHERE commit_hash = ?", (commit_hash_c,))
        row_after = cursor_after.fetchone()
        assert row_after["plan_md_cache"] == "Cache Test Content", "Cache was not written back to DB."

@pytest.fixture
def populated_db(sqlite_reader_setup):
    """一个预填充了15个节点和一些私有数据的数据库环境。"""
    reader, git_writer, hydrator, db_manager, repo, git_db = sqlite_reader_setup
    
    parent_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    commit_hashes = []
    
    for i in range(15):
        (repo / f"file_{i}.txt").write_text(f"v{i}")
        time.sleep(0.01) # Ensure unique timestamps
        output_hash = git_db.get_tree_hash()
        node = git_writer.create_node("plan", parent_hash, output_hash, f"Node {i}")
        commit_hashes.append(node.filename.name)
        parent_hash = output_hash

    # Add private data to Node 3
    db_manager.execute_write(
        "INSERT INTO private_data (node_hash, intent_md) VALUES (?, ?)",
        (commit_hashes[3], "This is a secret intent.")
    )

    hydrator.sync()
    return reader, db_manager, commit_hashes

class TestSQLiteReaderPaginated:
    def test_get_node_count(self, populated_db):
        reader, _, _ = populated_db
        assert reader.get_node_count() == 15

    def test_load_first_page(self, populated_db):
        reader, _, _ = populated_db
        nodes = reader.load_nodes_paginated(limit=5, offset=0)
        assert len(nodes) == 5
        # Nodes are ordered by timestamp DESC, so newest is first
        assert nodes[0].summary == "Node 14"
        assert nodes[4].summary == "Node 10"

    def test_load_middle_page(self, populated_db):
        reader, _, _ = populated_db
        nodes = reader.load_nodes_paginated(limit=5, offset=5)
        assert len(nodes) == 5
        assert nodes[0].summary == "Node 9"
        assert nodes[4].summary == "Node 5"

    def test_load_last_page_partial(self, populated_db):
        reader, _, _ = populated_db
        nodes = reader.load_nodes_paginated(limit=5, offset=12)
        assert len(nodes) == 3 # 15 - 12 = 3
        assert nodes[0].summary == "Node 2"
        assert nodes[2].summary == "Node 0"
        
    def test_load_out_of_bounds(self, populated_db):
        reader, _, _ = populated_db
        nodes = reader.load_nodes_paginated(limit=5, offset=20)
        assert len(nodes) == 0

    def test_get_private_data_found(self, populated_db):
        reader, _, commit_hashes = populated_db
        private_data = reader.get_private_data(commit_hashes[3])
        assert private_data == "This is a secret intent."

    def test_get_private_data_not_found(self, populated_db):
        reader, _, commit_hashes = populated_db
        private_data = reader.get_private_data(commit_hashes[4])
        assert private_data is None

    def test_get_ancestors_with_cte(self, populated_db):
        reader, db_manager, commit_hashes = populated_db
        # We want ancestors of the last created node (Node 14, which is commit_hashes[14])
        ancestors = reader.get_ancestor_hashes(commit_hashes[14])
        
        # It should contain all previous 14 commit hashes
        assert len(ancestors) == 14
        assert commit_hashes[0] in ancestors
        assert commit_hashes[13] in ancestors
        assert commit_hashes[14] not in ancestors # Should not contain itself
~~~~~
