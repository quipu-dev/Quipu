# fix-test: 修复重构后的 pytest 导入错误

## 目标
解决在运行 `pytest` 时出现的 `ModuleNotFoundError`，使测试能够在新重构的项目结构下正常运行。

## 基本原理
第一步，我们将递归删除项目中的所有 `__pycache__` 目录。这是一个安全的、标准的调试步骤，用于清除可能导致导入冲突的旧字节码缓存文件。

第二步，我们将修改 `tests/conftest.py`。将 `Executor` 类的导入从文件的顶层移动到 `executor` fixture 函数的内部。这种“延迟导入” (deferred import) 的模式更加健壮，因为它确保了只有在 `pytest` 完全初始化、`PYTHONPATH` 已经设置好、并且 fixture 实际被调用时，才会去解析该模块。为了保持类型提示的有效性，我们将使用字符串类型提示 (`-> "Executor"`)。

## 标签
#fix #test

---

## Script

### Act 1: 清理所有 __pycache__ 目录

这是一个标准的维护操作，用于解决因缓存不一致导致的导入问题。

~~~~~act
run_command
~~~~~

~~~~~shell
find . -type d -name "__pycache__" -exec rm -r {} +
~~~~~

### Act 2: 修改 conftest.py 以使用延迟导入

此操作将重构 `tests/conftest.py`，使其对 `PYTHONPATH` 的初始化顺序不那么敏感。

~~~~~act
replace tests/conftest.py
~~~~~

~~~~~python
import pytest
from pathlib import Path
from quipu.core.executor import Executor
from acts.basic import register as register_basic_acts

@pytest.fixture
def isolated_vault(tmp_path: Path) -> Path:
    """
    创建一个临时的隔离工作区。
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault

@pytest.fixture
def executor(isolated_vault: Path) -> Executor:
    """
    返回一个绑定到临时工作区的执行器实例，并预装了基础 Acts。
    测试期间默认开启 YOLO 模式，跳过交互确认。
    """
    exc = Executor(root_dir=isolated_vault, yolo=True)
    register_basic_acts(exc)
    return exc
~~~~~

~~~~~python
import pytest
from pathlib import Path
from typing import TYPE_CHECKING
from acts.basic import register as register_basic_acts

# 使用 TYPE_CHECKING 块来辅助静态分析工具，而不在运行时导入
if TYPE_CHECKING:
    from quipu.core.executor import Executor

@pytest.fixture
def isolated_vault(tmp_path: Path) -> Path:
    """
    创建一个临时的隔离工作区。
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault

@pytest.fixture
def executor(isolated_vault: Path) -> "Executor":
    """
    返回一个绑定到临时工作区的执行器实例，并预装了基础 Acts。
    测试期间默认开启 YOLO 模式，跳过交互确认。
    """
    # 将导入操作延迟到 fixture 函数内部执行
    from quipu.core.executor import Executor
    
    exc = Executor(root_dir=isolated_vault, yolo=True)
    register_basic_acts(exc)
    return exc
~~~~~