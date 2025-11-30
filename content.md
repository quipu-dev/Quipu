好的，针对 `tests/` 目录下的 lint 错误，我将创建一个修复计划。

这些错误主要是未使用的导入 (`F401`)、重复定义 (`F811`) 和导入排序 (`I001`) 问题。

## [WIP] fix(tests): 修复集成测试中的 lint 错误

### 错误分析
`ruff` 扫描报告了 `tests/integration/conftest.py` 和 `tests/integration/test_sync_workflow.py` 中的多个代码质量问题：
1.  **未使用的导入**: `subprocess`, `pathlib.Path`, `pytest` 被导入但未在代码中使用。
2.  **重复定义**: `CliRunner` 被导入了两次。
3.  **导入排序**: 导入块未格式化。

### 用户需求
清理 `tests/` 目录下的代码，移除未使用的导入，修复重复定义，并整理导入顺序，以通过 CI 的 lint 检查。

### 评论
这是一个常规的代码清理任务 (`chore`/`fix`)，有助于保持测试代码的整洁和可维护性，避免误导开发者。

### 目标
1.  清理 `tests/integration/conftest.py` 中的未使用导入。
2.  清理并重组 `tests/integration/test_sync_workflow.py` 中的导入块。

### 基本原理
根据 `ruff` 的报告精确删除多余代码。不涉及逻辑变更。

### 标签
#intent/fix #intent/tune #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/linter #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 清理 `tests/integration/conftest.py`

移除未使用的 `subprocess` 和 `pathlib.Path`。

~~~~~act
patch_file
tests/integration/conftest.py
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest

from .helpers import run_git_command
~~~~~
~~~~~python
import pytest

from .helpers import run_git_command
~~~~~

#### Acts 2: 清理 `tests/integration/test_sync_workflow.py`

移除未使用的 `sqlite3` (虽然 ruff 没报这个，但根据上下文检查它似乎被用到了 `conn = sqlite3.connect`，所以保留), `subprocess`, `Path`, `pytest`。移除重复的 `CliRunner`。整理导入顺序。

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python
import sqlite3
import subprocess
from pathlib import Path

import pytest
import yaml
from pyquipu.cli.main import app
from pyquipu.common.identity import get_user_id_from_email
from typer.testing import CliRunner

from typer.testing import CliRunner

from .helpers import run_git_command

runner = CliRunner()
~~~~~
~~~~~python
import sqlite3

import yaml
from pyquipu.cli.main import app
from pyquipu.common.identity import get_user_id_from_email
from typer.testing import CliRunner

from .helpers import run_git_command

runner = CliRunner()
~~~~~

### 下一步建议
- 运行 `ruff check tests/` 验证修复结果。
- 如果涉及逻辑变更或重构，考虑运行相关测试用例确保无回归。
