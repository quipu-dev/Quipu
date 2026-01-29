好的，我们现在执行重构路线图的**阶段二：物理迁移与链接重定向**。

此计划将自动化执行所有必要的代码和配置修改，将整个项目对 `pyquipu-interfaces` 的依赖彻底切换到我们新创建的 `pyquipu-spec` 包，并最终移除旧包。

## [WIP] refactor: 将项目依赖从 pyquipu-interfaces 迁移到 pyquipu-spec

### 用户需求
1.  修改所有 `pyproject.toml` 文件，将依赖项从 `pyquipu-interfaces` 替换为 `pyquipu-spec`。
2.  更新所有 Python 源码文件中的 `import` 语句，使其指向 `quipu.spec` 下的新模块路径。
3.  物理删除 `packages/pyquipu-interfaces` 目录。

### 评论
这是一个典型的“大爆炸”式重构，通过自动化脚本一次性完成所有变更，可以最大限度地减少系统处于不一致状态的时间。这是实现 Clean Cut 策略的核心执行步骤。

### 目标
1.  确保项目的构建配置（`pyproject.toml`）正确反映新的 `spec` 依赖。
2.  保证所有 Python 代码的类型注解和导入都与新的 `spec` 包结构保持一致。
3.  从文件系统中彻底移除已废弃的 `interfaces` 包，完成迁移。

### 基本原理
我们将使用一系列精确的 `patch_file` 指令来修改配置文件和源码。这种方式比 `write_file` 更能保留文件原有的格式和注释。
1.  **配置先行**: 首先修改 `pyproject.toml`，确保构建系统了解新的依赖关系。
2.  **源码同步**: 接着修改 Python 代码的导入语句，使其与新的包结构和依赖关系对齐。
3.  **清理收尾**: 最后，执行 `rm -rf` 命令删除旧包，完成整个迁移过程。

### 标签
#intent/refine #flow/ready #priority/critical
#comp/build #comp/interfaces #scope/core #scope/dx
#ai/instruct
#task/domain/architecture #task/object/spec-package #task/action/dependency-migration #task/state/continue

---

### Script

#### Acts 1: 更新根构建配置

修改项目根目录的 `pyproject.toml`，将 `uv` 的 workspace 配置和 `pytest` 的 pythonpath 指向 `spec` 包。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu = { workspace = true }
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
pyquipu-cli = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-interfaces = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-test-utils = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra --cov=quipu --cov-report=term-missing"
testpaths = "tests packages"
pythonpath = [
  "packages/pyquipu/src",
  "packages/pyquipu-interfaces/src",
  "packages/pyquipu-engine/src",
  "packages/pyquipu-runtime/src",
  "packages/pyquipu-cli/src",
  "packages/pyquipu-common/src",
  "packages/pyquipu-application/src",
  "packages/pyquipu-test-utils/src",
]
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu = { workspace = true }
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
pyquipu-cli = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-spec = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-test-utils = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra --cov=quipu --cov-report=term-missing"
testpaths = "tests packages"
pythonpath = [
  "packages/pyquipu/src",
  "packages/pyquipu-spec/src",
  "packages/pyquipu-engine/src",
  "packages/pyquipu-runtime/src",
  "packages/pyquipu-cli/src",
  "packages/pyquipu-common/src",
  "packages/pyquipu-application/src",
  "packages/pyquipu-test-utils/src",
]
~~~~~

#### Acts 2: 更新子包构建配置

遍历所有子包，将其 `pyproject.toml` 中的 `pyquipu-interfaces` 依赖替换为 `pyquipu-spec`。

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
]
~~~~~
~~~~~toml.new
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.1",
]
~~~~~
~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
~~~~~
~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
pyquipu-spec = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~

#### Acts 3: 更新 Python 源码导入路径

现在，我们修改所有 Python 文件，将 `import` 语句重定向到 `quipu.spec`。

