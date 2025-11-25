# fix-test: Repair test suite failures from API implementation

## 用户需求
在实现了 `find_nodes` API 和 `quipu find` 命令后，测试套件出现了多处失败。失败的原因包括：对命令行输出格式的解析不健壮、测试装置 (fixture) 使用了无效的 Git 哈希导致底层命令失败，以及测试装置的依赖注入不正确。

## 评论
修复这些测试是确保新功能稳定可靠的关键步骤。本次修复将提高测试代码的健壮性，使其更能抵抗未来对输出格式的微小调整，并确保测试环境的正确性。

## 目标
1.  修复 `test_storage_integration.py` 中对 `quipu find` 命令输出的解析逻辑，使其能够正确处理带空格的时间戳和格式化填充。
2.  修复 `test_engine.py` 中的 `populated_engine` 测试装置，使其使用真实的文件变更和有效的 Git Tree 哈希来创建历史节点，避免底层 `git diff-tree` 命令失败。
3.  修复 `test_storage_integration.py` 中的 `populated_workspace` 测试装置，为其正确注入 `runner` 依赖，解决 `AttributeError`。

## 基本原理
1.  **健壮的输出解析**: `quipu find` 的输出行格式为 `[日期] [时间] [类型] [哈希] - [摘要]`。由于时间戳包含空格，简单的 `split()` 可能会导致索引错误。我们将更新测试代码，使用更可靠的索引 `[3]` 来定位哈希。
2.  **真实的测试数据**: 单元测试和集成测试应尽可能模拟真实世界的使用场景。`Engine` 的内部方法依赖于有效的 Git 对象。我们将修改测试装置，通过实际的文件系统操作来生成这些有效的 Git 对象 (Tree 哈希)，而不是使用伪造的字符串。
3.  **正确的依赖注入**: `pytest` 通过函数的参数签名来注入测试装置。一个测试装置如果需要使用另一个测试装置，必须在其参数列表中声明它。我们将修正 `populated_workspace` 的签名，使其正确接收 `runner` 实例。

## 标签
#comp/tests #scope/dx #fix

---

## Script

### Acts 1: 修复测试逻辑与装置

我们将一次性应用所有对测试文件的修复。

~~~~~act
write_file tests/test_engine.py
~~~~~

~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from quipu.core.state_machine import Engine
from quipu.core.git_db import GitDB
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter


@pytest.fixture
def engine_setup(tmp_path):
    """
    创建一个包含 Git 仓库和 Engine 实例的测试环境。
    默认使用新的 GitObject 存储后端。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)

    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有历史记录的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态 (适用于两种后端)。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    status = engine.align()
    
    assert status == "ORPHAN"
    assert engine.current_node is None

def test_capture_drift_git_object(engine_setup):
    """
    测试场景 (GitObject Backend)：当工作区处于 DIRTY 状态时，引擎应能成功捕获变化，
    创建一个新的 Capture 节点，并更新 Git 引用。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    
    # Manually create an initial commit to act as parent
    initial_commit = engine.git_db.commit_tree(initial_hash, parent_hashes=None, message="Initial")
    engine.git_db.update_ref("refs/quipu/history", initial_commit)
    
    # Create the first node using the writer to simulate a full flow
    engine.writer.create_node("plan", "_" * 40, initial_hash, "Initial content")
    initial_commit = engine.git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()

    # Re-align to load the node we just created
    engine.align()
    
    (repo_path / "main.py").write_text("version = 2", "utf-8")
    dirty_hash = engine.git_db.get_tree_hash()
    assert initial_hash != dirty_hash
    
    # --- The Action ---
    capture_node = engine.capture_drift(dirty_hash)
    
    # --- Assertions ---
    assert len(engine.history_graph) == 2, "历史图谱中应有两个节点"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == dirty_hash
    assert capture_node.node_type == "capture"
    assert capture_node.input_tree == initial_hash
    
    # Key Assertion: Verify the Git ref was updated by the writer
    latest_ref_commit = subprocess.check_output(
        ["git", "rev-parse", "refs/quipu/history"], cwd=repo_path
    ).decode().strip()
    assert latest_ref_commit != initial_commit, "Git 引用必须更新到新的锚点"
    
    # Verify the new commit has the correct parent
    parent_of_latest = subprocess.check_output(
        ["git", "rev-parse", f"{latest_ref_commit}^"], cwd=repo_path
    ).decode().strip()
    assert parent_of_latest == initial_commit

