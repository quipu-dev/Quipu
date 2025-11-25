# refactor: 修正所有 Python 文件的导入路径

## 目标
修正因文件物理迁移导致的导入路径错误。将所有旧的 `core.*` 引用更新为新的 `quipu.*` 命名空间引用，并确保包内引用使用相对路径，跨包引用使用绝对路径。

## 基本原理
在物理拆分后，代码库的拓扑结构发生了变化。为了让 Python 解释器正确找到模块，我们需要更新所有的 `import` 语句。
*   **Interfaces**: 处于 `quipu.core` 命名空间。
*   **Engine**: 处于 `quipu.core` 命名空间，依赖 Interfaces。
*   **Runtime**: 处于 `quipu.core` 命名空间，依赖 Interfaces。
*   **CLI**: 处于 `quipu.cli` 命名空间，依赖上述所有。

## 标签
修正导入路径。 #refactor #fix #imports

---

## Script

### Act 1: 修正 quipu-interfaces 和 quipu-engine

修正基础包的内部引用和跨包引用。

~~~~~act
replace packages/quipu-interfaces/src/quipu/core/types.py
~~~~~
~~~~~python
from .intf_exceptions import ExecutionError

# --- Forward declaration to avoid circular imports ---
# The real Executor class is in core.executor
~~~~~
~~~~~python
from .exceptions import ExecutionError

# --- Forward declaration to avoid circular imports ---
# The real Executor class is in quipu.core.executor
~~~~~

~~~~~act
replace packages/quipu-engine/src/quipu/core/git_db.py
~~~~~
~~~~~python
from typing import Optional, Dict
from contextlib import contextmanager
from .intf_exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
from typing import Optional, Dict
from contextlib import contextmanager
from quipu.core.exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace packages/quipu-engine/src/quipu/core/history.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict, Optional, List
import yaml
from .intf_models import AxonNode
from datetime import datetime
~~~~~
~~~~~python
from pathlib import Path
from typing import Dict, Optional, List
import yaml
from quipu.core.models import AxonNode
from datetime import datetime
~~~~~

~~~~~act
replace packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~
~~~~~python
from datetime import datetime

from .eng_git_db import GitDB
from .eng_history import load_history_graph
from .intf_models import AxonNode

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
from datetime import datetime

from .git_db import GitDB
from .history import load_history_graph
from quipu.core.models import AxonNode

logger = logging.getLogger(__name__)
~~~~~

### Act 2: 修正 quipu-runtime

修正运行时包的引用。

~~~~~act
replace packages/quipu-runtime/src/quipu/core/executor.py
~~~~~
~~~~~python
import shlex
import sys
from pathlib import Path
from typing import Dict, List, Any
from .intf_types import Statement, ActFunction, ActContext
from .intf_exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import shlex
import sys
from pathlib import Path
from typing import Dict, List, Any
from quipu.core.types import Statement, ActFunction, ActContext
from quipu.core.exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/parser.py
~~~~~
~~~~~python
import re
from abc import ABC, abstractmethod
from typing import List, Type
from .intf_types import Statement

class BaseParser(ABC):
~~~~~
~~~~~python
import re
from abc import ABC, abstractmethod
from typing import List, Type
from quipu.core.types import Statement

class BaseParser(ABC):
~~~~~

~~~~~act
replace packages/quipu-runtime/src/quipu/core/plugin_loader.py
~~~~~
~~~~~python
import logging
import sys
from pathlib import Path
from .rt_executor import Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import logging
import sys
from pathlib import Path
from .executor import Executor

logger = logging.getLogger(__name__)
~~~~~

### Act 3: 修正 quipu-cli

修正 CLI 包的引用，包括主入口、控制器和配置。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/logger_config.py
~~~~~
~~~~~python
import logging
import sys
from config import LOG_LEVEL

def setup_logging():
~~~~~
~~~~~python
import logging
import sys
from .config import LOG_LEVEL

def setup_logging():
~~~~~

~~~~~act
replace packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional

from .intf_result import AxonResult
from .eng_state_machine import Engine
from .rt_executor import Executor, ExecutionError
from .intf_exceptions import ExecutionError as CoreExecutionError # Alias to avoid conflict
from .rt_parser import get_parser, detect_best_parser
from .rt_plugin_loader import load_plugins

