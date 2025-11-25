# test: Add integration tests for storage backend selection

## 用户需求
在完成了存储后端的动态选择逻辑后，我需要创建一套集成测试来验证该机制的正确性。这些测试应覆盖所有关键场景，确保系统能够正确地为新项目、旧项目和已使用新格式的项目选择合适的存储策略。

## 评论
这是确保重构后系统稳定性的关键一步。通过编写端到端的集成测试，我们可以模拟真实的用户场景，验证从 CLI 命令、存储格式检测、策略选择到最终数据持久化的整个流程是否按预期工作。这不仅能捕捉当前可能存在的缺陷，也为未来的重构提供了安全保障。

## 目标
1.  创建一个新的测试文件 `tests/test_storage_integration.py`。
2.  编写测试用例，验证在一个全新的项目中，系统默认使用 `GitObject` 存储后端。
3.  编写测试用例，验证在一个包含旧格式历史记录 (`.quipu/history/`) 的项目中，系统能回退并继续使用 `FileSystem` 存储后端。
4.  编写测试用例，验证在一个已使用新格式 (`refs/quipu/history`) 的项目中，系统能继续使用 `GitObject` 存储后端。
5.  编写一个完整的端到端工作流测试，模拟 `run`, `save`, `log`, `checkout` 等命令在新的 `GitObject` 存储后端上的协同工作情况。

## 基本原理
我们将使用 `typer.testing.CliRunner` 来调用 `quipu` 的各个子命令，模拟用户的真实操作。通过 `pytest` 的 `fixture`，我们将为每个测试场景动态创建不同状态的 Git 仓库（例如，空的、包含旧历史目录的、包含新历史引用的）。

测试的断言将通过以下方式进行：
*   检查文件系统的状态（例如，`hello.txt` 是否被创建）。
*   检查 `.quipu/history/` 目录中 `.md` 文件的存在与否。
*   使用 `subprocess` 调用 `git` 命令，检查 `refs/quipu/history` 引用是否存在及其指向的 Commit Hash 是否符合预期。
*   捕获并验证 CLI 命令的输出（`stdout` 和 `stderr`）是否正确。

通过这些多维度的验证，我们可以确保新的存储集成方案在各种边界条件下都能稳健运行。

## 标签
#comp/cli #comp/engine #concept/history #scope/tests

---

## Script

### Acts 1: 创建新的集成测试文件

我们将创建一个专门用于测试存储集成逻辑的新文件 `tests/test_storage_integration.py`。

~~~~~act
write_file
~~~~~
~~~~~path
tests/test_storage_integration.py
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

    def test_uses_filesystem_storage_on_legacy_project(self, runner, git_workspace):
        """
        SCENARIO: A user runs quipu in a project with existing legacy history.
        EXPECTATION: The system should detect the old format and continue using it.
        """
        # Setup: Create a legacy history directory
        legacy_history_dir = git_workspace / ".quipu" / "history"
        legacy_history_dir.mkdir(parents=True)
        (legacy_history_dir / "dummy_history.md").touch()
        
        num_files_before = len(list(legacy_history_dir.glob("*.md")))

        # Action: Run a plan
        result = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        
        assert result.exit_code == 0, result.stderr

        # Verification
        # 1. A new file should be added to the legacy directory
        num_files_after = len(list(legacy_history_dir.glob("*.md")))
        assert num_files_after == num_files_before + 1, "A new node should be created in the filesystem directory."

        # 2. The new ref format should NOT be created
        ref_hash = git_rev_parse("refs/quipu/history", git_workspace)
        assert ref_hash == "", "Git object ref should not be created for a legacy project."

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
        hash_a = git_rev_parse("refs/quipu/history", git_workspace)

        # 2. Manually add a file and use `save` to create state B
        (git_workspace / "b.txt").write_text("manual change")
        res_save = runner.invoke(app, ["save", "add b.txt", "-w", str(git_workspace)])
        assert res_save.exit_code == 0
        assert "快照已保存" in res_save.stderr
        hash_b = git_rev_parse("refs/quipu/history", git_workspace)
        assert hash_b != hash_a
        
        # 3. Use `log` to check history
        res_log = runner.invoke(app, ["log", "-w", str(git_workspace)])
        assert res_log.exit_code == 0
        assert "add b.txt" in res_log.stderr  # Summary of the save message
        assert "File A content" in res_log.stderr # Summary of the plan
        
        # 4. Use `checkout` to go back to state A
        # The output tree hash of state A needs to be found from the log
        # For simplicity, we can parse the log output or re-run the `git log` command
        # that the reader uses. Let's find the commit for state A.
        commit_log_a = subprocess.run(
            ["git", "log", "--grep=File A content", "--format=%H", "refs/quipu/history"],
            cwd=git_workspace, capture_output=True, text=True
        ).stdout.strip()
        
        output_tree_a_str = subprocess.run(
            ["git", "show", commit_log_a], cwd=git_workspace, capture_output=True, text=True
        ).stdout
        import re
        match = re.search(r"X-Quipu-Output-Tree:\s*([0-9a-f]{40})", output_tree_a_str)
        assert match
        output_tree_a = match.group(1)

        res_checkout = runner.invoke(app, ["checkout", output_tree_a[:8], "-f", "-w", str(git_workspace)])
        assert res_checkout.exit_code == 0
        
        # Verification of state A
        assert (git_workspace / "a.txt").exists()
        assert not (git_workspace / "b.txt").exists()

~~~~~