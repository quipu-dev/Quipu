from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn, Protocol, TypedDict, runtime_checkable

from ..exceptions import ExecutionError


@runtime_checkable
class ExecutorProtocol(Protocol):
    @property
    def root_dir(self) -> Path: ...
    def resolve_path(self, rel_path: str) -> Path: ...
    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> None: ...
    def register(self, name: str, func: ActFunction, arg_mode: str = "hybrid", summarizer: Any = None) -> None: ...


class ActContext:
    def __init__(self, executor: ExecutorProtocol):
        self._executor = executor

    @property
    def root_dir(self) -> Path:
        return self._executor.root_dir

    def resolve_path(self, rel_path: str) -> Path:
        return self._executor.resolve_path(rel_path)

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str) -> None:
        return self._executor.request_confirmation(file_path, old_content, new_content)

    def data(self, data_string: str) -> None:
        if hasattr(self._executor, "output_data"):
            self._executor.output_data(data_string)
        else:
            import sys

            sys.stdout.write(data_string + ("\n" if not data_string.endswith("\n") else ""))

    def fail(self, message: str) -> NoReturn:
        raise ExecutionError(message)


# --- Runtime Type Definitions ---


class Statement(TypedDict):
    act: str
    contexts: list[str]


# Act 函数签名定义: (context, args) -> None
ActFunction = Callable[[ActContext, list[str]], None]

# Summarizer 函数签名定义: (args, context_blocks) -> str
Summarizer = Callable[[list[str], list[str]], str]
