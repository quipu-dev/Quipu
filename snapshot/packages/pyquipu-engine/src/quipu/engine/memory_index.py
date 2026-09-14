import logging
import re
from typing import Any

from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import GraphIndex

logger = logging.getLogger(__name__)


class InMemoryGraphIndex(GraphIndex):
    def __init__(self):
        self._nodes: dict[str, QuipuNode] = {}
        self._private_data: dict[str, str] = {}

    def record_node(self, node: QuipuNode, meta_json: str | None = None, **kwargs: Any) -> None:
        self._nodes[node.commit_hash] = node
        if node.parent and node.parent.commit_hash in self._nodes:
            parent_in_index = self._nodes[node.parent.commit_hash]
            if node not in parent_in_index.children:
                parent_in_index.children.append(node)

    def record_private_data(self, commit_hash: str, intent_md: str) -> None:
        self._private_data[commit_hash] = intent_md

    def get_node(self, commit_hash: str) -> QuipuNode | None:
        return self._nodes.get(commit_hash)

    def get_node_count(self) -> int:
        return len(self._nodes)

    def get_node_position(self, output_tree_hash: str) -> int:
        sorted_nodes = self.load_all_nodes()
        for idx, node in enumerate(sorted_nodes):
            if node.output_tree == output_tree_hash:
                return idx
        return -1

    def load_all_nodes(self) -> list[QuipuNode]:
        return sorted(self._nodes.values(), key=lambda n: n.timestamp, reverse=True)

    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]:
        all_nodes = self.load_all_nodes()
        return all_nodes[offset : offset + limit]

    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]:
        candidates = list(self._nodes.values())

        if node_type:
            candidates = [n for n in candidates if n.node_type == node_type]

        if summary_regex:
            try:
                pattern = re.compile(summary_regex, re.IGNORECASE)
                candidates = [n for n in candidates if pattern.search(n.summary)]
            except re.error as e:
                logger.error(f"Invalid regex '{summary_regex}': {e}")
                return []

        candidates.sort(key=lambda n: n.timestamp, reverse=True)
        return candidates[:limit]

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]:
        ancestors = set()
        matched_nodes = [n for n in self._nodes.values() if n.output_tree == start_output_tree_hash]
        queue = list(matched_nodes)

        while queue:
            current = queue.pop(0)
            if current.parent:
                p_tree = current.parent.output_tree
                if p_tree not in ancestors:
                    ancestors.add(p_tree)
                    queue.append(current.parent)
        return ancestors

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]:
        descendants = set()
        matched_nodes = [n for n in self._nodes.values() if n.output_tree == start_output_tree_hash]
        queue = list(matched_nodes)

        while queue:
            current = queue.pop(0)
            for child in current.children:
                c_tree = child.output_tree
                if c_tree not in descendants:
                    descendants.add(c_tree)
                    queue.append(child)
        return descendants

    def get_private_data(self, node_commit_hash: str) -> str | None:
        return self._private_data.get(node_commit_hash)
