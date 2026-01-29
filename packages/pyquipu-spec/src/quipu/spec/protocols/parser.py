from typing import Protocol, List, runtime_checkable
from .runtime import Statement


@runtime_checkable
class PlanParser(Protocol):
    def parse(self, text: str) -> List[Statement]: ...
