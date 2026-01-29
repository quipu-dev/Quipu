当然。感谢你指出这些遗漏之处，这正是架构重构中彻底审查的重要性所在。为了确保系统的**本体论正确性（Ontological Correctness）**，任何残留的旧接口引用都必须被根除。

我将生成一个计划，使用精确的 `patch_file` 操作来修正这些遗漏的导入。

## [WIP] fix: 修正所有遗留的 pyquipu-interfaces 导入路径

### 用户需求
在之前的重构中，有多个文件（主要在 `tests` 和 `acts` 模块中）的 `import` 语句未被更新。需要将所有指向 `quipu.interfaces` 的引用都修正为新的 `quipu.spec` 路径。

### 评论
这是一个关键的清理步骤。这些遗漏的引用会导致构建失败和类型检查错误，破坏了我们创建 `spec` 包的初衷。通过一次性、自动化的修复，我们可以确保整个代码库的依赖关系恢复一致和正确。

### 目标
1.  定位并修复所有遗留的 `import from quipu.interfaces` 语句。
2.  确保 `QuipuNode`, `ExecutionError`, `ActContext` 等核心类型都从 `quipu.spec` 导入。
3.  处理 `Executor` 类型提示的特殊情况，将其指向 `ExecutorProtocol` 并使用别名以保持兼容。

### 基本原理
我们将使用一系列 `patch_file` 指令，对每个文件进行外科手术式的精确修改。对于涉及 `Executor` 类型提示的 `acts` 模块，我们将采用 `from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor` 的方式，通过别名平滑地完成过渡，而无需修改函数签名中的类型注解。

### 标签
#intent/fix #flow/ready #priority/critical
#comp/build #comp/tests #scope/dx
#ai/instruct
#task/domain/architecture #task/object/spec-package #task/action/dependency-migration #task/state/continue

---

### Script

#### Acts 1: 修正 Application 层测试

~~~~~act
patch_file
packages/pyquipu-application/tests/unit/test_controller.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
~~~~~

#### Acts 2: 修正 CLI 层代码与测试

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/query.py
~~~~~
~~~~~python.old
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/tests/unit/test_tui_logic.py
~~~~~
~~~~~python.old
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/tests/unit/test_tui_reachability.py
~~~~~
~~~~~python.old
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~act
patch_file
packages/pyquipu-cli/tests/unit/test_view_model.py
~~~~~
~~~~~python.old
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader
~~~~~
~~~~~python.new
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader
~~~~~

#### Acts 3: 修正 Engine 层测试

~~~~~act
patch_file
packages/pyquipu-engine/tests/unit/sqlite/test_reader_integrity.py
~~~~~
~~~~~python.old
from quipu.interfaces.models import QuipuNode
~~~~~
~~~~~python.new
from quipu.spec.models.graph import QuipuNode
~~~~~

#### Acts 4: 修正 Runtime 层核心 Acts 模块

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/basic.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/check.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/git.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/memory.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/read.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/refactor.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/acts/shell.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext, Executor
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext, ExecutorProtocol as Executor
~~~~~

#### Acts 5: 修正 Runtime 层测试

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/test_parser_and_basic_acts.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_refactor.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_shell.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_read.py
~~~~~
~~~~~python.old
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_memory.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_check.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
~~~~~
~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_patch_ambiguity.py
~~~~~
~~~~~python.old
from quipu.interfaces.exceptions import ExecutionError
from quipu.interfaces.types import ActContext
~~~~~
~~~~~python.new
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
~~~~~

### 下一步建议

所有已知的 `interfaces` 引用都已被修正。现在是运行完整测试套件 (`pytest`) 的最佳时机，以验证重构的完整性和正确性。

一旦测试通过，我们就可以继续路线图的下一阶段：**收拢 Protocol**，将 `Renderer` 和 `PlanParser` 的定义也迁移到 `spec` 包中，进一步巩固其作为“系统宪法”的地位。
