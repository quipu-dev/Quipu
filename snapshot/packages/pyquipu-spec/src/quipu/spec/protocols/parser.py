from typing import Protocol, List, runtime_checkable
from .runtime import Statement


@runtime_checkable
class PlanParser(Protocol):
    """定义 Plan 文件解析器的行为契约"""

    def parse(self, text: str) -> List[Statement]: ...