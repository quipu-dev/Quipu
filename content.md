# fix-test 修复 Acts 迁移后的导入路径

## 目标
修复 `acts` 目录迁移到 `quipu-runtime` 包后，测试文件和 CLI 入口中因引用旧路径而导致的 `ModuleNotFoundError`。

## 基本原理
上一阶段将 `acts/` 移动到了 `packages/quipu-runtime/src/quipu/acts/`。现有的测试代码仍试图从根目录的 `acts` 模块导入，导致 pytest 失败。同时，CLI 的 `--list-acts` 功能也依赖旧目录结构，需要一并更新为从包中导入。

## 标签
#fix #test #cli

---

## Script

### Act 1: 修复测试配置 (conftest.py)

更新 `conftest.py` 中的导入路径，从 `quipu.acts.basic` 导入注册函数。

~~~~~act
replace tests/conftest.py
~~~~~

~~~~~python
from pathlib import Path
from typing import TYPE_CHECKING
from acts.basic import register as register_basic_acts

# 使用 TYPE_CHECKING 块来辅助静态分析工具，而不在运行时导入
~~~~~

~~~~~python
from pathlib import Path
from typing import TYPE_CHECKING
from quipu.acts.basic import register as register_basic_acts

# 使用 TYPE_CHECKING 块来辅助静态分析工具，而不在运行时导入
~~~~~

### Act 2: 修复 Check 测试

更新 `tests/test_check.py` 的导入路径。

~~~~~act
replace tests/test_check.py
~~~~~

~~~~~python
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.exceptions import ExecutionError
from acts.check import register as register_check_acts
from quipu.core.types import ActContext
~~~~~

~~~~~python
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.exceptions import ExecutionError
from quipu.acts.check import register as register_check_acts
from quipu.core.types import ActContext
~~~~~

### Act 3: 修复 Git 测试

更新 `tests/test_git.py` 的导入路径。

~~~~~act
replace tests/test_git.py
~~~~~

~~~~~python
from pathlib import Path
from quipu.core.executor import Executor
from acts.git import register as register_git_acts

@pytest.mark.skipif(not shutil.which("git"), reason="Git 命令未找到，跳过 Git 测试")
~~~~~

~~~~~python
from pathlib import Path
from quipu.core.executor import Executor
from quipu.acts.git import register as register_git_acts

@pytest.mark.skipif(not shutil.which("git"), reason="Git 命令未找到，跳过 Git 测试")
~~~~~

### Act 4: 修复 Read 测试

更新 `tests/test_read.py` 的导入路径。

~~~~~act
replace tests/test_read.py
~~~~~

~~~~~python
import logging
from pathlib import Path
from quipu.core.executor import Executor, ExecutionError
from acts.read import register as register_read_acts
from quipu.core.types import ActContext
~~~~~

~~~~~python
import logging
from pathlib import Path
from quipu.core.executor import Executor, ExecutionError
from quipu.acts.read import register as register_read_acts
from quipu.core.types import ActContext
~~~~~

### Act 5: 修复集成测试

更新 `tests/test_integration_v2.py` 的导入路径。

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
from quipu.cli.main import app
from quipu.core.executor import Executor
from acts.basic import register as register_basic

# --- Fixtures ---
~~~~~

~~~~~python
from quipu.cli.main import app
from quipu.core.executor import Executor
from quipu.acts.basic import register as register_basic

# --- Fixtures ---
~~~~~

### Act 6: 修复 CLI 列表功能

更新 `packages/quipu-cli/src/quipu/cli/main.py`，使其使用 `register_core_acts` 来列出指令，而不是扫描已删除的 `acts` 目录。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~python
    setup_logging()
    if list_acts:
        executor = Executor(root_dir=Path("."), yolo=True)
        load_plugins(executor, PROJECT_ROOT / "acts")
        typer.secho("\n📋 可用的 Axon 指令列表:\n", fg=typer.colors.GREEN, bold=True, err=True)
        acts = executor.get_registered_acts()
~~~~~

~~~~~python
    setup_logging()
    if list_acts:
        executor = Executor(root_dir=Path("."), yolo=True)
        from quipu.acts import register_core_acts
        register_core_acts(executor)
        typer.secho("\n📋 可用的 Axon 指令列表:\n", fg=typer.colors.GREEN, bold=True, err=True)
        acts = executor.get_registered_acts()
~~~~~