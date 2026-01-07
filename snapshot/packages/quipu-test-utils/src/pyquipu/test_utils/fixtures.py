import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from pyquipu.engine.git_db import GitDB
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine
from pyquipu.test_utils.helpers import run_git_command

# --- Global & Core Fixtures ---

@pytest.fixture
def runner() -> CliRunner:
    """提供一个可复用的 CliRunner 实例。"""
    return CliRunner()

@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    """
    提供一个已初始化 Git 的干净工作区路径。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)
    return repo_path

@pytest.fixture
def engine_instance(git_workspace: Path) -> Engine:
    """
    提供一个绑定到 git_workspace 的、功能完备的 Engine 实例。
    """
    git_db = GitDB(git_workspace)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(root_dir=git_workspace, db=git_db, reader=reader, writer=writer)
    return engine

# --- Application Layer Mocks ---

@pytest.fixture
def mock_engine():
    """
    提供一个模拟的 Engine 实例。
    用于测试 Application 层在不触及真实 Git/文件系统的情况下的编排逻辑。
    """
    engine = MagicMock(spec=Engine)
    # 设置基础属性以防止简单的 AttributeError
    engine.root_dir = Path("/mock/root")
    # 显式初始化 git_db
    engine.git_db = MagicMock()
    # 初始化状态属性
    engine.current_node = None
    engine.history_graph = {}
    return engine

@pytest.fixture
def mock_runtime():
    """
    提供一个模拟的 Runtime (Executor) 实例。
    """
    # 延迟导入以避免循环依赖或在未安装 runtime 时报错
    from pyquipu.runtime.executor import Executor
    runtime = MagicMock(spec=Executor)
    return runtime

# --- CLI Layer Fixtures ---

@pytest.fixture
def quipu_workspace(engine_instance: Engine):
    """
    为 CLI 测试提供 Engine 实例及其工作目录。
    返回: (work_dir_path, git_db, engine)
    """
    return engine_instance.root_dir, engine_instance.git_db, engine_instance

# --- Integration Layer Fixtures ---

@pytest.fixture(scope="module")
def sync_test_environment(tmp_path_factory):
    """
    Sets up a full sync test environment:
    1. A bare remote repository.
    2. Two user workspaces cloned from the remote.
    """
    base_dir = tmp_path_factory.mktemp("sync_tests")
    remote_path = base_dir / "remote.git"
    user_a_path = base_dir / "user_a"
    user_b_path = base_dir / "user_b"

    # 1. Create bare remote
    run_git_command(base_dir, ["init", "--bare", str(remote_path)])

    # 2. Clone for User A
    run_git_command(base_dir, ["clone", str(remote_path), str(user_a_path)])
    run_git_command(user_a_path, ["config", "user.name", "User A"])
    run_git_command(user_a_path, ["config", "user.email", "user.a@example.com"])

    # 3. Clone for User B
    run_git_command(base_dir, ["clone", str(remote_path), str(user_b_path)])
    run_git_command(user_b_path, ["config", "user.name", "User B"])
    run_git_command(user_b_path, ["config", "user.email", "user.b@example.com"])

    # Add a dummy file to avoid issues with initial empty commits
    (user_a_path / "README.md").write_text("Initial commit")
    run_git_command(user_a_path, ["add", "README.md"])
    run_git_command(user_a_path, ["commit", "-m", "Initial commit"])
    run_git_command(user_a_path, ["push", "origin", "HEAD"])
    run_git_command(user_b_path, ["pull"])

    return remote_path, user_a_path, user_b_path

# --- Runtime/Executor Layer Fixtures ---

@pytest.fixture
def mock_runtime_bus(monkeypatch):
    """
    自动 patch 所有 runtime 模块中导入的 'bus' 实例。
    """
    m_bus = MagicMock()
    # 让 bus.get 返回传入的 msg_id，方便测试断言语义
    m_bus.get.side_effect = lambda msg_id, **kwargs: msg_id

    patch_targets = [
        "pyquipu.runtime.executor.bus",
        "pyquipu.runtime.plugin_loader.bus",
        "pyquipu.acts.basic.bus",
        "pyquipu.acts.check.bus",
        "pyquipu.acts.git.bus",
        "pyquipu.acts.memory.bus",
        "pyquipu.acts.read.bus",
        "pyquipu.acts.refactor.bus",
        "pyquipu.acts.shell.bus",
    ]
    for target in patch_targets:
        monkeypatch.setattr(target, m_bus, raising=False)
    return m_bus

@pytest.fixture
def executor(tmp_path: Path):
    """
    为运行时测试提供一个隔离的 Executor 实例。
    """
    from pyquipu.acts.basic import register as register_basic_acts
    from pyquipu.runtime.executor import Executor
    
    instance = Executor(root_dir=tmp_path, yolo=True)
    register_basic_acts(instance)
    return instance

@pytest.fixture
def isolated_vault(executor) -> Path:
    """
    提供 Executor 实例的根工作目录。
    """
    return executor.root_dir