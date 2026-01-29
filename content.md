根据重构路线图，我们将开始执行**阶段一：基础设施构建与骨架搭建**。

我们将创建 `packages/pyquipu-spec` 包，并将原 `interfaces` 中的内容按照新的逻辑结构（Models 与 Protocols 分离，ABC 转换为 Protocol）进行填充。

## [WIP] feat: 创建 pyquipu-spec 包并定义核心协议骨架

### 用户需求
取消 `pyquipu-interfaces` 包，创建一个全新的 `pyquipu-spec` 包作为系统宪法，采用 `typing.Protocol` 替代 `abc.ABC`，并建立更严谨的目录结构。

### 评论
这是架构演进的关键一步。通过将接口（Interface）升级为规范（Spec），并利用 Python 的结构化类型（Protocols），我们增强了系统的解耦能力，特别是在消除循环依赖和优化测试 Mock 方面具有重要意义。

### 目标
1.  创建 `pyquipu-spec` 的物理目录结构。
2.  定义 `pyproject.toml` 构建配置。
3.  将原 `interfaces` 中的异常、模型和存储定义迁移并重构为 Protocol 形式。
4.  在 `spec` 中新增 `ExecutorProtocol` 以解耦运行时上下文。

### 基本原理
按照“先搭建骨架”的原则，我们直接在 `spec` 下建立 `models/` 和 `protocols/` 子包。
- `models/` 存放纯粹的数据结构（DataClasses）。
- `protocols/` 存放行为契约（Protocols）。
- 所有的 `abc.ABC` 继承和 `@abstractmethod` 装饰器都被移除，转而使用 `typing.Protocol`。

### 标签
#intent/architect #flow/ready #priority/high 
#comp/interfaces #comp/build #scope/core 
#ai/brainstorm
#task/domain/architecture #task/object/spec-package #task/action/initialization #task/state/begin

---

### Script

#### Acts 1: 创建目录结构

首先，我们在 `packages` 目录下建立 `pyquipu-spec` 的完整层级。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/pyquipu-spec/src/quipu/spec/models packages/pyquipu-spec/src/quipu/spec/protocols
touch packages/pyquipu-spec/src/quipu/spec/__init__.py
touch packages/pyquipu-spec/src/quipu/spec/models/__init__.py
touch packages/pyquipu-spec/src/quipu/spec/protocols/__init__.py
~~~~~

#### Acts 2: 建立构建配置与常量

创建 `pyproject.toml` 并定义核心常量文件。

~~~~~act
write_file
packages/pyquipu-spec/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-spec"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The constitutional specifications and protocols for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]

dependencies = []

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/constants.py
~~~~~
~~~~~python
# Quipu 系统全局常量规范

# Git 空树的哈希值，作为所有历史图谱的绝对起点 (Genesis)
EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
~~~~~

#### Acts 3: 迁移异常与模型

将原有的异常类和数据模型迁移到新位置。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/exceptions.py
~~~~~
~~~~~python
class AIFSOpsError(Exception):
    """Quipu 生态系统的基础异常类"""
    pass


class ParseError(AIFSOpsError):
    """Markdown 或指令解析错误"""
    pass


class ExecutionError(AIFSOpsError):
    """Act 操作执行错误"""
    pass


class OperationCancelledError(ExecutionError):
    """当用户取消一个需要确认的操作时引发"""
    pass
~~~~~

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/models/graph.py
~~~~~
~~~~~python
from __future__ import annotations
import dataclasses
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclasses.dataclass
class QuipuNode:
    """表示 Quipu 历史图谱中的一个节点（DTO）"""
    commit_hash: str
    output_tree: str
    input_tree: str
    timestamp: datetime
    filename: Path
    node_type: str  # "plan" | "capture"
    summary: str = ""
    owner_id: Optional[str] = None

    # 图遍历字段（由加载器填充）
    parent: Optional[QuipuNode] = None
    children: List[QuipuNode] = dataclasses.field(default_factory=list)

    @property
    def short_hash(self) -> str:
        return self.output_tree[:7]

    @property
    def siblings(self) -> List[QuipuNode]:
        if not self.parent:
            return [self]
        return self.parent.children
~~~~~

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/models/execution.py
~~~~~
~~~~~python
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

#### Acts 4: 定义核心协议 (Protocols)

将 Storage 和 Runtime 的定义重构为 Protocols。

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
    def find_nodes(self, summary_regex: Optional[str] = None, node_type: Optional[str] = None, limit: int = 10) -> List[QuipuNode]: ...
    def get_node_count(self) -> int: ...
    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]: ...
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]: ...
    def get_private_data(self, node_commit_hash: str) -> Optional[str]: ...
    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]: ...
    def get_node_position(self, output_tree_hash: str) -> int: ...


@runtime_checkable
class HistoryWriter(Protocol):
    """定义向历史存储后端写入新节点的行为契约"""
    def create_node(self, node_type: str, input_tree: str, output_tree: str, content: str, **kwargs: Any) -> QuipuNode: ...
~~~~~

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/runtime.py
~~~~~
~~~~~python
from __future__ import annotations
from pathlib import Path
from typing import Protocol, List, Callable, runtime_checkable
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


# Act 函数签名定义: (context, args) -> None
ActFunction = Callable[[ActContext, List[str]], None]

# Summarizer 函数签名定义: (args, context_blocks) -> str
Summarizer = Callable[[List[str], List[str]], str]
~~~~~

### 下一步建议

1.  **执行批量替换**: 使用 `refactor_imports.py` 脚本（稍后提供）将整个项目中的 `quipu.interfaces` 引用更新为 `quipu.spec`。
2.  **更新项目依赖**: 修改根目录及各子包的 `pyproject.toml`，用 `pyquipu-spec` 替换 `pyquipu-interfaces`。
3.  **移除旧包**: 确认所有引用更新完毕且测试通过后，物理删除 `packages/pyquipu-interfaces`。
4.  **收拢 Protocol**: 接下来可以将 `Renderer` 和 `PlanParser` 的定义也提取到 `spec` 包中。