# 从配置导入，注意为了解耦，未来可能需要将 config 注入而不是直接导入
from config import PROJECT_ROOT

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional

from quipu.core.result import AxonResult
from quipu.core.state_machine import Engine
from quipu.core.executor import Executor, ExecutionError
from quipu.core.exceptions import ExecutionError as CoreExecutionError
from quipu.core.parser import get_parser, detect_best_parser
from quipu.core.plugin_loader import load_plugins

# 从配置导入，注意为了解耦，未来可能需要将 config 注入而不是直接导入
from .config import PROJECT_ROOT

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated, Optional, Dict

from logger_config import setup_logging
from core.cli_controller import run_axon, find_project_root
from config import DEFAULT_WORK_DIR, DEFAULT_ENTRY_FILE, PROJECT_ROOT
from core.rt_plugin_loader import load_plugins
from core.rt_executor import Executor
from core.eng_state_machine import Engine
from core.eng_history import load_history_graph
from core.intf_models import AxonNode
import inspect
import subprocess
from core.eng_config import ConfigManager
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated, Optional, Dict

from .logger_config import setup_logging
from .controller import run_axon, find_project_root
from .config import DEFAULT_WORK_DIR, DEFAULT_ENTRY_FILE, PROJECT_ROOT
from quipu.core.plugin_loader import load_plugins
from quipu.core.executor import Executor
from quipu.core.state_machine import Engine
from quipu.core.history import load_history_graph
from quipu.core.models import AxonNode
import inspect
import subprocess
from quipu.core.config import ConfigManager
~~~~~

### Act 4: 修正 Acts 插件

修正根目录下 `acts/` 目录中的所有插件文件。

~~~~~act
replace acts/basic.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import List
import logging
from core.intf_types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import List
import logging
from quipu.core.types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/check.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import List
import logging
from core.intf_types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import List
import logging
from quipu.core.types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/git.py
~~~~~
~~~~~python
import subprocess
import logging
import os
from typing import List
from core.intf_types import ActContext, Executor
from core.intf_exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import subprocess
import logging
import os
from typing import List
from quipu.core.types import ActContext, Executor
from quipu.core.exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/memory.py
~~~~~
~~~~~python
import logging
from typing import List
from datetime import datetime
from core.intf_types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import logging
from typing import List
from datetime import datetime
from quipu.core.types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/read.py
~~~~~
~~~~~python
import argparse
from pathlib import Path
from typing import List
import logging
from core.intf_types import ActContext, Executor
from core.intf_exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import argparse
from pathlib import Path
from typing import List
import logging
from quipu.core.types import ActContext, Executor
from quipu.core.exceptions import ExecutionError

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/refactor.py
~~~~~
~~~~~python
import shutil
from typing import List
import logging
from core.intf_types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import shutil
from typing import List
import logging
from quipu.core.types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~

~~~~~act
replace acts/shell.py
~~~~~
~~~~~python
import subprocess
import logging
from typing import List
from core.intf_types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~
~~~~~python
import subprocess
import logging
from typing import List
from quipu.core.types import ActContext, Executor

logger = logging.getLogger(__name__)
~~~~~

### Act 5: 修正 Tests

修正测试用例中的导入路径。

~~~~~act
replace tests/conftest.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from core.rt_executor import Executor
from acts.basic import register as register_basic_acts
~~~~~
~~~~~python
import pytest
from pathlib import Path
from quipu.core.executor import Executor
from acts.basic import register as register_basic_acts
~~~~~

~~~~~act
replace tests/test_arg_strategy.py
~~~~~
~~~~~python
import pytest
from core.rt_executor import Executor

class TestArgStrategy:
~~~~~
~~~~~python
import pytest
from quipu.core.executor import Executor

class TestArgStrategy:
~~~~~

~~~~~act
replace tests/test_auto_detect.py
~~~~~
~~~~~python
from core.rt_parser import detect_best_parser

class TestAutoDetect:
~~~~~
~~~~~python
from quipu.core.parser import detect_best_parser

class TestAutoDetect:
~~~~~

