这是基于 **HFEA (高保真工程公理)** 和 **ADAP (假设驱动分析协议)** 的重构计划。我们将通过建立一个“测试基础设施层”来消除当前的冗余和潜在冲突。

### 核心变更

1.  **基础设施化 (Infrastructuralization)**: 将所有分散的 `conftest.py` 中的逻辑提取到 `packages/quipu-test-utils/src/pyquipu/test_utils/fixtures.py` 中，使其成为 SSoT (单一真理来源)。
2.  **引用化 (Referencing)**: 各个 `conftest.py` 转变为“消费者”，仅负责从工具包中导入所需的 Fixture，不再持有实现逻辑。

---

### Script

#### Acts 1: 构建统一的 Fixture 仓库

我们将所有通用的测试夹具逻辑集中到一个文件中。

~~~~~act
write_file
packages/quipu-test-utils/src/pyquipu/test_utils/fixtures.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 2: 重构根目录 `conftest.py`

根目录配置只保留全局设置和最核心的 Fixture 引用。

~~~~~act
patch_file
tests/conftest.py
~~~~~
~~~~~python.old
import subprocess
from pathlib import Path

import pytest
from pyquipu.engine.git_db import GitDB
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """提供一个可复用的 CliRunner 实例。"""
    return CliRunner()


@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    """
    提供一个已初始化 Git 的干净工作区路径。
    这是最基础的环境 fixture。
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
    这是最常用的 fixture，用于所有需要 Engine 核心逻辑的测试。
    """
    git_db = GitDB(git_workspace)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(root_dir=git_workspace, db=git_db, reader=reader, writer=writer)
    return engine
~~~~~
~~~~~python.new
from pyquipu.test_utils.fixtures import engine_instance, git_workspace, runner

__all__ = ["runner", "git_workspace", "engine_instance"]
~~~~~

#### Acts 3: 重构 Application 层 `conftest.py`

移除了本地定义的 Mock 工厂，改为从 `test_utils` 导入。

~~~~~act
patch_file
tests/application/conftest.py
~~~~~
~~~~~python.old
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyquipu.engine.state_machine import Engine
from pyquipu.runtime.executor import Executor


@pytest.fixture
def mock_engine():
    """
    提供一个模拟的 Engine 实例。
    用于测试 Application 层在不触及真实 Git/文件系统的情况下的编排逻辑。
    """
    engine = MagicMock(spec=Engine)

    # 设置基础属性以防止简单的 AttributeError (绕过 spec 检查)
    engine.root_dir = Path("/mock/root")

    # 显式初始化 git_db，因为它是实例属性，spec 可能不包含它
    engine.git_db = MagicMock()

    # 初始化状态属性
    engine.current_node = None
    engine.history_graph = {}

    return engine


@pytest.fixture
def mock_runtime():
    """
    提供一个模拟的 Runtime (Executor) 实例。
    用于验证 Application 层是否正确调用了执行器，而不真正执行 Act。
    """
    runtime = MagicMock(spec=Executor)
    return runtime
~~~~~
~~~~~python.new
from pyquipu.test_utils.fixtures import mock_engine, mock_runtime

__all__ = ["mock_engine", "mock_runtime"]
~~~~~

#### Acts 4: 重构 CLI 层 `conftest.py`

`quipu_workspace` 现在也从工具库导入，确保与 `engine_instance` 的定义保持同步。

~~~~~act
patch_file
tests/cli/conftest.py
~~~~~
~~~~~python.old
import pytest
from pyquipu.engine.state_machine import Engine

# runner fixture is now in the root conftest.py, so it's removed from here.


@pytest.fixture
def quipu_workspace(engine_instance: Engine):
    """
    为 CLI 测试提供 Engine 实例及其工作目录，保持原有返回结构以兼容现有测试。
    返回: (work_dir_path, git_db, engine)
    """
    return engine_instance.root_dir, engine_instance.git_db, engine_instance
~~~~~
~~~~~python.new
from pyquipu.test_utils.fixtures import quipu_workspace

__all__ = ["quipu_workspace"]
~~~~~

#### Acts 5: 重构 Integration 层 `conftest.py`

移除了复杂的 `sync_test_environment` 逻辑，改为导入。

~~~~~act
patch_file
tests/integration/conftest.py
~~~~~
~~~~~python.old
import pytest

from pyquipu.test_utils.helpers import run_git_command


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
~~~~~
~~~~~python.new
from pyquipu.test_utils.fixtures import sync_test_environment

__all__ = ["sync_test_environment"]
~~~~~

#### Acts 6: 重构 Runtime 层 `conftest.py`

清理了大量重复的 Executor 初始化和 Bus Mocking 逻辑。

~~~~~act
patch_file
tests/runtime/conftest.py
~~~~~
~~~~~python.old
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyquipu.acts.basic import register as register_basic_acts
from pyquipu.runtime.executor import Executor


@pytest.fixture(autouse=True)
def mock_runtime_bus(monkeypatch):
    """
    自动 patch 所有 runtime 模块中导入的 'bus' 实例。
    """
    m_bus = MagicMock()

    # 关键修改：让 bus.get 返回传入的 msg_id，方便测试断言语义
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
def executor(tmp_path: Path) -> Executor:
    """
    为运行时测试提供一个隔离的 Executor 实例。
    - 在独立的临时目录 (tmp_path) 中运行。
    - 自动注册基础 acts。
    - 默认以非交互模式 (yolo=True) 运行。
    """
    instance = Executor(root_dir=tmp_path, yolo=True)
    register_basic_acts(instance)
    return instance


@pytest.fixture
def isolated_vault(executor: Executor) -> Path:
    """
    提供 Executor 实例的根工作目录。
    """
    return executor.root_dir


def pytest_configure(config):
    """注册自定义标记以消除警告"""
    config.addinivalue_line("markers", "timeout(seconds): kill test after a certain time")
~~~~~
~~~~~python.new
from pyquipu.test_utils.fixtures import executor, isolated_vault, mock_runtime_bus

# 保持 autouse 生效
@pytest.fixture(autouse=True)
def _auto_mock_runtime_bus(mock_runtime_bus):
    return mock_runtime_bus

def pytest_configure(config):
    """注册自定义标记以消除警告"""
    config.addinivalue_line("markers", "timeout(seconds): kill test after a certain time")

__all__ = ["executor", "isolated_vault", "mock_runtime_bus"]
~~~~~
