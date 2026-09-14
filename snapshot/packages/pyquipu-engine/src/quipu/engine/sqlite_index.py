import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from quipu.engine.sqlite_db import DatabaseManager
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import GraphIndex

logger = logging.getLogger(__name__)


class SQLiteGraphIndex(GraphIndex):
    """基于 SQLite 的图谱与元数据索引实现 (Read-Model / Query Accelerator).

    职责仅限于维护 nodes, edges, private_data 表的结构化数据与关系计算，
    绝不涉及任何底层 Git Plumbing 操作。
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def record_node(self, node: QuipuNode, meta_json: str | None = None) -> None:
        """将 QuipuNode 元数据及边关系记录入 SQLite 索引."""
        meta_str = meta_json
        if not meta_str:
            meta_str = json.dumps(
                {
                    "summary": node.summary,
                    "type": node.node_type,
                    "exec": {"start": node.timestamp.timestamp()},
                }
            )

        self.db_manager.execute_write(
            """
            INSERT OR REPLACE INTO nodes
            (commit_hash, owner_id, output_tree, node_type, timestamp, summary,
             generator_id, meta_json, plan_md_cache)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node.commit_hash,
                node.owner_id or "unknown-local-user",
                node.output_tree,
                node.node_type,
                node.timestamp.timestamp(),
                node.summary,
                None,
                meta_str,
                node.content or None,
            ),
        )

        if node.parent:
            self.db_manager.execute_write(
                "INSERT OR IGNORE INTO edges (child_hash, parent_hash) VALUES (?, ?)",
                (node.commit_hash, node.parent.commit_hash),
            )

    def record_private_data(self, commit_hash: str, intent_md: str) -> None:
        self.db_manager.execute_write(
            "INSERT OR REPLACE INTO private_data (node_hash, intent_md) VALUES (?, ?)",
            (commit_hash, intent_md),
        )

    def get_node(self, commit_hash: str) -> QuipuNode | None:
        conn = self.db_manager._get_conn()
        cursor = conn.execute("SELECT * FROM nodes WHERE commit_hash = ?", (commit_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        return QuipuNode(
            commit_hash=row["commit_hash"],
            input_tree="",
            output_tree=row["output_tree"],
            timestamp=datetime.fromtimestamp(row["timestamp"]),
            filename=Path(f".quipu/git_objects/{row['commit_hash']}"),
            node_type=row["node_type"],
            summary=row["summary"],
            content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
            owner_id=row["owner_id"],
        )

    def get_node_count(self) -> int:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to get node count: {e}")
            return 0

    def get_node_position(self, output_tree_hash: str) -> int:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT MAX(timestamp) FROM nodes WHERE output_tree = ?", (output_tree_hash,))
            row = cursor.fetchone()
            if not row or row[0] is None:
                return -1
            target_ts = row[0]
            cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE timestamp > ?", (target_ts,))
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Failed to get node position: {e}")
            return -1

    def load_all_nodes(self) -> list[QuipuNode]:
        conn = self.db_manager._get_conn()
        nodes_cursor = conn.execute("SELECT * FROM nodes ORDER BY timestamp DESC;")
        nodes_data = nodes_cursor.fetchall()

        temp_nodes: dict[str, QuipuNode] = {}
        for row in nodes_data:
            commit_hash = row["commit_hash"]
            node = QuipuNode(
                commit_hash=commit_hash,
                input_tree="",
                output_tree=row["output_tree"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                filename=Path(f".quipu/git_objects/{commit_hash}"),
                node_type=row["node_type"],
                summary=row["summary"],
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                owner_id=row["owner_id"],
            )
            temp_nodes[commit_hash] = node

        edges_cursor = conn.execute("SELECT child_hash, parent_hash FROM edges;")
        edges_data = edges_cursor.fetchall()

        for row in edges_data:
            child_hash, parent_hash = row["child_hash"], row["parent_hash"]
            if child_hash == parent_hash:
                continue
            if child_hash in temp_nodes and parent_hash in temp_nodes:
                child_node = temp_nodes[child_hash]
                parent_node = temp_nodes[parent_hash]
                if child_node.parent is None:
                    child_node.parent = parent_node
                    parent_node.children.append(child_node)
                    child_node.input_tree = parent_node.output_tree

        for node in temp_nodes.values():
            if node.parent is None:
                node.input_tree = EMPTY_TREE_HASH
            node.children.sort(key=lambda n: n.timestamp)

        return list(temp_nodes.values())

    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM nodes ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            if not rows:
                return []

            nodes_map = {}
            node_hashes = []
            for row in rows:
                commit_hash = row["commit_hash"]
                node_hashes.append(commit_hash)
                nodes_map[commit_hash] = QuipuNode(
                    commit_hash=commit_hash,
                    input_tree="",
                    output_tree=row["output_tree"],
                    timestamp=datetime.fromtimestamp(row["timestamp"]),
                    filename=Path(f".quipu/git_objects/{commit_hash}"),
                    node_type=row["node_type"],
                    summary=row["summary"],
                    content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                    owner_id=row["owner_id"],
                )

            placeholders = ",".join("?" * len(node_hashes))
            edges_cursor = conn.execute(
                f"SELECT child_hash, parent_hash FROM edges WHERE child_hash IN ({placeholders})", tuple(node_hashes)
            )
            edges = edges_cursor.fetchall()
            child_to_parent = {row["child_hash"]: row["parent_hash"] for row in edges}
            parent_hashes = [row["parent_hash"] for row in edges]

            parent_info = {}
            if parent_hashes:
                p_placeholders = ",".join("?" * len(parent_hashes))
                p_cursor = conn.execute(
                    f"SELECT commit_hash, output_tree FROM nodes WHERE commit_hash IN ({p_placeholders})",
                    tuple(parent_hashes),
                )
                parent_info = {row["commit_hash"]: row["output_tree"] for row in p_cursor.fetchall()}

            results = []
            for commit_hash in node_hashes:
                node = nodes_map[commit_hash]
                parent_hash = child_to_parent.get(commit_hash)
                if parent_hash:
                    node.input_tree = parent_info.get(parent_hash, EMPTY_TREE_HASH)
                    if parent_hash in nodes_map:
                        parent_node = nodes_map[parent_hash]
                        node.parent = parent_node
                        parent_node.children.append(node)
                else:
                    node.input_tree = EMPTY_TREE_HASH
                results.append(node)

            for node in results:
                node.children.sort(key=lambda n: n.timestamp)
            return results
        except sqlite3.Error as e:
            logger.error(f"Failed to load paginated nodes: {e}")
            return []

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            rows = cursor.fetchall()
            if not rows:
                return set()
            start_commit_hashes = [row[0] for row in rows]

            all_ancestor_trees = set()
            for commit_hash in start_commit_hashes:
                sql = """
                WITH RECURSIVE ancestors(h) AS (
                    SELECT parent_hash FROM edges WHERE child_hash = ?
                    UNION ALL
                    SELECT e.parent_hash FROM edges e, ancestors a WHERE e.child_hash = a.h AND e.parent_hash IS NOT NULL
                )
                SELECT h FROM ancestors WHERE h IS NOT NULL;
                """
                c_cursor = conn.execute(sql, (commit_hash,))
                ancestor_commit_hashes = {r[0] for r in c_cursor.fetchall()}
                if ancestor_commit_hashes:
                    placeholders = ",".join("?" * len(ancestor_commit_hashes))
                    sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
                    out_cursor = conn.execute(sql_out, tuple(ancestor_commit_hashes))
                    all_ancestor_trees.update(r[0] for r in out_cursor.fetchall())
            return all_ancestor_trees
        except sqlite3.Error as e:
            logger.error(f"Failed to get ancestors for {start_output_tree_hash[:7]}: {e}")
            return set()

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            rows = cursor.fetchall()
            if not rows:
                return set()
            start_commit_hashes = [row[0] for row in rows]

            all_descendant_trees = set()
            for commit_hash in start_commit_hashes:
                sql = """
                WITH RECURSIVE descendants(h) AS (
                    SELECT child_hash FROM edges WHERE parent_hash = ?
                    UNION ALL
                    SELECT e.child_hash FROM edges e, descendants d WHERE e.parent_hash = d.h AND e.child_hash IS NOT NULL
                )
                SELECT h FROM descendants WHERE h IS NOT NULL;
                """
                c_cursor = conn.execute(sql, (commit_hash,))
                descendant_commit_hashes = {r[0] for r in c_cursor.fetchall()}
                if descendant_commit_hashes:
                    placeholders = ",".join("?" * len(descendant_commit_hashes))
                    sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
                    out_cursor = conn.execute(sql_out, tuple(descendant_commit_hashes))
                    all_descendant_trees.update(r[0] for r in out_cursor.fetchall())
            return all_descendant_trees
        except sqlite3.Error as e:
            logger.error(f"Failed to get descendants for {start_output_tree_hash[:7]}: {e}")
            return set()

    def get_private_data(self, node_commit_hash: str) -> str | None:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT intent_md FROM private_data WHERE node_hash = ?", (node_commit_hash,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get private data for {node_commit_hash[:7]}: {e}")
            return None

    def find_nodes(
        self,
        summary_regex: str | None = None,
        node_type: str | None = None,
        limit: int = 10,
    ) -> list[QuipuNode]:
        query = "SELECT * FROM nodes"
        conditions = []
        params = []

        if node_type:
            conditions.append("node_type = ?")
            params.append(node_type)

        if summary_regex:
            conditions.append("summary LIKE ?")
            params.append(f"%{summary_regex}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        conn = self.db_manager._get_conn()
        cursor = conn.execute(query, tuple(params))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            node = QuipuNode(
                commit_hash=row["commit_hash"],
                input_tree="",
                output_tree=row["output_tree"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                filename=Path(f".quipu/git_objects/{row['commit_hash']}"),
                node_type=row["node_type"],
                summary=row["summary"],
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                owner_id=row["owner_id"],
            )
            results.append(node)
        return results
