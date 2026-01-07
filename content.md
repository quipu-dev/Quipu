再次感谢你指出我的错误。我的上一处修复不够彻底，只更正了 `conftest.py`，却遗漏了同样存在导入错误的 `test_sync_workflow.py`。此外，文件树中显示的 `tests/tests/helpers.py` 明显是一个冗余的错误文件，我将一并清理掉。

我将立即生成一个计划来修正这两个问题。

## [WIP] fix(tests): 修正剩余导入路径并移除重复的辅助文件

### 错误分析

1.  **导入错误**: `tests/integration/test_sync_workflow.py` 文件中仍然存在 `from .helpers import run_git_command` 的错误导入语句。与 `conftest.py` 一样，它需要被更新为 `from ..helpers import run_git_command` 以正确定位到顶层的 `tests/helpers.py`。
2.  **冗余文件**: 文件列表中存在一个 `tests/tests/helpers.py` 文件。这是一个错误的路径，可能是之前操作失误的产物。它与 `tests/helpers.py` 内容重复且位置错误，会造成混淆，必须删除。

### 用户需求

彻底解决因模块导入路径不正确导致的 `ModuleNotFoundError`，并清理测试目录中结构错误的冗余文件。

### 评论

这次修复将完成对测试目录结构的基础清理工作，确保所有集成测试都能正确找到其依赖的辅助函数，并移除干扰性的重复文件。这是进行下一步大规模重构的必要前提。

### 目标

1.  修改 `tests/integration/test_sync_workflow.py` 中的导入语句，使其指向正确的顶层辅助模块。
2.  删除错误的 `tests/tests/helpers.py` 文件。

### 基本原理

通过 `patch_file` 精确修正 `test_sync_workflow.py` 中的相对导入路径。通过 `delete_file` 移除冗余的辅助文件。这两个原子操作将一次性解决当前测试集合失败的所有已知原因。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/imports #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `test_sync_workflow.py` 的导入路径

我将修正 `test_sync_workflow.py` 中的导入语句，使其与 `conftest.py` 保持一致。

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python.old
from typer.testing import CliRunner

from .helpers import run_git_command

runner = CliRunner()
~~~~~
~~~~~python.new
from typer.testing import CliRunner

from ..helpers import run_git_command

runner = CliRunner()
~~~~~

#### Acts 2: 删除冗余的 `helpers.py`

现在，我将删除那个位置错误的 `helpers.py` 文件。

~~~~~act
delete_file
tests/tests/helpers.py
~~~~~

### 下一步建议

现在，所有的导入问题和结构性错误都应该已解决，测试套件应该可以成功运行了。

我们可以安全地回到之前的计划：继续审查 `tests/cli` 和 `tests/engine` 目录，将其中重复的 fixture 和本地辅助函数，用 `tests/helpers.py` 中的标准化函数进行替换，以提高代码的复用性和可维护性。
