# refactor: 清理旧版文件系统存储与迁移代码

## 用户需求
在完成了基于 Git 对象的新存储架构 (`QDPS v1.0`) 并确认其稳定性后，需要清理项目中遗留的旧版文件系统存储 (`.quipu/history/*.md`) 相关代码，以及用于数据迁移的工具。这可以简化代码库，降低维护成本，并使新架构成为系统中唯一的存储实现。

## 评论
这是一个必要的重构步骤，标志着存储层升级工作的正式完成。通过移除废弃代码，可以使项目结构更清晰，并减少新开发者的认知负担。

## 目标
1.  从代码库中完全移除 `FileSystemHistoryReader` 和 `FileSystemHistoryWriter`。
2.  移除用于从文件系统格式迁移到 Git 对象格式的 `HistoryMigrator` 模块和 `quipu history migrate` 命令。
3.  简化 `Engine` 的创建工厂 (`create_engine`)，使其不再需要检测存储格式，而是默认且唯一地使用 `GitObjectHistory...` 实现。
4.  清理所有相关的、现已废弃的测试用例。

## 基本原理
本次清理遵循“单一职责原则”和“保持代码简洁” (KISS) 的原则。随着新存储架构的稳定，旧的实现和一次性的迁移工具已完成了它们的历史使命，继续保留它们会成为技术债。移除这些代码可以降低项目的复杂性，并确保所有未来的开发都基于统一的、现代化的存储层进行。

## 标签
#comp/engine #comp/cli #comp/tests #scope/core #refactor

---

## Script

### Acts 1: 移除核心模块中的废弃代码

首先，我们将删除与旧文件系统存储和迁移功能相关的核心逻辑文件。

~~~~~act
delete_file
~~~~~
~~~~~
packages/quipu-engine/src/quipu/core/file_system_storage.py
~~~~~

~~~~~act
delete_file
~~~~~
~~~~~
packages/quipu-engine/src/quipu/core/history.py
~~~~~

~~~~~act
delete_file
~~~~~
~~~~~
packages/quipu-engine/src/quipu/core/migration.py
~~~~~

### Acts 2: 简化 Engine 创建工厂

现在，`create_engine` 函数不再需要检测不同的存储后端。我们将简化它，使其只创建 `GitObject` 存储实例。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/factory.py
~~~~~
~~~~~python
    # 2. 检测存储格式并选择策略
    # 优先检测新格式 (Git refs)
    if git_db.has_quipu_ref():
        logger.debug("Detected Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
    # 回退检测旧格式 (FS directory)
    elif (real_root / ".quipu" / "history").exists():
        logger.debug("Detected File System storage format (legacy).")
        history_dir = real_root / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
    # 默认在新项目中使用新格式
    else:
        logger.debug("No existing history found. Defaulting to Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
~~~~~
~~~~~python
    # 2. 默认使用 Git Object 存储
    logger.debug("Defaulting to Git Object storage format.")
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/factory.py
~~~~~
~~~~~python
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
~~~~~
~~~~~python

~~~~~

### Acts 3: 移除 CLI 中的迁移命令

由于迁移逻辑已被删除，我们需要从 `main.py` 中移除 `history migrate` 命令及其相关代码。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
from quipu.core.migration import HistoryMigrator
~~~~~
~~~~~python

~~~~~

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
# --- History Management Commands ---
history_app = typer.Typer(help="管理 Axon 历史记录的高级命令。")
app.add_typer(history_app, name="history")

@history_app.command("migrate")
def migrate_history(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w",
            help="操作执行的根目录（工作区）",
            file_okay=False,
            dir_okay=True,
            resolve_path=True
        )
    ] = DEFAULT_WORK_DIR,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="仅模拟迁移过程，不写入 Git。")
    ] = False,
):
    """
    将旧版文件系统历史记录迁移到 Git 对象存储格式 (QDPS v1.0)。
    """
    setup_logging()
    root = resolve_root(work_dir)
    
    try:
        git_db = GitDB(root)
        migrator = HistoryMigrator(root, git_db)
        
        count = migrator.migrate(dry_run=dry_run)
        
        if count > 0:
            if dry_run:
                typer.secho(f"\n✅ [Dry Run] 模拟完成，将迁移 {count} 个节点。", fg=typer.colors.GREEN)
            else:
                typer.secho(f"\n✅ 迁移成功！已转换 {count} 个历史节点。", fg=typer.colors.GREEN)
                typer.secho("💡 你现在可以使用 'quipu log' 查看新格式的历史记录。", fg=typer.colors.BLUE)
                typer.secho("⚠️  建议保留 .quipu/history 目录一段时间作为备份，确认无误后再删除。", fg=typer.colors.YELLOW)
        else:
            typer.secho("🤔 未发现需要迁移的节点，或迁移未执行。", fg=typer.colors.YELLOW)
            
    except Exception as e:
        typer.secho(f"❌ 迁移失败: {e}", fg=typer.colors.RED)
        logger.exception(e)
        ctx.exit(1)
