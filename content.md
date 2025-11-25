# refactor (Phase 1.1) 建立接口层隔离

## 目标
完成 Quipu 重构的第一阶段第一步：建立接口层 (Interface Isolation)。
将核心数据结构和异常定义从逻辑代码中分离，重命名为 `intf_*.py`，并更新所有相关的导入路径。

## 基本原理
为了实现“星座模型”架构，我们需要打破模块间的强耦合。
当前的 `core/types.py`, `core/models.py`, `core/exceptions.py`, `core/result.py` 被广泛引用。将它们重命名并显式定义为 "Interface" (intf)，有助于在后续的物理拆分（Phase 2）中，清晰地将它们移动到 `quipu-interfaces` 包中，而不带入业务逻辑依赖。

## 标签
 #refactor #core #interface

---

## Script

### Act 1: 重命名接口文件

将 `core` 目录下的四个基础定义文件添加 `intf_` 前缀，明确其作为接口层的身份。

~~~~~act
move_file core/types.py core/intf_types.py
~~~~~

~~~~~act
move_file core/models.py core/intf_models.py
~~~~~

~~~~~act
move_file core/exceptions.py core/intf_exceptions.py
~~~~~

~~~~~act
move_file core/result.py core/intf_result.py
~~~~~

### Act 2: 修正 intf_types.py 内部引用

`core/intf_types.py` 内部引用了 `core/exceptions.py`，需要更新为指向新的 `core/intf_exceptions.py`。

~~~~~act
replace core/intf_types.py
~~~~~

~~~~~python
from .exceptions import ExecutionError
~~~~~

~~~~~python
from .intf_exceptions import ExecutionError
~~~~~

### Act 3: 更新 Acts 目录中的引用 (Types & Exceptions)

更新 `acts/` 目录下所有插件对 `core.types` 和 `core.exceptions` 的引用。

~~~~~act
replace acts/basic.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
~~~~~

~~~~~act
replace acts/check.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
~~~~~

~~~~~act
replace acts/git.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
from core.exceptions import ExecutionError
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
from core.intf_exceptions import ExecutionError
~~~~~

~~~~~act
replace acts/memory.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
~~~~~

~~~~~act
replace acts/read.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
from core.exceptions import ExecutionError
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
from core.intf_exceptions import ExecutionError
~~~~~

~~~~~act
replace acts/refactor.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
~~~~~

~~~~~act
replace acts/shell.py
~~~~~

~~~~~python
from core.types import ActContext, Executor
~~~~~

~~~~~python
from core.intf_types import ActContext, Executor
~~~~~

### Act 4: 更新 Core 目录中的引用 (Executor, Parser, GitDB)

更新 `core/` 目录下的逻辑模块对接口文件的引用。

~~~~~act
replace core/executor.py
~~~~~

~~~~~python
from .types import Statement, ActFunction, ActContext
from .exceptions import ExecutionError
~~~~~

~~~~~python
from .intf_types import Statement, ActFunction, ActContext
from .intf_exceptions import ExecutionError
~~~~~

~~~~~act
replace core/parser.py
~~~~~

~~~~~python
from .types import Statement
~~~~~

~~~~~python
from .intf_types import Statement
~~~~~

~~~~~act
replace core/git_db.py
~~~~~

~~~~~python
from .exceptions import ExecutionError
~~~~~

~~~~~python
from .intf_exceptions import ExecutionError
~~~~~

### Act 5: 更新 Core 目录中的引用 (Engine, History, Controller)

继续更新 `core/` 目录下的引用，涉及 Models, Result 和 Exceptions。

~~~~~act
replace core/engine.py
~~~~~

~~~~~python
from .models import AxonNode
~~~~~

~~~~~python
from .intf_models import AxonNode
~~~~~

~~~~~act
replace core/history.py
~~~~~

~~~~~python
from .models import AxonNode
~~~~~

~~~~~python
from .intf_models import AxonNode
~~~~~

~~~~~act
replace core/controller.py
~~~~~

~~~~~python
from .result import AxonResult
from .engine import Engine
from .executor import Executor, ExecutionError
from .exceptions import ExecutionError as CoreExecutionError # Alias to avoid conflict
~~~~~

~~~~~python
from .intf_result import AxonResult
from .engine import Engine
from .executor import Executor, ExecutionError
from .intf_exceptions import ExecutionError as CoreExecutionError # Alias to avoid conflict
~~~~~

### Act 6: 更新 Main 和 UI 中的引用

更新入口文件 `main.py` 和 UI 模块 `ui/tui.py` 对 `core.models` 的引用。

~~~~~act
replace main.py
~~~~~

~~~~~python
from core.models import AxonNode
~~~~~

~~~~~python
from core.intf_models import AxonNode
~~~~~

~~~~~act
replace ui/tui.py
~~~~~

~~~~~python
from core.models import AxonNode
~~~~~

~~~~~python
from core.intf_models import AxonNode
~~~~~

### Act 7: 更新 Tests 中的引用

更新测试文件以匹配新的接口文件名。

~~~~~act
replace tests/test_check.py
~~~~~

~~~~~python
from core.types import ActContext
~~~~~

~~~~~python
from core.intf_types import ActContext
~~~~~

~~~~~act
replace tests/test_ops.py
~~~~~

~~~~~python
from core.types import ActContext
~~~~~

~~~~~python
from core.intf_types import ActContext
~~~~~

~~~~~act
replace tests/test_read.py
~~~~~

~~~~~python
from core.types import ActContext
~~~~~

~~~~~python
from core.intf_types import ActContext
~~~~~

~~~~~act
replace tests/test_ui_logic.py
~~~~~

~~~~~python
from core.models import AxonNode
~~~~~

~~~~~python
from core.intf_models import AxonNode
~~~~~

~~~~~act
replace tests/test_ui_reachability.py
~~~~~

~~~~~python
from core.models import AxonNode
~~~~~

~~~~~python
from core.intf_models import AxonNode
~~~~~