class TestEngineFindNodes:
    @pytest.fixture
    def populated_engine(self, engine_setup):
        import time
        engine, repo_path = engine_setup

        def add_commit(filename, content, message, node_type, parent_hash):
            """辅助函数：创建文件变更并生成一个新节点"""
            (repo_path / filename).write_text(content)
            time.sleep(0.01)  # 确保时间戳唯一
            new_hash = engine.git_db.get_tree_hash()
            if node_type == 'plan':
                engine.create_plan_node(parent_hash, new_hash, message)
            else: # capture
                # 对于 capture，message 是用户备注，不是 plan content
                engine.capture_drift(new_hash, message=message)
            return new_hash

        # 创世状态
        parent = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
        # Node 1 (Plan)
        parent = add_commit("f_a.txt", "content_a", "# feat: Add feature A", "plan", parent)
        # Node 2 (Capture)
        parent = add_commit("f_b.txt", "content_b", "Snapshot after feature A", "capture", parent)
        # Node 3 (Plan)
        parent = add_commit("f_c.txt", "content_c", "refactor: Cleanup code", "plan", parent)
        
        # 重新对齐以加载完整的图谱
        engine.align()
        return engine

    def test_find_by_type(self, populated_engine):
        plans = populated_engine.find_nodes(node_type="plan")
        captures = populated_engine.find_nodes(node_type="capture")
        
        assert len(plans) == 2
        assert all(p.node_type == "plan" for p in plans)
        
        assert len(captures) == 1
        assert captures[0].node_type == "capture"

    def test_find_by_summary_regex(self, populated_engine):
        feat_nodes = populated_engine.find_nodes(summary_regex="feat:")
        assert len(feat_nodes) == 1
        assert "Add feature A" in feat_nodes[0].summary
        
        snapshot_nodes = populated_engine.find_nodes(summary_regex="snapshot")
        assert len(snapshot_nodes) == 1
        assert "Snapshot after" in snapshot_nodes[0].summary

    def test_find_combined_filters(self, populated_engine):
        results = populated_engine.find_nodes(summary_regex="refactor", node_type="plan")
        assert len(results) == 1
        assert "Cleanup code" in results[0].summary
        
        empty_results = populated_engine.find_nodes(summary_regex="feat", node_type="capture")
        assert len(empty_results) == 0

    def test_find_limit(self, populated_engine):
        results = populated_engine.find_nodes(limit=1)
        assert len(results) == 1
        # 应该是最新的节点
        assert "Cleanup code" in results[0].summary

class TestPersistentIgnores:
    def test_sync_creates_file_if_not_exists(self, engine_setup):
        """测试：如果 exclude 文件不存在，应能根据默认配置创建它。"""
        engine, repo_path = engine_setup
        
        (repo_path / ".quipu").mkdir(exist_ok=True)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        assert exclude_file.exists()
        content = exclude_file.read_text("utf-8")
        
        assert "# --- Managed by Quipu ---" in content
        assert ".envs" in content

    def test_sync_appends_to_existing_file(self, engine_setup):
        """测试：如果 exclude 文件已存在，应追加 Quipu 块而不是覆盖。"""
        engine, repo_path = engine_setup
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(exist_ok=True)
        user_content = "# My personal ignores\n*.log\n"
        exclude_file.write_text(user_content)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        content = exclude_file.read_text("utf-8")
        assert user_content in content
        assert "# --- Managed by Quipu ---" in content
        assert "o.md" in content

    def test_sync_updates_existing_block(self, engine_setup):
        """测试：如果 Quipu 块已存在，应更新其内容。"""
        engine, repo_path = engine_setup
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(exist_ok=True)
        
        old_block = (
            "# --- Managed by Quipu ---\n"
            "old_rule/\n"
            "# --- End Managed by Quipu ---"
        )
        user_content = f"# My ignores\n{old_block}\n# More ignores"
        exclude_file.write_text(user_content)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        content = exclude_file.read_text("utf-8")
        assert "old_rule/" not in content
        assert ".vscode" in content
        assert "# My ignores" in content
        assert "# More ignores" in content

    def test_sync_uses_user_config(self, engine_setup):
        """测试：应优先使用 .quipu/config.yml 中的用户配置。"""
        import yaml
        engine, repo_path = engine_setup
        
        config_dir = repo_path / ".quipu"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.yml"
        
        user_ignores = {
            "sync": {
                "persistent_ignores": ["custom_dir/", "*.tmp"]
            }
        }
        config_file.write_text(yaml.dump(user_ignores), "utf-8")
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        content = exclude_file.read_text("utf-8")
        
        assert "custom_dir/" in content
        assert "*.tmp" in content
        assert ".envs" not in content
~~~~~

~~~~~act
write_file tests/test_storage_integration.py
~~~~~

~~~~~python
import pytest
import subprocess
from pathlib import Path
from typer.testing import CliRunner

from quipu.cli.main import app

# A simple plan that creates one file
PLAN_A = """
~~~act
write_file a.txt
~~~
~~~content
File A content
~~~
"""

# A simple plan that creates a different file
PLAN_B = """
~~~act
write_file b.txt
~~~
~~~content
File B content
~~~
"""

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    """Creates a temporary directory and initializes it as a Git repository."""
    ws = tmp_path / "ws"
    ws.mkdir()
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=ws, check=True)
    return ws

