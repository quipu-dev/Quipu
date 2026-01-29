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
    content: str = ""
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