~~~~~
~~~~~python

~~~~~

### Acts 4: 清理废弃的测试文件

最后，删除所有与旧存储格式和迁移功能相关的测试文件。

~~~~~act
delete_file
~~~~~
~~~~~
tests/test_graph_loader.py
~~~~~

~~~~~act
delete_file
~~~~~
~~~~~
tests/test_migration.py
~~~~~

### Acts 5: 更新并清理其余测试用例

部分测试用例依赖于旧的存储实现，需要更新它们以适应新的单一存储架构。

~~~~~act
replace
~~~~~
~~~~~path
tests/test_engine.py
~~~~~
~~~~~python
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
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

@pytest.fixture
def fs_engine_setup(tmp_path):
    """
    (旧版) 创建一个使用 FileSystem 存储后端的 Engine 实例。
    """
    repo_path = tmp_path / "fs_test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    history_dir = repo_path / ".quipu" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    
    reader = FileSystemHistoryReader(history_dir)
    writer = FileSystemHistoryWriter(history_dir)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path


def test_align_clean_state_fs(fs_engine_setup):
    """
    测试场景 (FS Backend)：当工作区状态与最新的历史节点完全匹配时，
    引擎应能正确识别为 "CLEAN" 状态。
    """
    engine, repo_path = fs_engine_setup
    
    (repo_path / "main.py").write_text("print('hello')", "utf-8")
    clean_hash = engine.git_db.get_tree_hash()
    
    # 使用 writer 创建节点以模拟真实流程
    node = engine.writer.create_node("plan", "_" * 40, clean_hash, "# A Plan")

    status = engine.align()
    
    assert status == "CLEAN"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == clean_hash
    assert engine.current_node.filename == node.filename

def test_align_dirty_state_fs(fs_engine_setup):
    """
    测试场景 (FS Backend)：当工作区被修改，与任何历史节点都不匹配时，
    引擎应能正确识别为 "DIRTY" 状态。
    """
    engine, repo_path = fs_engine_setup
    
    past_hash = "a" * 40
    engine.writer.create_node("plan", "_" * 40, past_hash, "Past plan")
    
    (repo_path / "main.py").write_text("print('dirty state')", "utf-8")
    
    status = engine.align()
    
    assert status == "DIRTY"
    assert engine.current_node is None
~~~~~
~~~~~python
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
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
tests/test_head_and_root.py
~~~~~
~~~~~python
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestHeadTracking:
    @pytest.fixture
    def engine_with_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        # Config git user
        subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=repo, check=True)
        
        history_dir = repo / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
        return Engine(repo, reader=reader, writer=writer)
~~~~~
~~~~~python
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter

class TestHeadTracking:
    @pytest.fixture
    def engine_with_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        # Config git user
        subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=repo, check=True)
        
        from quipu.core.git_db import GitDB
        git_db = GitDB(repo)
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
        return Engine(repo, reader=reader, writer=writer)
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
tests/test_idempotent_node.py
~~~~~
~~~~~python
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestIdempotentNode:
    
    def test_idempotent_plan_creation(self, tmp_path: Path):
        """验证无文件变更的操作也能生成历史节点"""
        # 1. 初始化环境
        workspace = tmp_path / "ws"
        workspace.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        
        # 2. 先执行一个会产生变更的操作 (State A)
        plan_1 = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nA\n~~~"
        run_quipu(plan_1, workspace, yolo=True)
        
        history_dir = workspace / ".quipu" / "history"
        
        # 使用正确的 Engine 设置来验证
        from quipu.cli.factory import create_engine
        engine1 = create_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
        assert len(nodes1) >= 1
~~~~~
~~~~~python
from quipu.cli.controller import run_quipu

class TestIdempotentNode:
    
    def test_idempotent_plan_creation(self, tmp_path: Path):
        """验证无文件变更的操作也能生成历史节点"""
        # 1. 初始化环境
        workspace = tmp_path / "ws"
        workspace.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        
        # 2. 先执行一个会产生变更的操作 (State A)
        plan_1 = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nA\n~~~"
        run_quipu(plan_1, workspace, yolo=True)
        
        # 使用正确的 Engine 设置来验证
        from quipu.cli.factory import create_engine
        engine1 = create_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
        assert len(nodes1) >= 1
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
tests/test_storage_integration.py
~~~~~
~~~~~python
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

~~~~~
~~~~~python
~~~~~
