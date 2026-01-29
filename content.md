好的，我们现在开始执行路线图的第三阶段：**协议化改革 (Protocolization)**。

这一阶段的核心是将抽象基类（ABC）转换为结构化类型（Protocol），并解耦运行时上下文，从而建立一个更灵活、更松耦合的类型系统。

我将生成一个计划来执行这些修改。

## [WIP] refactor: 将接口转换为 Protocol 并解耦运行时上下文

### 用户需求

根据“Quipu 架构重构路线图”，实施第三阶段“协议化改革”。这包括将 `spec` 包中的 `ABC` 替换为 `Protocol`，并重构 `ActContext` 以消除对具体实现的依赖。

### 评论

这是迈向现代化 Python 架构的关键一步。通过拥抱 `Protocol`（即结构化类型），我们可以在不强制修改实现类继承关系的情况下定义行为契约。这不仅使代码更清晰，也极大地提升了系统的可测试性和模块化程度。

### 目标

1.  将 `storage.py` 中的 `HistoryReader` 和 `HistoryWriter` 从 `ABC` 转换为 `Protocol`。
2.  移除 `engine` 包中相应实现类的显式继承关系。
3.  在 `runtime.py` 中定义 `ExecutorProtocol`，并使 `ActContext` 依赖此协议。
4.  将 `Statement` 类型定义从 `models/execution.py` 移动到 `protocols/runtime.py`，以实现更好的逻辑内聚。
5.  更新所有受影响模块的导入路径，确保类型系统的一致性。

### 基本原理

*   **解耦规范与实现**: 使用 `Protocol` 可以将“它应该做什么”（规范）与“它是什么”（实现）完全分开。`engine` 包的存储实现类不再需要知道 `spec` 包中的基类，只要它们的方法签名匹配契约即可。
*   **依赖倒置**: `ActContext` 之前概念上依赖于 `Executor` 的具体实现。通过引入 `ExecutorProtocol`，我们将依赖关系倒置为 `ActContext -> ExecutorProtocol <- Executor`。这消除了潜在的循环依赖风险，并为测试 `Act` 插件提供了清晰、稳定的 Mock 目标。
*   **逻辑内聚**: `Statement` 类型是运行时解析和执行的基本单元，将其与 `ActContext`、`ActFunction` 等运行时协议放在一起，可以提高 `spec` 包内部的逻辑一致性。

### 标签

#intent/refine #flow/ready #priority/high #comp/spec #comp/engine #comp/runtime #scope/api #scope/dx #ai/instruct #task/domain/architecture #task/object/type-system #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 协议化 Storage 接口

首先，我们将 `storage.py` 中的 `HistoryReader` 和 `HistoryWriter` 从 ABC 转换为 Protocol。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/storage.py
~~~~~
~~~~~python
from typing import Protocol, List, Dict, Optional, Set, Any, runtime_checkable
from ..models.graph import QuipuNode


@runtime_checkable
class HistoryReader(Protocol):
    """定义从存储后端读取历史图谱的行为契约"""

    def load_all_nodes(self) -> List[QuipuNode]: ...
    def get_node_content(self, node: QuipuNode) -> str: ...
    def get_node_blobs(self, commit_hash: str) -> Dict[str, bytes]: ...
    def find_nodes(
        self, summary_regex: Optional[str] = None, node_type: Optional[str] = None, limit: int = 10
    ) -> List[QuipuNode]: ...
    def get_node_count(self) -> int: ...
    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]: ...
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]: ...
    def get_private_data(self, node_commit_hash: str) -> Optional[str]: ...
    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]: ...
    def get_node_position(self, output_tree_hash: str) -> int: ...


@runtime_checkable
class HistoryWriter(Protocol):
    """定义向历史存储后端写入新节点的行为契约"""

    def create_node(
        self, node_type: str, input_tree: str, output_tree: str, content: str, **kwargs: Any
    ) -> QuipuNode: ...
~~~~~

#### Acts 2: 移除实现类的显式继承

