# fix: 修复 SQLite 写入器集成测试中的逻辑错误

## 用户需求
在执行“第二步：SQLite 存储后端实现”后，`pytest` 中出现了一个 `AssertionError`，需要修复。

## 评论
经过分析，失败的测试 (`test_dual_write_on_run`) 包含了一个逻辑缺陷。它在两次 `quipu run` 调用之间手动修改了工作区文件，这会触发系统的“状态漂移捕捉” (`capture_drift`) 机制，从而在预期的两个 Plan 节点之间自动插入一个 Capture 节点。测试的断言没有考虑到这个中间节点，因此失败了。这是一个很好的例子，说明了测试需要精确地模拟预期的工作流，以避免系统特性（如自动快照）的干扰。

## 目标
修复 `tests/test_sqlite_writer.py` 中的测试用例，使其能够正确、稳定地验证以下行为：
1.  在 SQLite 模式下，`quipu run` 能够成功地将节点数据写入 Git Commit。
2.  同时，能够将节点的元数据和正确的父子关系（`edge`）写入 SQLite 数据库。

## 基本原理
修复方案是重写该测试用例，使其更直接地反映核心业务流程，避免触发边缘情况。
1.  **移除手动文件操作**：不再使用 `(path).touch()` 来制造“脏”工作区。
2.  **使用连续的 Plan**: 创建两个独立的、会实际改变文件系统的 Plan (`PLAN_A` 和 `PLAN_B`)。
3.  **顺序执行**: 连续执行这两个 Plan。由于每次执行后工作区都是“干净”的（与上一个历史节点一致），因此不会触发 `capture_drift`。
4.  **精确断言**: 这样，第二个 Plan 节点会直接以第一个 Plan 节点为父节点。测试现在可以简单而精确地断言 `edges` 表中存在从第二个节点的 commit_hash 指向第一个节点的 commit_hash 的记录。
5.  **健壮性提升**: 同时，将测试中获取最新 commit hash 的方式从 `git log` 改为更精确的 `git rev-parse refs/quipu/history`，确保我们总是拿到 Quipu 历史记录的真正头部。

这个修改后的测试用例不仅修复了错误，而且更清晰地表达了其测试意图。

## 标签
#intent/fix #flow/ready #priority/critical
#comp/engine #comp/tests #concept/state #concept/history
#ai/delegate
#task/domain/storage #task/object/sqlite-backend #task/action/integration
#task/state/continue #task/status/active

---

## Script

### Acts 1: 修复测试文件

我们将用一个更健壮、逻辑更清晰的版本替换掉 `TestSQLiteWriterIntegration` 类。

~~~~~act
replace tests/test_sqlite_writer.py
~~~~~
~~~~~python
PLAN_A = """
```act
write_file a.txt
```
```content
File A content
```
"""

@pytest.fixture
def sqlite_workspace(tmp_path: Path) -> Path:
    """创建一个配置为使用 SQLite 后端的 Git 工作区。"""
    ws = tmp_path / "ws_sqlite"
    ws.mkdir()
    
    # Init Git
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=ws, check=True)

    # Init Quipu config for SQLite
    quipu_dir = ws / ".quipu"
    quipu_dir.mkdir()
    (quipu_dir / "config.yml").write_text("storage:\n  type: sqlite\n")
    
    return ws