def git_rev_parse(ref: str, cwd: Path) -> str:
    """Helper to get the hash of a git ref."""
    result = subprocess.run(["git", "rev-parse", ref], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


class TestStorageSelection:
    """Tests the automatic detection and selection of storage backends."""

    def test_defaults_to_git_object_storage_on_new_project(self, runner, git_workspace):
        """
        SCENARIO: A user starts a new project.
        EXPECTATION: The system should use the new Git Object storage by default.
        """
        # Action: Run a plan in the new workspace
        result = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        
        assert result.exit_code == 0, result.stderr
        
        # Verification
        assert (git_workspace / "a.txt").exists()
        
        # 1. New ref should exist
        ref_hash = git_rev_parse("refs/quipu/history", git_workspace)
        assert len(ref_hash) == 40, "A git ref for quipu history should have been created."
        
        # 2. Old directory should NOT exist
        legacy_history_dir = git_workspace / ".quipu" / "history"
        assert not legacy_history_dir.exists(), "Legacy file system history should not be used."


    def test_continues_using_git_object_storage(self, runner, git_workspace):
        """
        SCENARIO: A user runs quipu in a project already using the new format.
        EXPECTATION: The system should continue using the Git Object storage.
        """
        # Setup: Run one command to establish the new format
        runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        hash_after_a = git_rev_parse("refs/quipu/history", git_workspace)
        assert hash_after_a
        
        # Action: Run a second command
        result = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_B)
        
        assert result.exit_code == 0, result.stderr
        
        # Verification
        # 1. The ref should be updated to a new commit
        hash_after_b = git_rev_parse("refs/quipu/history", git_workspace)
        assert hash_after_b != hash_after_a, "The history ref should point to a new commit."
        
        # 2. The parent of the new commit should be the old one
        parent_hash = git_rev_parse(f"{hash_after_b}^", git_workspace)
        assert parent_hash == hash_after_a, "The new commit should be parented to the previous one."

        # 3. No legacy files should be created
        assert not (git_workspace / ".quipu" / "history").exists()


class TestGitObjectWorkflow:
    """End-to-end tests for core commands using the Git Object backend."""

    def test_full_workflow_with_git_object_storage(self, runner, git_workspace):
        # 1. Run a plan to create state A
        res_run = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        assert res_run.exit_code == 0
        assert (git_workspace / "a.txt").exists()
        
        # 2. Manually add a file and use `save` to create state B
        (git_workspace / "b.txt").write_text("manual change")
        res_save = runner.invoke(app, ["save", "add b.txt", "-w", str(git_workspace)])
        assert res_save.exit_code == 0
        assert "快照已保存" in res_save.stderr
        
        # 3. Use `log` to check history
        res_log = runner.invoke(app, ["log", "-w", str(git_workspace)])
        assert res_log.exit_code == 0
        assert "add b.txt" in res_log.stderr  # Summary of the save message
        assert "write_file a.txt" in res_log.stderr # Summary of the plan
        
        # 4. Use `find` and `checkout` to go back to state A
        # --- REFACTOR START ---
        # Use the robust find_nodes API via CLI to get the target hash
        res_find = runner.invoke(app, ["find", "--summary", "write_file a.txt", "-w", str(git_workspace)])
        assert res_find.exit_code == 0
        
        # Parse the output to get the full hash
        found_line = res_find.stderr.strip().splitlines()[-1] # Get the last line of output
        parts = found_line.split()
        # Format: YYYY-MM-DD HH:MM:SS [TYPE] HASH - Summary
        # Index:    0          1         2     3
        output_tree_a = parts[3] 
        
        assert len(output_tree_a) == 40
        # --- REFACTOR END ---

        res_checkout = runner.invoke(app, ["checkout", output_tree_a[:8], "-f", "-w", str(git_workspace)])
        assert res_checkout.exit_code == 0, res_checkout.stderr
        
        # Verification of state A
        assert (git_workspace / "a.txt").exists()
        assert not (git_workspace / "b.txt").exists()

class TestFindCliCommand:

    @pytest.fixture
    def populated_workspace(self, git_workspace, runner): # Correctly inject runner
        # Run plan A
        runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        # Run save
        (git_workspace / "change.txt").write_text("manual")
        runner.invoke(app, ["save", "Snapshot 1", "-w", str(git_workspace)])
        return git_workspace

    def test_find_cli_by_type(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "--type", "plan", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[PLAN]" in result.stderr
        assert "[CAPTURE]" not in result.stderr
        assert "write_file a.txt" in result.stderr

    def test_find_cli_by_summary(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "-s", "snapshot", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[CAPTURE]" in result.stderr
        assert "Snapshot 1" in result.stderr
        assert "[PLAN]" not in result.stderr

    def test_find_cli_no_results(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "-s", "non-existent", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "未找到符合条件" in result.stderr
~~~~~