现在，我们移除 `GitObject...` 和 `SQLite...` 实现类对 `HistoryReader` / `HistoryWriter` 的显式继承。它们将通过结构化类型隐式地满足协议。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
class GitObjectHistoryReader(HistoryReader):
~~~~~
~~~~~python.new
class GitObjectHistoryReader:
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
class GitObjectHistoryWriter(HistoryWriter):
~~~~~
~~~~~python.new
class GitObjectHistoryWriter:
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
class SQLiteHistoryReader(HistoryReader):
~~~~~
~~~~~python.new
class SQLiteHistoryReader:
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
class SQLiteHistoryWriter(HistoryWriter):
~~~~~
~~~~~python.new
class SQLiteHistoryWriter:
~~~~~

#### Acts 3: 解耦 Runtime Context 并整合类型定义

接下来，我们重构 `runtime.py`，定义 `ExecutorProtocol`，让 `ActContext` 依赖于它，并把 `Statement` 类型移到这里。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/runtime.py
~~~~~
~~~~~python
from __future__ import annotations
from pathlib import Path
from typing import Protocol, List, Callable, runtime_checkable, TypedDict
from ..exceptions import ExecutionError


@runtime_checkable
class ExecutorProtocol(Protocol):
    """定义执行器的核心能力契约"""

    @property
    def root_dir(self) -> Path: ...
    def resolve_path(self, rel_path: str) -> Path: ...
    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> bool: ...


class ActContext:
    """提供给插件函数的上下文 API。

    它是插件与 ExecutorProtocol 之间的稳定接口。
    """

    def __init__(self, executor: ExecutorProtocol):
        self._executor = executor

    @property
    def root_dir(self) -> Path:
        return self._executor.root_dir

    def resolve_path(self, rel_path: str) -> Path:
        return self._executor.resolve_path(rel_path)

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> bool:
        return self._executor.request_confirmation(file_path, old_content, new_content)

    def fail(self, message: str):
        raise ExecutionError(message)


# --- Runtime Type Definitions ---


class Statement(TypedDict):
    """表示解析后的单个操作语句"""

    act: str
    contexts: List[str]


# Act 函数签名定义: (context, args) -> None
ActFunction = Callable[[ActContext, List[str]], None]

# Summarizer 函数签名定义: (args, context_blocks) -> str
Summarizer = Callable[[List[str], List[str]], str]
~~~~~

#### Acts 4: 清理并更新导入路径

最后，我们从 `execution.py` 中移除 `Statement` 的旧定义，并更新 `executor.py` 和 `parser.py` 的导入路径以指向新位置。

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/models/execution.py
~~~~~
~~~~~python.old
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, TypedDict


@dataclass
class QuipuResult:
    """Quipu 业务逻辑执行结果的标准容器"""

    success: bool
    exit_code: int
    message: str = ""
    data: Any = None
    error: Optional[Exception] = None
    msg_kwargs: Dict[str, Any] = field(default_factory=dict)


class Statement(TypedDict):
    """表示解析后的单个操作语句"""

    act: str
    contexts: List[str]
~~~~~
~~~~~python.new
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class QuipuResult:
    """Quipu 业务逻辑执行结果的标准容器"""

    success: bool
    exit_code: int
    message: str = ""
    data: Any = None
    error: Optional[Exception] = None
    msg_kwargs: Dict[str, Any] = field(default_factory=dict)
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/executor.py
~~~~~
~~~~~python.old
from quipu.spec.exceptions import ExecutionError, OperationCancelledError
from quipu.spec.protocols.runtime import ActContext, ActFunction
from quipu.spec.models.execution import Statement
~~~~~
~~~~~python.new
from quipu.bus import bus
from quipu.spec.exceptions import ExecutionError, OperationCancelledError
from quipu.spec.protocols.runtime import ActContext, ActFunction, Statement
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
from typing import List, Optional

from quipu.spec.models.execution import Statement
~~~~~
~~~~~python.new
from typing import List, Optional

from quipu.spec.protocols.runtime import Statement
~~~~~

### 下一步建议

我们已经完成了协议化改革。现在，我建议执行一次 `pytest` 来验证这些重构没有破坏任何现有功能。

确认测试通过后，我们可以继续执行路线图的**第四阶段：统一与收敛 (Unification)**，将散落在各处的其他协议（如 `Renderer` 和 `PlanParser`）也收归到 `spec` 包中，从而最终确立其作为“单一事实来源”的地位。
