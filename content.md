**检测到“测试模块命名冲突”违例，已根据 ADAP v1.0 协议挂起执行。**

**分析显示，为了继续执行任务，我必须做出以下未经证实的核心假设：**
*   假设 `pytest` 能够自动处理两个都名为 `tests` 且都包含 `__init__.py` 的包（根目录 `tests` 和 `packages/pkg/tests`）之间的命名空间冲突。

**诊断缺失组件:**
*   **明确的测试包命名策略**：当前架构在根目录和子包中同时使用了 `tests` 作为包名（通过添加 `__init__.py`），导致 Python 导入系统出现“影子（Shadowing）”和“路径不匹配（Path Mismatch）”错误。我们必须移除子包测试目录中的 `__init__.py`，使其成为“命名空间包（Namespace Packages）”或简单的文件目录，从而避免被识别为顶层 `tests` 包。

**拒绝战术修复并提出战略方案:**
*   我拒绝仅修复报错文件的“打地鼠”式尝试。
*   我提议执行以下战略修复：
    1.  **清理命名空间**：批量删除 `packages/*/tests` 及其子目录下的所有 `__init__.py` 文件。这将解除它们作为 Python 包的身份，消除与根目录 `tests` 的冲突。
    2.  **修正引用方式**：由于移除了 `__init__.py`，显式相对导入（如 `from .foo import bar`）将失效。必须将其转换为隐式同级导入（`from foo import bar`），这利用了 Pytest 将当前测试目录加入 `sys.path` 的特性。

---

### [WIP] refactor(tests): 移除子包测试目录的 __init__.py 以解决命名冲突

### 用户需求
解决运行 `pytest packages` 时出现的 `ImportPathMismatchError` 和 `ModuleNotFoundError`。

### 评论
这是一个经典的 Python 测试结构陷阱。在 Monorepo 中，如果不小心在嵌套的 `tests` 目录中放置了 `__init__.py`，Python 就会尝试将其解析为名为 `tests` 的顶层包，从而与根目录的 `tests` 发生灾难性的冲突。移除 `__init__.py` 是最标准、最符合 Pytest 推荐实践（"Tests as part of application code" vs "Tests outside application code"）的解法。

### 目标
1.  删除所有 `packages/*/tests/**/__init__.py` 文件。
2.  修复因移除 `__init__.py` 而破坏的相对导入（主要在 `quipu-cli` 的单元测试中）。

### 基本原理
1.  **消除歧义**：没有 `__init__.py`，`pytest` 会根据文件路径生成唯一的模块名（如 `packages.quipu_cli.tests.unit.test_foo`），而不是通用的 `tests.unit.test_foo`，从而解决 `ImportPathMismatchError`。
2.  **利用 Pytest 机制**：Pytest 默认将正在执行的测试文件所在目录添加到 `sys.path`。这意味着我们可以直接 `import sibling_module` 而不需要 `from . import sibling_module`。

### 标签
#intent/fix #flow/ready #priority/high
#comp/tests #scope/dx
#ai/instruct
#task/domain/testing #task/object/test-structure #task/action/namespace-fix #task/state/continue

---

### Script

#### Acts 1: 批量删除冲突的 `__init__.py`

我们使用 `find` 命令来精确定位并删除这些文件。保留根目录 `tests/__init__.py`。

~~~~~act
run_command
~~~~~
~~~~~bash
find packages -path "*/tests/__init__.py" -delete
find packages -path "*/tests/unit/__init__.py" -delete
find packages -path "*/tests/integration/__init__.py" -delete
find packages -path "*/tests/integration/*/__init__.py" -delete
find packages -path "*/tests/unit/*/__init__.py" -delete
~~~~~

#### Acts 2: 修复 `test_tui_logic.py` 的相对导入

将 `from .test_view_model import` 改为 `from test_view_model import`。

~~~~~act
patch_file
packages/quipu-cli/tests/unit/test_tui_logic.py
~~~~~
~~~~~python.old
from pyquipu.cli.tui import QuipuUiApp
from pyquipu.cli.view_model import GraphViewModel
from pyquipu.interfaces.models import QuipuNode

from .test_view_model import MockHistoryReader
~~~~~
~~~~~python.new
from pyquipu.cli.tui import QuipuUiApp
from pyquipu.cli.view_model import GraphViewModel
from pyquipu.interfaces.models import QuipuNode

from test_view_model import MockHistoryReader
~~~~~

#### Acts 3: 修复 `test_tui_reachability.py` 的相对导入

同样的操作。

~~~~~act
patch_file
packages/quipu-cli/tests/unit/test_tui_reachability.py
~~~~~
~~~~~python.old
from pyquipu.cli.tui import QuipuUiApp
from pyquipu.cli.view_model import GraphViewModel
from pyquipu.interfaces.models import QuipuNode

from .test_view_model import MockHistoryReader
~~~~~
~~~~~python.new
from pyquipu.cli.tui import QuipuUiApp
from pyquipu.cli.view_model import GraphViewModel
from pyquipu.interfaces.models import QuipuNode

from test_view_model import MockHistoryReader
~~~~~

### 下一步建议
再次运行 `uv run pytest packages` 验证修复效果。如果通过，则说明测试架构迁移成功。
