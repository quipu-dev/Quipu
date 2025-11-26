from typing import List, Optional, Set

from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader


class GraphViewModel:
    """
    一个 ViewModel，用于解耦 TUI (View) 和 HistoryReader (Model)。

    它负责管理分页加载状态、缓存可达性数据，并为 UI 提供简洁的数据接口。
    """

    def __init__(self, reader: HistoryReader, current_hash: Optional[str]):
        self.reader = reader
        self.current_hash = current_hash
        self.loaded_nodes: List[QuipuNode] = []
        self.ancestor_set: Set[str] = set()
        self.total_count: int = 0
        self.offset: int = 0

    def initialize(self):
        """
        初始化 ViewModel，获取总数并计算可达性缓存。
        这是一个快速操作，因为它不加载任何节点内容。
        """
        self.total_count = self.reader.get_node_count()
        if self.current_hash:
            # 后端直接计算祖先，避免在前端加载整个图谱
            self.ancestor_set = self.reader.get_ancestor_hashes(self.current_hash)
            # 当前节点本身也是可达的
            self.ancestor_set.add(self.current_hash)

    def is_reachable(self, node_hash: str) -> bool:
        """检查一个节点哈希是否在可达性集合中。"""
        if not self.current_hash:
            # 如果没有当前状态 (例如，在创世之前)，将所有内容视为可达，
            # 以避免 UI 显示全灰色。
            return True
        return node_hash in self.ancestor_set

    def has_more_data(self) -> bool:
        """检查是否还有更多数据可以从后端加载。"""
        if self.total_count == 0:
            return False
        return self.offset < self.total_count

    def load_next_page(self, size: int = 50) -> List[QuipuNode]:
        """
        加载下一页数据，更新内部状态，并返回新加载的节点列表。
        """
        if not self.has_more_data():
            return []

        new_nodes = self.reader.load_nodes_paginated(limit=size, offset=self.offset)
        self.loaded_nodes.extend(new_nodes)
        self.offset += len(new_nodes)
        return new_nodes

    def get_content_bundle(self, node: QuipuNode) -> str:
        """
        获取节点的公共内容和私有内容，并将它们格式化成一个单一的字符串用于展示。
        """
        public_content = self.reader.get_node_content(node) or ""
        private_content = self.reader.get_private_data(node.filename.name)

        if not public_content and not private_content:
            return "*此节点无详细内容*"

        # 构建最终的显示内容
        bundle = []
        if public_content:
            bundle.append("== 📜 公共计划内容=========")
            bundle.append(public_content.strip())

        if private_content is not None:
            if public_content:
                bundle.append("\n---\n")
            bundle.append("== 🧠 开发者意图===========")
            bundle.append(private_content.strip())
        elif public_content:
            # 仅当有公共内容时，才显示“无私有数据”的消息
            bundle.append("\n---\n")
            bundle.append("== 🧠 开发者意图===========")
            bundle.append("*此节点无私有数据或来自协作者*")

        return "\n\n".join(bundle)