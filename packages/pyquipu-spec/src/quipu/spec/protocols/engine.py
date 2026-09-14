from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..models.graph import QuipuNode
from .storage import GraphIndex, HistoryReader, HistoryWriter, SnapshotStorage


@runtime_checkable
class QuipuEngine(Protocol):
    root_dir: Path
    history_graph: dict[str, QuipuNode]
    current_node: QuipuNode | None

    # 新架构属性
    storage: SnapshotStorage | Any
    index: GraphIndex | Any

    # 兼容过渡属性
    reader: HistoryReader | Any
    writer: HistoryWriter | Any
    git_db: Any

    def align(self) -> str: ...
    def visit(self, target_hash: str) -> None: ...
    def capture_drift(self, current_hash: str, message: str | None = None) -> QuipuNode: ...
    def create_plan_node(
        self, input_tree: str, output_tree: str, plan_content: str, summary_override: str | None = None
    ) -> QuipuNode: ...
    def checkout(self, target_hash: str) -> None: ...
    def back(self) -> str | None: ...
    def forward(self) -> str | None: ...
    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]: ...
    def close(self) -> None: ...