~~~~~act
replace tests/test_check.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from core.rt_executor import Executor, ExecutionError
from acts.check import register as register_check_acts
from core.intf_types import ActContext
~~~~~
~~~~~python
import pytest
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.exceptions import ExecutionError
from acts.check import register as register_check_acts
from quipu.core.types import ActContext
~~~~~

~~~~~act
replace tests/test_engine.py
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from core.eng_state_machine import Engine
from core.eng_git_db import GitDB
from core.eng_history import load_history_graph

@pytest.fixture
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from quipu.core.state_machine import Engine
from quipu.core.git_db import GitDB
from quipu.core.history import load_history_graph

@pytest.fixture
~~~~~

~~~~~act
replace tests/test_git.py
~~~~~
~~~~~python
import pytest
import subprocess
import shutil
from pathlib import Path
from core.rt_executor import Executor
from acts.git import register as register_git_acts
~~~~~
~~~~~python
import pytest
import subprocess
import shutil
from pathlib import Path
from quipu.core.executor import Executor
from acts.git import register as register_git_acts
~~~~~

~~~~~act
replace tests/test_git_db.py
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from core.eng_git_db import GitDB

@pytest.fixture
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from quipu.core.git_db import GitDB

@pytest.fixture
~~~~~

~~~~~act
replace tests/test_graph_loader.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from datetime import datetime
from core.eng_history import load_history_graph

@pytest.fixture
~~~~~
~~~~~python
import pytest
from pathlib import Path
from datetime import datetime
from quipu.core.history import load_history_graph

@pytest.fixture
~~~~~

~~~~~act
replace tests/test_head_and_root.py
~~~~~
~~~~~python
import pytest
import os
from pathlib import Path
from core.eng_state_machine import Engine
from core.cli_controller import find_project_root

class TestHeadTracking:
~~~~~
~~~~~python
import pytest
import os
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.controller import find_project_root

class TestHeadTracking:
~~~~~

~~~~~act
replace tests/test_idempotent_node.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from core.eng_state_machine import Engine
from core.cli_controller import run_axon

class TestIdempotentNode:
~~~~~
~~~~~python
import pytest
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.controller import run_axon

class TestIdempotentNode:
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~
~~~~~python
import logging
from pathlib import Path
from typer.testing import CliRunner
from core.cli_controller import run_axon, AxonResult
from main import app
from core.rt_executor import Executor
from acts.basic import register as register_basic
~~~~~
~~~~~python
import logging
from pathlib import Path
from typer.testing import CliRunner
from quipu.cli.controller import run_axon, AxonResult
from quipu.cli.main import app
from quipu.core.executor import Executor
from acts.basic import register as register_basic
~~~~~

~~~~~act
replace tests/test_ops.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from core.rt_parser import BacktickParser, TildeParser, get_parser
from core.rt_executor import Executor, ExecutionError
from core.intf_types import ActContext

class TestParser:
~~~~~
~~~~~python
import pytest
from pathlib import Path
from quipu.core.parser import BacktickParser, TildeParser, get_parser
from quipu.core.executor import Executor, ExecutionError
from quipu.core.types import ActContext

class TestParser:
~~~~~

~~~~~act
replace tests/test_plugins.py
~~~~~
~~~~~python
import sys
from pathlib import Path
from core.rt_executor import Executor
from core.rt_plugin_loader import load_plugins
from core.cli_controller import find_project_root  # 从 Controller 导入辅助函数

class TestPluginLoading:
~~~~~
~~~~~python
import sys
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins
from quipu.cli.controller import find_project_root  # 从 Controller 导入辅助函数

class TestPluginLoading:
~~~~~

~~~~~act
replace tests/test_read.py
~~~~~
~~~~~python
import logging
from pathlib import Path
from core.rt_executor import Executor, ExecutionError
from acts.read import register as register_read_acts
from core.intf_types import ActContext

class TestReadActs:
~~~~~
~~~~~python
import logging
from pathlib import Path
from quipu.core.executor import Executor, ExecutionError
from acts.read import register as register_read_acts
from quipu.core.types import ActContext

class TestReadActs:
~~~~~

~~~~~act
replace tests/test_root_invariance.py
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from core.cli_controller import run_axon

@pytest.fixture
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from quipu.cli.controller import run_axon

@pytest.fixture
~~~~~

~~~~~act
replace tests/test_ui_logic.py
~~~~~
~~~~~python
from ui.tui import AxonUiApp
from textual.widgets import DataTable

