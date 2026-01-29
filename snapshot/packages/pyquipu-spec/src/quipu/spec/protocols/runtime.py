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