class TestSQLiteWriterIntegration:
    def test_dual_write_on_run(self, sqlite_workspace):
        """
        验证 `quipu run` 在 SQLite 模式下是否能正确地双写到 Git 和 DB。
        """
        # --- Action ---
        result = run_quipu(PLAN_A, work_dir=sqlite_workspace, yolo=True)
        assert result.success, f"run_quipu failed: {result.message}"

        # --- Verification ---
        
        # 1. Verify Git Commit was created
        git_log = subprocess.check_output(
            ["git", "log", "--all", "--format=%H"], cwd=sqlite_workspace, text=True
        ).strip()
        assert len(git_log) > 0, "Git log should not be empty"
        commit_hash = git_log.splitlines()[0]

        # 2. Verify SQLite DB was created and populated
        db_path = sqlite_workspace / ".quipu" / "history.sqlite"
        assert db_path.exists()

        db = DatabaseManager(sqlite_workspace)
        conn = db._get_conn()
        
        # Check nodes table
        cursor = conn.execute("SELECT * FROM nodes WHERE commit_hash = ?", (commit_hash,))
        node_row = cursor.fetchone()
        assert node_row is not None
        assert node_row["summary"] == "Write: a.txt"
        assert node_row["node_type"] == "plan"
        assert node_row["plan_md_cache"] is not None # Should be hot-cached

        # Check edges table (for the second commit)
        (sqlite_workspace / "b.txt").touch()
        run_quipu("```act\nend\n```", work_dir=sqlite_workspace, yolo=True)
        
        git_log_2 = subprocess.check_output(
            ["git", "log", "--all", "--format=%H"], cwd=sqlite_workspace, text=True
        ).strip()
        commit_hash_2 = git_log_2.splitlines()[0]
        
        cursor_edge = conn.execute("SELECT * FROM edges WHERE child_hash = ?", (commit_hash_2,))
        edge_row = cursor_edge.fetchone()
        assert edge_row is not None
        assert edge_row["parent_hash"] == commit_hash
        
        db.close()
~~~~~
~~~~~python
PLAN_A = """
```act
write_file a.txt
```
```content
File A content
```
"""

PLAN_B = """
```act
write_file b.txt
```
```content
File B content
```
"""


@pytest.fixture
def sqlite_workspace(tmp_path: Path) -> Path:
    """创建一个配置为使用 SQLite 后端的 Git 工作区。"""
    ws = tmp_path / "ws_sqlite"
    ws.mkdir()

    # Init Git
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=ws, check=True)

    # Init Quipu config for SQLite
    quipu_dir = ws / ".quipu"
    quipu_dir.mkdir()
    (quipu_dir / "config.yml").write_text("storage:\n  type: sqlite\n")

    return ws


class TestSQLiteWriterIntegration:
    def test_dual_write_on_run_and_link(self, sqlite_workspace):
        """
        验证 `quipu run` 在 SQLite 模式下是否能正确地双写到 Git 和 DB，并建立父子关系。
        """
        # --- Action 1: Create first node ---
        result_a = run_quipu(PLAN_A, work_dir=sqlite_workspace, yolo=True)
        assert result_a.success, f"run_quipu failed on Plan A: {result_a.message}"

        # Get its commit hash using the stable ref
        commit_hash_a = subprocess.check_output(
            ["git", "rev-parse", "refs/quipu/history"], cwd=sqlite_workspace, text=True
        ).strip()
        assert len(commit_hash_a) == 40

        # --- Action 2: Create second node, which should be a child of the first ---
        result_b = run_quipu(PLAN_B, work_dir=sqlite_workspace, yolo=True)
        assert result_b.success, f"run_quipu failed on Plan B: {result_b.message}"

        # Get the new commit hash from the updated ref
        commit_hash_b = subprocess.check_output(
            ["git", "rev-parse", "refs/quipu/history"], cwd=sqlite_workspace, text=True
        ).strip()
        assert len(commit_hash_b) == 40
        assert commit_hash_a != commit_hash_b, "History ref was not updated after second run"

        # --- Verification ---
        db_path = sqlite_workspace / ".quipu" / "history.sqlite"
        assert db_path.exists()
        db = DatabaseManager(sqlite_workspace)
        conn = db._get_conn()

        # 1. Verify node B exists
        cursor_node = conn.execute("SELECT * FROM nodes WHERE commit_hash = ?", (commit_hash_b,))
        node_row = cursor_node.fetchone()
        assert node_row is not None
        assert node_row["summary"] == "Write: b.txt"
        assert node_row["plan_md_cache"] is not None  # Should be hot-cached

        # 2. Verify the edge exists and points to node A
        cursor_edge = conn.execute("SELECT * FROM edges WHERE child_hash = ?", (commit_hash_b,))
        edge_row = cursor_edge.fetchone()
        assert edge_row is not None, "Edge for the second node was not created in the database."
        assert edge_row["parent_hash"] == commit_hash_a, "The parent hash in the edge is incorrect."

        db.close()
~~~~~