class TestUiLogic:
~~~~~
~~~~~python
from quipu.cli.tui import AxonUiApp
from textual.widgets import DataTable

class TestUiLogic:
~~~~~
> **注意**: 我注意到 `ui/tui.py` 还没有被处理。根据之前的步骤，`ui` 目录也应该被整合到 `quipu-cli` 中。虽然重构手册没有明确提到 `ui` 目录（它可能是在手册之后加的），但逻辑上它属于 CLI 的一部分。为了保证一致性，我将在下面的 Act 6 中处理它。

# fix: 修正剩余的 UI 相关导入路径错误

## 目标
继续完成之前的重构任务，修正 `test_ui_logic.py` 中因上下文不匹配导致失败的 Act，并完成后续 `ui` 模块的迁移和 `main.py` 的修正。

## 基本原理
上一步骤中，Act 33 已成功将 `ui.tui` 替换为 `quipu.cli.tui`，这改变了文件内容，导致紧随其后的 Act 34 因使用了旧的上下文而匹配失败。此外，Act 34 的旧数据本身也存在错误（引用了错误的文件内容）。本脚本将基于当前实际的文件状态进行修正，并完成剩余的迁移工作。

## 标签
修正导入路径。 #fix #refactor #ui

---

## Script

### Act 1: 修正 `tests/test_ui_logic.py`

基于 Act 33 执行后的新状态，修正 `AxonNode` 的导入路径。

~~~~~act
replace tests/test_ui_logic.py
~~~~~
~~~~~python
from datetime import datetime
from core.intf_models import AxonNode
from quipu.cli.tui import AxonUiApp
~~~~~
~~~~~python
from datetime import datetime
from quipu.core.models import AxonNode
from quipu.cli.tui import AxonUiApp
~~~~~

### Act 2: 修正 `tests/test_ui_reachability.py`

修正 `AxonNode` 和 `AxonUiApp` 的导入路径。

~~~~~act
replace tests/test_ui_reachability.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from datetime import datetime
from core.intf_models import AxonNode
from ui.tui import AxonUiApp

class TestUiReachability:
~~~~~
~~~~~python
import pytest
from pathlib import Path
from datetime import datetime
from quipu.core.models import AxonNode
from quipu.cli.tui import AxonUiApp

class TestUiReachability:
~~~~~

### Act 3: 迁移 `ui/tui.py` 到 CLI 包

将 `tui.py` 物理移动到 `quipu-cli` 包中。

~~~~~act
move_file ui/tui.py packages/quipu-cli/src/quipu/cli/tui.py
~~~~~

### Act 4: 修正 `packages/quipu-cli/src/quipu/cli/tui.py`

修正 `tui.py` 内部对 `AxonNode` 的导入路径。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
from textual.binding import Binding
from textual.coordinate import Coordinate

sys.path.append('..')
from core.intf_models import AxonNode

class AxonUiApp(App):
~~~~~
~~~~~python
from textual.binding import Binding
from textual.coordinate import Coordinate

from quipu.core.models import AxonNode

class AxonUiApp(App):
~~~~~

### Act 5: 修正 `main.py` 中的 TUI 导入

修正 `ui` 命令中对 `AxonUiApp` 的动态导入。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
    """
    try:
        from ui.tui import AxonUiApp
    except ImportError:
        typer.secho("❌ TUI 依赖 'textual' 未安装。", fg=typer.colors.RED, err=True)
~~~~~
~~~~~python
    """
    try:
        from .tui import AxonUiApp
    except ImportError:
        typer.secho("❌ TUI 依赖 'textual' 未安装。", fg=typer.colors.RED, err=True)
~~~~~

### Act 6: 修正 `main.py` 中的 History 导入

修正 `ui` 命令中对历史加载函数的导入。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
    # 2. 从哈希到最新节点的映射 (graph) -> 用于 checkout 查找
    from core.eng_history import load_all_history_nodes, load_history_graph
    
    real_root = _resolve_root(work_dir)
~~~~~
~~~~~python
    # 2. 从哈希到最新节点的映射 (graph) -> 用于 checkout 查找
    from quipu.core.history import load_all_history_nodes, load_history_graph
    
    real_root = _resolve_root(work_dir)
~~~~~