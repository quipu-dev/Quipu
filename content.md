# [Type] feat: Implement SQLite pagination and private data reading

## 用户需求
UI 性能在历史记录较多时显著下降，且无法展示私有数据（如 intent）。用户希望通过分页加载和私有数据支持来优化体验。

## 评论
这是一个关键的性能优化。通过在数据库层面实现分页和递归查询，避免了全量加载的开销。同时引入私有数据读取，完善了 Quipu 的知识管理能力。

## 目标
1.  在 `SQLiteHistoryReader` 中实现 `get_node_count` 和 `load_nodes_paginated`。
2.  实现 `get_private_data` 用于读取 `intent.md`。
3.  利用 SQLite CTE 实现高效的 `get_ancestor_hashes`，替代内存计算。

## 基本原理
利用 SQLite 的 SQL 能力（LIMIT/OFFSET 分页，Recursive CTE 递归查询）将计算下推到数据库层，大幅减少 Python 层的内存占用和 IO 开销。

## 标签
#intent/build #flow/ready #priority/high
#comp/engine #concept/state #scope/core
#ai/instruct
#task/domain/storage #task/object/sqlite-backend #task/action/integration
#task/state/continue #task/status/active

---

## Script

### Acts 1: Add sqlite3 import

引入 `sqlite3` 模块以支持异常处理。

~~~~~act
replace packages/quipu-engine/src/quipu/core/sqlite_storage.py
~~~~~
~~~~~python
import json
import logging
from typing import Any, List, Dict, Optional, Set
~~~~~
~~~~~python
import json
import logging
import sqlite3
from typing import Any, List, Dict, Optional, Set
~~~~~

### Acts 2: Implement pagination and data retrieval methods

实现分页加载、节点计数、私有数据读取和基于 CTE 的祖先查询。

~~~~~act
replace packages/quipu-engine/src/quipu/core/sqlite_storage.py
~~~~~
~~~~~python
    def get_node_count(self) -> int:
        # 待实现
        return 0

    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]:
        # 待实现
        return []

    def get_ancestor_hashes(self, commit_hash: str) -> Set[str]:
        # 待实现
        return set()

    def get_private_data(self, commit_hash: str) -> Optional[str]:
        # 待实现
        return None
~~~~~
~~~~~python
    def get_node_count(self) -> int:
        """
        获取历史节点总数。
        """
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get node count: {e}")
            return 0

    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]:
        """
        按需加载一页节点数据。
        """
        conn = self.db_manager._get_conn()
        try:
            # 1. Fetch nodes
            cursor = conn.execute(
                "SELECT * FROM nodes ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()

            if not rows:
                return []

            nodes_map = {}
            node_hashes = []

            for row in rows:
                commit_hash = row["commit_hash"]
                node_hashes.append(commit_hash)
                nodes_map[commit_hash] = QuipuNode(
                    input_tree="",  # Placeholder
                    output_tree=row["output_tree"],
                    timestamp=datetime.fromtimestamp(row["timestamp"]),
                    filename=Path(f".quipu/git_objects/{commit_hash}"),
                    node_type=row["node_type"],
                    summary=row["summary"],
                    content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                )

            # 2. Fetch edges to identify parents
            placeholders = ",".join("?" * len(node_hashes))
            edges_cursor = conn.execute(
                f"SELECT child_hash, parent_hash FROM edges WHERE child_hash IN ({placeholders})",
                tuple(node_hashes)
            )
            edges = edges_cursor.fetchall()
            
            child_to_parent = {row["child_hash"]: row["parent_hash"] for row in edges}
            parent_hashes = [row["parent_hash"] for row in edges]

            # 3. Fetch parent output_tree for input_tree linking
            parent_info = {}
            if parent_hashes:
                p_placeholders = ",".join("?" * len(parent_hashes))
                p_cursor = conn.execute(
                    f"SELECT commit_hash, output_tree FROM nodes WHERE commit_hash IN ({p_placeholders})",
                    tuple(parent_hashes)
                )
                parent_info = {row["commit_hash"]: row["output_tree"] for row in p_cursor.fetchall()}
            
            genesis_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

            results = []
            for commit_hash in node_hashes:
                node = nodes_map[commit_hash]
                parent_hash = child_to_parent.get(commit_hash)

                if parent_hash:
                    # Set input_tree from parent's output_tree
                    node.input_tree = parent_info.get(parent_hash, genesis_hash)
                    
                    # Link objects if parent is in the same page
                    if parent_hash in nodes_map:
                        parent_node = nodes_map[parent_hash]
                        node.parent = parent_node
                        parent_node.children.append(node)
                else:
                    node.input_tree = genesis_hash
                
                results.append(node)
            
            # Sort children for consistency (though partial)
            for node in results:
                node.children.sort(key=lambda n: n.timestamp)
            
            return results

        except sqlite3.Error as e:
            logger.error(f"Failed to load paginated nodes: {e}")
            return []

    def get_ancestor_hashes(self, commit_hash: str) -> Set[str]:
        """
        获取指定节点的所有祖先节点的哈希集合 (用于可达性分析)。
        使用 Recursive CTE 在数据库层面高效完成。
        """
        conn = self.db_manager._get_conn()
        try:
            sql = """
            WITH RECURSIVE ancestors(parent_hash) AS (
                SELECT parent_hash FROM edges WHERE child_hash = ?
                UNION ALL
                SELECT e.parent_hash FROM edges e, ancestors a WHERE e.child_hash = a.parent_hash
            )
            SELECT parent_hash FROM ancestors;
            """
            cursor = conn.execute(sql, (commit_hash,))
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to get ancestors for {commit_hash[:7]}: {e}")
            return set()

    def get_private_data(self, commit_hash: str) -> Optional[str]:
        """
        获取指定节点的私有数据 (如 intent.md)。
        """
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute(
                "SELECT intent_md FROM private_data WHERE node_hash = ?", 
                (commit_hash,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get private data for {commit_hash[:7]}: {e}")
            return None
~~~~~
