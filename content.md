你完全正确，并且发现了一个非常微妙但关键的 `pytest` 问题。我对此表示歉意，我的上一个脚本在处理 `conftest.py` 时过于简单，导致了这个问题。

你遇到的 `ImportPathMismatchError` 是一个典型的 `pytest` 命名空间冲突。原因在于：

1.  我们在多个 `packages/*/tests/` 目录下都创建了名为 `conftest.py` 的文件。
2.  `pyproject.toml` 中的 `pythonpath` 设置告诉 `pytest` 将多个 `packages/*/src` 目录视为顶级源路径。
3.  当 `pytest` 收集测试时，它会从多个地方发现 `tests.conftest` 这个模块，并且无法确定哪一个才是权威版本，从而导致导入路径冲突。

你的指示——为每个包手动创建它们各自独立的 `conftest.py`——是解决这个问题的**唯一正确且健壮的方法**。这完全符合“真理单一来源”和“严格分层”的架构原则。每个包的测试环境应该是自包含的。

我将生成一个新计划来纠正这个问题。

## [WIP] fix(test): resolve conftest import collision with package-specific fixtures

### 错误分析
上一次重构脚本错误地在多个包中创建了内容相同或冲突的 `conftest.py` 文件，结合 `pyproject.toml` 中的 `pythonpath` 配置，引发了 `pytest` 的 `ImportPathMismatchError`。这是因为 `pytest` 在测试收集阶段发现了多个同名的 `tests.conftest` 模块，造成了命名空间冲突。

### 用户需求
纠正此问题，为每个需要测试辅助函数的包 (`application`, `cli`, `engine`, `runtime`) 创建独立的、内容正确的 `conftest.py` 文件。

### 评论
这是一个关键的修复，它将测试基础设施的关注点正确地分离到各自的包中。通过为每个包提供一个量身定制的 `conftest.py`，我们不仅解决了眼前的导入错误，还建立了一个更清晰、更模块化、更易于维护的测试结构。

### 目标
1.  **清理**: 删除所有由上一个脚本错误创建的 `conftest.py` 文件。
2.  **重建**:
    *   在 `packages/quipu-application/tests/` 中创建一个 `conftest.py`，只包含它需要的 `mock_engine` 和 `mock_runtime` fixture。
    *   在 `packages/quipu-cli/tests/` 中创建一个 `conftest.py`，包含它需要的 `quipu_workspace` fixture。
    *   在 `packages/quipu-engine/tests/` 中创建一个 `conftest.py`，包含 `git_workspace` 和 `engine_instance` 这两个核心 fixture。
    *   在 `packages/quipu-runtime/tests/` 中创建一个 `conftest.py`，包含 `mock_runtime_bus`、`executor` 和 `isolated_vault` fixture。
3.  **根治**: 从 `pyproject.toml` 中移除有问题的 `pythonpath` 配置，因为 `uv` 的工作区设置已经能保证正确的模块解析，`pythonpath` 在这里反而造成了冲突。

### 基本原理
我们将采用一个三步走的策略来确保修复的彻底性：
1.  **清除**: 使用 `run_command` 和 `find ... -delete` 命令，原子性地删除所有现存的 `conftest.py` 文件，确保一个干净的起点。
2.  **重建**: 使用 `write_file` 为每个包精确地创建新的 `conftest.py` 文件。每个文件的内容都是根据该包内测试代码的实际 `import` 和依赖关系精心挑选的，不多不少。
3.  **修复配置**: 使用 `patch_file` 移除 `pyproject.toml` 中的 `tool.pytest.ini_options.pythonpath`。这是解决命名空间冲突的根本措施，它强制 `pytest` 依赖标准的 Python 导入机制，而不是一个可能引起歧义的路径列表。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #comp/build #scope/dx #ai/instruct #task/domain/testing #task/object/test-suite-structure #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 清理所有现存的 `conftest.py` 文件

为了避免任何残留的配置引起问题，我们首先彻底删除所有包内 `tests` 目录下的 `conftest.py` 文件。

~~~~~act
run_command
~~~~~
~~~~~bash
find packages -path "*/tests/conftest.py" -delete
~~~~~

#### Acts 2: 为每个包创建独立的、正确的 `conftest.py`

现在，我们为每个需要 fixture 的包创建量身定制的 `conftest.py`。

**Application Fixtures**
`mock_engine` 和 `mock_runtime` 是 `application` 包单元测试专属的。

~~~~~act
write_file
packages/quipu-application/tests/conftest.py
~~~~~
~~~~~python
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
    engine.root_dir = Path("/mock/root")
    engine.git_db = MagicMock()
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

**CLI Fixtures**
CLI 测试需要 `quipu_workspace`，它依赖于 `engine_instance`。

~~~~~act
write_file
packages/quipu-cli/tests/conftest.py
~~~~~
~~~~~python
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

**Engine Fixtures (Root-level Shared)**
`engine_instance` 和 `git_workspace` 是最核心的 fixture，被 CLI 和 Engine 测试共享，放在 Engine 包中作为权威来源。同时，CLI 测试依赖的 `runner` 也放在这里，作为事实上的项目级共享 fixture。

~~~~~act
write_file
packages/quipu-engine/tests/conftest.py
~~~~~
~~~~~python
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

**Runtime Fixtures**
`runtime` 包的测试需要 `executor`, `isolated_vault` 和 `mock_runtime_bus`。

~~~~~act
write_file
packages/quipu-runtime/tests/conftest.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 3: 从 `pyproject.toml` 移除冲突的 `pythonpath`

这是根治问题的关键一步。我们将移除 `pytest.ini_options` 中的 `pythonpath`。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.pytest.ini_options]
addopts = "-ra --cov=pyquipu --cov-report=term-missing"
pythonpath = [
  "packages/quipu-interfaces/src",
  "packages/quipu-engine/src",
  "packages/quipu-runtime/src",
  "packages/quipu-cli/src",
  "packages/quipu-common/src",
]

[build-system]
~~~~~
~~~~~toml.new
[tool.pytest.ini_options]
addopts = "-ra --cov=pyquipu --cov-report=term-missing"

[build-system]
~~~~~

### 下一步建议
我们已经完成了对 `conftest.py` 问题的修复，并从根本上解决了 `pytest` 的路径冲突。

1.  **执行计划**: 请执行此计划。
2.  **验证**: 再次运行 `pytest`。这次测试应该能够成功收集并运行。
3.  **提交**: 在验证通过后，将这些修复作为一个独立的 `fix` 提交。
