import math

from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader


class GraphViewModel:
    """
    一个 ViewModel, 用于解耦 TUI (View) 和 HistoryReader (Model)。

    它负责管理分页状态、缓存可达性数据，并为 UI 提供简洁的数据接口。
    """

    def __init__(self, reader: HistoryReader, current_output_tree_hash: str | None, page_size: int = 50):
        self.reader = reader
        self.current_output_tree_hash = current_output_tree_hash
        self.page_size = page_size

        # --- 核心状态 ---
        self.total_nodes: int = 0
        self.total_pages: int = 1
        self.current_page: int = 0

        # --- TUI 交互状态 ---
        self.show_unreachable: bool = True
        self.current_page_nodes: list[QuipuNode] = []
        self.current_selected_node: QuipuNode | None = None
        self._node_by_key: dict[str, QuipuNode] = {}
        self.reachable_set: set[str] = set()

    def initialize(self):
        """
        初始化 ViewModel, 获取总数并计算可达性缓存。
        这是一个快速操作，因为它不加载任何节点内容。
        """
        self.total_nodes = self.reader.get_node_count()
        if self.page_size > 0 and self.total_nodes > 0:
            self.total_pages = math.ceil(self.total_nodes / self.page_size)
        else:
            self.total_pages = 1

        if self.current_output_tree_hash:
            # 后端直接计算祖先和后代，避免在前端加载整个图谱
            ancestors = self.reader.get_ancestor_output_trees(self.current_output_tree_hash)
            descendants = self.reader.get_descendant_output_trees(self.current_output_tree_hash)

            # 合并祖先、后代和当前节点自身，形成完整的可达集合
            self.reachable_set = ancestors.union(descendants)
            self.reachable_set.add(self.current_output_tree_hash)

    def is_reachable(self, output_tree_hash: str) -> bool:
        """检查一个节点哈希是否在可达性集合中。"""
        if not self.current_output_tree_hash:
            # 如果没有当前状态 (例如，在创世之前)，将所有内容视为可达，
            # 以避免 UI 显示全灰色。
            return True
        return output_tree_hash in self.reachable_set

    def calculate_initial_page(self) -> int:
        """根据当前 HEAD 位置计算其所在的页码"""
        if not self.current_output_tree_hash:
            return 1

        position = self.reader.get_node_position(self.current_output_tree_hash)
        if position == -1:
            return 1

        # position 是从 0 开始的索引
        # e.g. pos 0 -> page 1; pos 49 -> page 1; pos 50 -> page 2
        return (position // self.page_size) + 1

    def load_page(self, page_number: int) -> list[QuipuNode]:
        """加载指定页码的数据，更新内部状态，并返回该页的节点列表。"""
        if not (1 <= page_number <= self.total_pages):
            self.current_page_nodes = []
            self._node_by_key = {}
            return []

        self.current_page = page_number
        offset = (self.current_page - 1) * self.page_size

        self.current_page_nodes = self.reader.load_nodes_paginated(limit=self.page_size, offset=offset)
        self._node_by_key = {str(node.filename): node for node in self.current_page_nodes}
        return self.current_page_nodes

    def set_head(self, node: QuipuNode):
        self.current_output_tree_hash = node.output_tree
        ancestors = self.reader.get_ancestor_output_trees(node.output_tree)
        descendants = self.reader.get_descendant_output_trees(node.output_tree)
        self.reachable_set = ancestors.union(descendants)
        self.reachable_set.add(node.output_tree)

    def toggle_unreachable(self):
        """切换是否显示不可达节点。"""
        self.show_unreachable = not self.show_unreachable

    def get_nodes_to_render(self) -> list[QuipuNode]:
        """根据当前可见性设置，返回需要渲染的节点列表。"""
        if self.show_unreachable:
            return self.current_page_nodes
        return [node for node in self.current_page_nodes if self.is_reachable(node.output_tree)]

    def select_node_by_key(self, key: str) -> QuipuNode | None:
        """根据行 Key 选择节点并更新状态。"""
        node = self._node_by_key.get(key)
        self.current_selected_node = node
        return node

    def get_selected_node(self) -> QuipuNode | None:
        return self.current_selected_node

    def get_public_content(self, node: QuipuNode) -> str:
        """仅获取节点的公共内容 (content.md)。"""
        return self.reader.get_node_content(node) or ""

    def previous_page(self) -> list[QuipuNode]:
        """加载上一页的数据。"""
        return self.load_page(self.current_page - 1)

    def next_page(self) -> list[QuipuNode]:
        """加载下一页的数据。"""
        return self.load_page(self.current_page + 1)

    def get_content_bundle(self, node: QuipuNode) -> str:
        """获取节点的公共内容和私有内容，并将它们格式化成一个单一的字符串用于展示。"""
        public_content = self.reader.get_node_content(node) or ""
        private_content = self.reader.get_private_data(node.commit_hash)

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
