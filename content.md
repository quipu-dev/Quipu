## [WIP] test: 建立 Application 层测试基础设施 (第一阶段)

### 用户需求
根据“测试分层与应用架构错配”的诊断分析，我们需要开始重构测试套件。第一阶段的目标是建立 `pyquipu-application` 包的专属测试领地，即 `tests/application/` 目录及其基础配置 (`conftest.py`)。

### 目标
1.  创建 `tests/application/` 目录（通过创建 `__init__.py`）。
2.  创建 `tests/application/conftest.py`，并在其中定义用于隔离测试的 Mock Fixtures。
3.  确保新的测试环境能够通过 Mock 注入 `Engine` 和 `Runtime`，从而支持对 `Controller` 逻辑的纯单元测试。

### 基本原理
为了解决测试分层错配的问题，我们需要物理上隔离应用层的测试。通过引入 `mock_engine` 和 `mock_runtime` fixture，我们可以切断对底层实现（如真实的 Git 操作或文件系统修改）的依赖，使应用层的编排逻辑测试更加快速、稳定且聚焦。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/tests #concept/executor #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 初始化 Application 测试包

首先，我们创建一个空的 `__init__.py` 文件，将 `tests/application` 标记为一个 Python 包。

~~~~~act
write_file tests/application/__init__.py
~~~~~
~~~~~python
~~~~~

#### Acts 2: 配置 Application 层专用的 Fixtures

接着，我们创建 `tests/application/conftest.py`。在这里，我们将定义 `mock_engine` 和 `mock_runtime`。这些 fixture 将使用 `unittest.mock.MagicMock` 来模拟真实的引擎和运行时，确保应用层的测试不会产生副作用（如写磁盘或调用 Git）。

~~~~~act
write_file tests/application/conftest.py
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
    # 设置基础属性以防止简单的 AttributeError
    engine.root_dir = Path("/mock/root")
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

### 下一步建议
完成基础设施建设后，我们可以进入**第二阶段：应用层测试迁移**。我们将把 `tests/integration/test_cli_workflow.py` 中的 `TestController` 类及其逻辑迁移到 `tests/application/test_controller.py` 中，并改用上述 Mock Fixtures 进行测试。
