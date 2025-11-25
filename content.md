# refactor (Phase 1.2) 界定引擎层

## 目标
完成 Quipu 重构的第一阶段第二步：界定引擎层 (Engine Definition)。
标识并隔离负责“状态”与“历史”的模块，重命名为 `eng_*.py`，并更新所有相关的导入路径。

## 基本原理
Engine 层的核心职责是状态管理 (State Machine)、历史记录 (History) 和 Git 操作 (GitDB)。
通过将 `core/git_db.py`, `core/history.py`, `core/engine.py`, `core/config_manager.py` 重命名为 `eng_*.py`，我们明确了这些模块属于 Engine 层的边界。这不仅是为了物理拆分做准备，也是为了强制检查这些模块是否包含对 Runtime 层（如 Executor）的非法依赖。

## 标签
 #refactor #core #engine

---

## Script

### Act 1: 重命名引擎层文件

将负责状态和历史的核心文件添加 `eng_` 前缀。

~~~~~act
move_file core/git_db.py core/eng_git_db.py
~~~~~

~~~~~act
move_file core/history.py core/eng_history.py
~~~~~

~~~~~act
move_file core/engine.py core/eng_state_machine.py
~~~~~

~~~~~act
move_file core/config_manager.py core/eng_config.py
~~~~~

### Act 2: 更新 eng_state_machine.py 内部引用

`core/eng_state_machine.py` (原 `engine.py`) 引用了 `git_db` 和 `history`，需要更新为新的文件名。

~~~~~act
replace core/eng_state_machine.py
~~~~~

~~~~~python
from .git_db import GitDB
from .history import load_history_graph
~~~~~

~~~~~python
from .eng_git_db import GitDB
from .eng_history import load_history_graph
~~~~~

### Act 3: 更新 Controller 中的引用

`core/controller.py` 引用了 `engine` 模块。

~~~~~act
replace core/controller.py
~~~~~

~~~~~python
from .engine import Engine
~~~~~

~~~~~python
from .eng_state_machine import Engine
~~~~~

### Act 4: 更新 Main.py 中的引用

`main.py` 引用了 `engine`, `history`, `config_manager`。需要一次性更新多处。

~~~~~act
replace main.py
~~~~~

~~~~~python
from core.engine import Engine
from core.history import load_history_graph
~~~~~

~~~~~python
from core.eng_state_machine import Engine
from core.eng_history import load_history_graph
~~~~~

~~~~~act
replace main.py
~~~~~

~~~~~python
from core.config_manager import ConfigManager
~~~~~

~~~~~python
from core.eng_config import ConfigManager
~~~~~

> **注意**: `main.py` 中的 `ui` 命令函数内部还有延迟导入。

~~~~~act
replace main.py
~~~~~

~~~~~python
    from core.history import load_all_history_nodes, load_history_graph
~~~~~

~~~~~python
    from core.eng_history import load_all_history_nodes, load_history_graph
~~~~~

### Act 5: 更新测试文件中的引用

更新所有测试文件以匹配新的引擎层文件名。

**Tests: test_engine.py**

~~~~~act
replace tests/test_engine.py
~~~~~

~~~~~python
from core.engine import Engine
from core.git_db import GitDB
from core.history import load_history_graph
~~~~~

~~~~~python
from core.eng_state_machine import Engine
from core.eng_git_db import GitDB
from core.eng_history import load_history_graph
~~~~~

**Tests: test_git_db.py**

~~~~~act
replace tests/test_git_db.py
~~~~~

~~~~~python
from core.git_db import GitDB
~~~~~

~~~~~python
from core.eng_git_db import GitDB
~~~~~

**Tests: test_graph_loader.py**

~~~~~act
replace tests/test_graph_loader.py
~~~~~

~~~~~python
from core.history import load_history_graph
~~~~~

~~~~~python
from core.eng_history import load_history_graph
~~~~~

**Tests: test_head_and_root.py**

~~~~~act
replace tests/test_head_and_root.py
~~~~~

~~~~~python
from core.engine import Engine
~~~~~

~~~~~python
from core.eng_state_machine import Engine
~~~~~

**Tests: test_idempotent_node.py**

~~~~~act
replace tests/test_idempotent_node.py
~~~~~

~~~~~python
from core.engine import Engine
~~~~~

~~~~~python
from core.eng_state_machine import Engine
~~~~~