~~~~~act
patch_file
packages/pyquipu-application/src/quipu/application/controller.py
~~~~~
~~~~~python.old
from quipu.engine.state_machine import Engine
from quipu.interfaces.exceptions import ExecutionError as CoreExecutionError
from quipu.interfaces.exceptions import OperationCancelledError
from quipu.interfaces.result import QuipuResult
from quipu.runtime.executor import Executor
~~~~~
~~~~~python.new
from quipu.engine.state_machine import Engine
from quipu.spec.exceptions import ExecutionError as CoreExecutionError
from quipu.spec.exceptions import OperationCancelledError
from quipu.spec.models.execution import QuipuResult
from quipu.runtime.executor import Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python.old
import typer
import yaml
from quipu.bus import bus
from quipu.engine.state_machine import Engine
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
import typer
import yaml
from quipu.bus import bus
from quipu.engine.state_machine import Engine
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/helpers.py
~~~~~
~~~~~python.old
import typer
from quipu.application.factory import create_engine
from quipu.bus import bus
from quipu.engine.state_machine import Engine
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
import typer
from quipu.application.factory import create_engine
from quipu.bus import bus
from quipu.engine.state_machine import Engine
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python.old
from quipu.application.factory import create_engine
from quipu.engine.state_machine import Engine
from quipu.interfaces.models import QuipuNode
from textual import on
~~~~~
~~~~~python.new
from quipu.application.factory import create_engine
from quipu.engine.state_machine import Engine
from quipu.spec.models.graph import QuipuNode
from textual import on
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/ui_utils.py
~~~~~
~~~~~python.old
from typing import List, Optional

import click
import typer
from quipu.bus import bus
from quipu.interfaces.exceptions import OperationCancelledError
~~~~~
~~~~~python.new
from typing import List, Optional

import click
import typer
from quipu.bus import bus
from quipu.spec.exceptions import OperationCancelledError
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/view_model.py
~~~~~
~~~~~python.old
import math
from typing import Dict, List, Optional, Set

from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader
~~~~~
~~~~~python.new
import math
from typing import Dict, List, Optional, Set

from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_db.py
~~~~~
~~~~~python.old
from quipu.bus import bus
from quipu.interfaces.exceptions import ExecutionError
~~~~~
~~~~~python.new
from quipu.bus import bus
from quipu.spec.exceptions import ExecutionError
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
from quipu.engine.git_db import GitDB
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python.new
from quipu.engine.git_db import GitDB
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python.new
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
from quipu.common.identity import get_user_id_from_email
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python.new
from quipu.common.identity import get_user_id_from_email
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/executor.py
~~~~~
~~~~~python.old
from quipu.bus import bus
from quipu.interfaces.exceptions import ExecutionError, OperationCancelledError
from quipu.interfaces.types import ActContext, ActFunction, Statement
~~~~~
~~~~~python.new
from quipu.bus import bus
from quipu.spec.exceptions import ExecutionError, OperationCancelledError
from quipu.spec.protocols.runtime import ActContext, ActFunction
from quipu.spec.models.execution import Statement
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from quipu.interfaces.types import Statement
~~~~~
~~~~~python.new
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from quipu.spec.models.execution import Statement
~~~~~
~~~~~act
patch_file
packages/pyquipu-test-utils/src/quipu/test_utils/fixtures.py
~~~~~
~~~~~python.old
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.engine.state_machine import Engine
from quipu.test_utils.helpers import run_git_command
~~~~~
~~~~~python.new
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.engine.state_machine import Engine
from quipu.test_utils.helpers import run_git_command
~~~~~
~~~~~act
patch_file
packages/pyquipu-test-utils/src/quipu/test_utils/helpers.py
~~~~~
~~~~~python.old
from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python.new
from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter
~~~~~

#### Acts 4: 物理移除旧包

最后，我们从文件系统中删除 `pyquipu-interfaces` 包。

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/pyquipu-interfaces
~~~~~

### 下一步建议

我们已经完成了 `spec` 包的创建和依赖迁移。现在整个项目应该可以正常构建和测试了。

下一步是继续执行路线图的**阶段三：协议化改革 (Protocolization)**，将 `spec` 包内的 `ABC` 转换为 `Protocol`，并开始收拢散落在各处的协议定义，例如将 `bus` 和 `cli` 中的 `Renderer` Protocol 统一到 `spec` 中。
