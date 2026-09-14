现在进入第二阶段的核心落地：收敛并纯化 Git 物理快照层（`GitSnapshotStorage`）、重构 SQLite 逻辑索引层（`SQLiteGraphIndex`），并将原双向同步语义的 Hydrator 重塑为单向投影器（`CacheProjector`）。

## [WIP] refactor: 实现 GitSnapshotStorage、SQLiteGraphIndex 与 CacheProjector

### 用户需求
落实解耦路线图阶段二：
1. 提炼并创建独立的 `GitSnapshotStorage`，承揽所有 Git 底层快照捕获与对象存储，剥离任何 SQLite 交互。
2. 彻底拆除原 `SQLiteHistoryWriter` 嵌套代理 Git 写入器的设计，实现纯净的 `SQLiteGraphIndex`（实现 `GraphIndex` 协议）。
3. 将 `hydrator.py` 改造为单向投影器 `CacheProjector`，明确从 Source of Truth（Git）到 Read-Model（SQLite）的单向预热/重建语义。

### 评论
通过将 Git 的物理写入/读取与 SQLite 的元数据读写彻底解开：
- `GitSnapshotStorage` 成为唯一维护物理真相的独立组件，即使在没有 SQLite 的环境下也能完整创建快照与提交。
- `SQLiteGraphIndex` 不再扮演伪装的 Storage，而是纯粹的查询缓存和图谱索引器。
- `CacheProjector` 厘清了“缓存补水”的本质是读模型投影，消除了过去两个存储平级的认知偏差。

### 目标
1. 在 `pyquipu-engine` 中创建 `quipu.engine.git_storage.GitSnapshotStorage`，实现 `SnapshotStorage` 协议，提供工作区快照捕获、还原、差异分析及 QDPS 节点落盘能力。
2. 在 `pyquipu-engine` 中创建 `quipu.engine.sqlite_index.SQLiteGraphIndex`，实现 `GraphIndex` 协议，提供纯净的节点记录、关系维系和高速查询能力。
3. 在 `pyquipu-engine` 中创建 `quipu.engine.projector.CacheProjector`，负责将 Git 中的历史数据增量或全量投影至 SQLite。

### 基本原理
1. **单一职责与替换原则**：`GitSnapshotStorage` 专注处理 Git Plumbing（Tree、Blob、Commit、Refs），确保无论上层使用 `SQLiteGraphIndex` 还是 `InMemoryGraphIndex`，物理快照机制完全一致且可复用。
2. **读写分离与读模型投影**：写入操作由 Engine 先调用 `GitSnapshotStorage.create_snapshot_commit(...)` 产生物理凭证，再将生成的 `QuipuNode` 投递给 `GraphIndex.record_node(...)` 建立索引；数据丢失时由 `CacheProjector` 从物理层单向重建索引。

### 标签
#intent/refine #flow/ready #priority/high #comp/engine #concept/state #scope/core #scope/api #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 创建纯净的物理快照存储 `GitSnapshotStorage`

封装 Git 底层能力，实现 `SnapshotStorage` 协议及标准的 QDPS 快照 Commit 封装，零依赖 SQLite。

~~~~~act
write_file
packages/pyquipu-engine/src/quipu/engine/git_storage.py
~~~~~
~~~~~python
import importlib.metadata
import json
import logging
import os
import platform
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from quipu.engine.git_db import GitDB
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import SnapshotStorage

logger = logging.getLogger(__name__)


class GitSnapshotStorage(SnapshotStorage):
    """Git 物理快照存储实现 (Source of Truth).

    负责与底层 Git plumbing 交互，执行 Tree 捕获、检出、Blob/Tree 读写及 Commit 持久化。
    此模块绝不依赖 SQLite。
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.git_db = GitDB(self.root_dir)

    def get_tree_hash(self) -> str:
        return self.git_db.get_tree_hash()

    def capture_workspace(self, message: str | None = None) -> str:
        return self.git_db.get_tree_hash()

    def restore_workspace(self, tree_hash: str) -> None:
        self.git_db.checkout_tree(new_tree_hash=tree_hash)

    def read_blob(self, blob_hash: str) -> bytes:
        return self.git_db.cat_file(blob_hash, "blob")

    def read_tree_blobs(self, tree_hash: str) -> dict[str, bytes]:
        return self.git_db.get_blobs_from_tree(tree_hash)

    def get_diff_stat(self, old_tree: str, new_tree: str, count: int = 30) -> str:
        return self.git_db.get_diff_stat(old_tree, new_tree, count=count)

    def get_diff_name_status(self, old_tree: str, new_tree: str) -> list[tuple[str, str]]:
        return self.git_db.get_diff_name_status(old_tree, new_tree)

    def _get_generator_info(self) -> dict[str, str]:
        return {
            "id": os.getenv("QUIPU_GENERATOR_ID", "manual"),
            "tool": os.getenv("QUIPU_TOOL", "quipu-cli"),
        }

    def _get_env_info(self) -> dict[str, str]:
        try:
            quipu_version = importlib.metadata.version("pyquipu-engine")
        except importlib.metadata.PackageNotFoundError:
            try:
                quipu_version = importlib.metadata.version("quipu-engine")
            except importlib.metadata.PackageNotFoundError:
                quipu_version = "unknown"

        return {
            "quipu": quipu_version,
            "python": platform.python_version(),
            "os": platform.system().lower(),
        }

    def generate_summary(
        self,
        node_type: str,
        content: str,
        input_tree: str,
        output_tree: str,
        summary_override: str | None = None,
        message: str | None = None,
    ) -> str:
        if summary_override:
            return summary_override

        if node_type == "plan":
            match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip()
            first_line = next((line.strip() for line in content.strip().splitlines() if line.strip()), "Plan executed")
            return (first_line[:75] + "...") if len(first_line) > 75 else first_line

        elif node_type == "capture":
            changes = self.git_db.get_diff_name_status(input_tree, output_tree)
            if not changes:
                auto_summary = "Capture: No changes detected"
            else:
                formatted_changes = [f"{status} {Path(path).name}" for status, path in changes[:3]]
                summary_part = ", ".join(formatted_changes)
                if len(changes) > 3:
                    summary_part += f" ... and {len(changes) - 3} more files"
                auto_summary = f"Capture: {summary_part}"

            user_msg = (message or "").strip()
            return f"{user_msg} {auto_summary}".strip() if user_msg else auto_summary

        return "Unknown node type"

    def create_snapshot_commit(
        self,
        node_type: str,
        input_tree: str,
        output_tree: str,
        content: str,
        summary_override: str | None = None,
        parent_commit_hash: str | None = None,
        message: str | None = None,
        owner_id: str | None = None,
        start_time: float | None = None,
    ) -> tuple[QuipuNode, str]:
        """按照 QDPS 规范创建 Git Commit，返回 (QuipuNode, meta_json_str)."""
        actual_start_time = start_time or time.time()
        end_time = time.time()
        duration_ms = int((end_time - actual_start_time) * 1000)

        summary = self.generate_summary(
            node_type=node_type,
            content=content,
            input_tree=input_tree,
            output_tree=output_tree,
            summary_override=summary_override,
            message=message,
        )

        metadata = {
            "meta_version": "1.0",
            "summary": summary,
            "type": node_type,
            "generator": self._get_generator_info(),
            "env": self._get_env_info(),
            "exec": {"start": actual_start_time, "duration_ms": duration_ms},
        }

        meta_json_bytes = json.dumps(metadata, sort_keys=False, ensure_ascii=False).encode("utf-8")
        content_md_bytes = content.encode("utf-8")

        meta_blob_hash = self.git_db.hash_object(meta_json_bytes)
        content_blob_hash = self.git_db.hash_object(content_md_bytes)

        # 构建包含 snapshot tree 强引用的 tree descriptor
        tree_descriptor = (
            f"100444 blob {meta_blob_hash}\tmetadata.json\n"
            f"100444 blob {content_blob_hash}\tcontent.md\n"
            f"040000 tree {output_tree}\tsnapshot"
        )
        tree_hash = self.git_db.mktree(tree_descriptor)

        # 确定父 Commit
        resolved_parent = parent_commit_hash
        if not resolved_parent and input_tree != EMPTY_TREE_HASH:
            resolved_parent = self.git_db.get_commit_by_output_tree(input_tree)

        parents = [resolved_parent] if resolved_parent else None

        commit_message = f"{summary}\n\nX-Quipu-Output-Tree: {output_tree}"
        new_commit_hash = self.git_db.commit_tree(tree_hash=tree_hash, parent_hashes=parents, message=commit_message)

        # 更新本地 head ref
        self.git_db.update_ref(f"refs/quipu/local/heads/{new_commit_hash}", new_commit_hash)

        logger.info(f"✅ Git 快照 Commit 已创建: {new_commit_hash[:7]}")

        node = QuipuNode(
            commit_hash=new_commit_hash,
            input_tree=input_tree,
            output_tree=output_tree,
            timestamp=datetime.fromtimestamp(actual_start_time),
            filename=Path(f".quipu/git_objects/{new_commit_hash}"),
            node_type=node_type,
            content=content,
            summary=summary,
            owner_id=owner_id,
        )

        if resolved_parent:
            node.parent = QuipuNode(
                commit_hash=resolved_parent,
                input_tree="",
                output_tree=input_tree,
                timestamp=datetime.fromtimestamp(0),
                filename=Path(f".quipu/git_objects/{resolved_parent}"),
                node_type="unknown",
                content="",
                summary="",
            )

        return node, meta_json_bytes.decode("utf-8")

    def read_node_content(self, node: QuipuNode) -> str:
        """从 Git 对象库按需提取 content.md."""
        if node.content:
            return node.content

        try:
            commit_bytes = self.git_db.cat_file(node.commit_hash, "commit")
            tree_line = commit_bytes.split(b"\n", 1)[0].decode("utf-8")
            if not tree_line.startswith("tree "):
                return ""
            tree_hash = tree_line.split()[1]

            tree_content_map = self.git_db.batch_cat_file([tree_hash])
            if tree_hash not in tree_content_map:
                return ""

            tree_content = tree_content_map[tree_hash]
            entries = self._parse_tree_binary(tree_content)
            blob_hash = entries.get("content.md")
            if not blob_hash:
                return ""

            content_bytes = self.git_db.cat_file(blob_hash, "blob")
            content = content_bytes.decode("utf-8", errors="ignore")
            node.content = content
            return content
        except Exception as e:
            logger.error(f"Failed to read content for {node.short_hash}: {e}")
            return ""

    def _parse_tree_binary(self, data: bytes) -> dict[str, str]:
        entries = {}
        idx = 0
        length = len(data)
        while idx < length:
            space_idx = data.find(b" ", idx)
            if space_idx == -1:
                break
            null_idx = data.find(b"\0", space_idx + 1)
            if null_idx == -1:
                break
            filename = data[space_idx + 1 : null_idx].decode("utf-8", errors="ignore")
            hash_start = null_idx + 1
            if hash_start + 20 > length:
                break
            hash_bytes = data[hash_start : hash_start + 20]
            entries[filename] = hash_bytes.hex()
            idx = hash_start + 20
        return entries
~~~~~

#### Acts 2: 实现纯净的图谱索引 `SQLiteGraphIndex`

实现 `GraphIndex` 协议，仅承担 SQLite 的 CRUD 与拓扑查询，彻底废除伪装代理写入模式。

~~~~~act
write_file
packages/pyquipu-engine/src/quipu/engine/sqlite_index.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 3: 实现单向读模型投影器 `CacheProjector`

替代原 `hydrator.py`，语义明确为“从 Git 物理真实源单向预热/重建 SQLite 读模型”。

~~~~~act
write_file
packages/pyquipu-engine/src/quipu/engine/projector.py
~~~~~
~~~~~python
import json
import logging
import re

from quipu.engine.git_db import GitDB
from quipu.engine.git_storage import GitSnapshotStorage
from quipu.engine.sqlite_db import DatabaseManager

logger = logging.getLogger(__name__)


class CacheProjector:
    """读模型单向投影器 (Read-Model Projector / Cache Warmer).

    将不可变的 Git 物理快照历史记录增量或全量投影至 SQLite 索引库。
    """

    def __init__(self, git_db: GitDB, db_manager: DatabaseManager):
        self.git_db = git_db
        self.db_manager = db_manager
        self._storage_parser = GitSnapshotStorage(git_db.root)

    def _get_owner_from_ref(self, ref_name: str, local_user_id: str) -> str | None:
        remote_match = re.match(r"refs/quipu/remotes/[^/]+/([^/]+)/heads/.*", ref_name)
        if remote_match:
            return remote_match.group(1)
        if ref_name.startswith("refs/quipu/local/heads/"):
            return local_user_id
        return None

    def _get_commit_owners(self, local_user_id: str) -> dict[str, str]:
        head_ref_tuples = self.git_db.get_all_ref_heads("refs/quipu/")
        head_owners: dict[str, str] = {}
        for commit_hash, ref_name in head_ref_tuples:
            owner_id = self._get_owner_from_ref(ref_name, local_user_id)
            if owner_id and (ref_name.startswith("refs/quipu/remotes") or commit_hash not in head_owners):
                head_owners[commit_hash] = owner_id

        if not head_owners:
            return {}

        all_git_logs = self.git_db.log_ref(list(head_owners.keys()))
        log_map = {entry["hash"]: entry for entry in all_git_logs}

        final_commit_owners: dict[str, str] = {}
        queue = list(head_owners.keys())

        for commit_hash in queue:
            final_commit_owners[commit_hash] = head_owners[commit_hash]

        visited = set(head_owners.keys())

        while queue:
            child_hash = queue.pop(0)
            owner = final_commit_owners.get(child_hash)
            if not owner or child_hash not in log_map:
                continue

            parent_hashes = log_map[child_hash]["parent"].split()
            for parent_hash in parent_hashes:
                if parent_hash and parent_hash not in visited:
                    final_commit_owners[parent_hash] = owner
                    visited.add(parent_hash)
                    queue.append(parent_hash)

        return final_commit_owners

    def _parse_output_tree_from_body(self, body: str) -> str | None:
        match = re.search(r"X-Quipu-Output-Tree:\s*([0-9a-f]{40})", body)
        return match.group(1) if match else None

    def project(self, local_user_id: str):
        """执行单向读模型投影同步."""
        all_ref_heads = [t[0] for t in self.git_db.get_all_ref_heads("refs/quipu/")]
        if not all_ref_heads:
            logger.debug("✅ Git 中未发现 Quipu 引用，无需投影。")
            return

        all_git_logs = self.git_db.log_ref(all_ref_heads)
        if not all_git_logs:
            logger.debug("✅ Git 中未发现 Quipu 历史，无需投影。")
            return
        log_map = {entry["hash"]: entry for entry in all_git_logs}

        commit_owners = self._get_commit_owners(local_user_id)
        db_hashes = self.db_manager.get_all_node_hashes()
        missing_hashes = set(log_map.keys()) - db_hashes

        if not missing_hashes:
            logger.debug("✅ 数据库索引与 Git 历史完全一致，无需投影。")
            return

        logger.info(f"发现 {len(missing_hashes)} 个待投影的历史节点。")

        nodes_to_insert: list[tuple] = []
        edges_to_insert: list[tuple] = []

        tree_hashes = [log_map[h]["tree"] for h in missing_hashes if h in log_map]
        trees_content = self.git_db.batch_cat_file(tree_hashes)

        tree_to_meta_blob: dict[str, str] = {}
        meta_blob_hashes: list[str] = []
        for tree_hash, content_bytes in trees_content.items():
            entries = self._storage_parser._parse_tree_binary(content_bytes)
            if "metadata.json" in entries:
                blob_hash = entries["metadata.json"]
                tree_to_meta_blob[tree_hash] = blob_hash
                meta_blob_hashes.append(blob_hash)
        metas_content = self.git_db.batch_cat_file(meta_blob_hashes)

        for commit_hash in missing_hashes:
            log_entry = log_map[commit_hash]
            tree_hash = log_entry["tree"]
            owner_id = commit_owners.get(commit_hash)
            if not owner_id:
                logger.warning(f"跳过 {commit_hash[:7]}: 无法确定所有者")
                continue

            meta_blob_hash = tree_to_meta_blob.get(tree_hash)
            if not meta_blob_hash or meta_blob_hash not in metas_content:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 metadata.json 内容")
                continue

            output_tree = self._parse_output_tree_from_body(log_entry["body"])
            if not output_tree:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 Output-Tree trailer")
                continue

            try:
                meta_bytes = metas_content[meta_blob_hash]
                meta_data = json.loads(meta_bytes)
                nodes_to_insert.append(
                    (
                        commit_hash,
                        owner_id,
                        output_tree,
                        meta_data.get("type", "unknown"),
                        float(meta_data.get("exec", {}).get("start") or log_entry["timestamp"]),
                        meta_data.get("summary", "No summary"),
                        meta_data.get("generator", {}).get("id"),
                        meta_bytes.decode("utf-8"),
                        None,
                    )
                )
                for p_hash in log_entry["parent"].split():
                    if p_hash in log_map:
                        edges_to_insert.append((commit_hash, p_hash))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析 {commit_hash[:7]} 元数据失败: {e}")

        if nodes_to_insert:
            self.db_manager.batch_insert_nodes(nodes_to_insert)
            logger.info(f"💧 {len(nodes_to_insert)} 个节点索引已投影。")
        if edges_to_insert:
            self.db_manager.batch_insert_edges(edges_to_insert)
            logger.info(f"💧 {len(edges_to_insert)} 条边拓扑已投影。")
~~~~~

### 下一步建议
阶段二的关键组件已经全部就位：
- `GitSnapshotStorage`：物理快照层
- `SQLiteGraphIndex`：本地磁盘索引层
- `InMemoryGraphIndex`：内存极简索引层
- `CacheProjector`：读模型投影器

建议下一步推进**阶段三（引擎中枢改造与装配）**：
1. **改造 `Engine` (`quipu.engine.state_machine`)**：
   - 构造参数接纳 `storage: SnapshotStorage` 与 `index: GraphIndex`（可自动从 `use_cache` 装配），将物理操作路由至 `storage`，图谱操作路由至 `index`。
2. **改造工厂方法 (`quipu.application.factory.create_engine`)**：
   - 支持 `use_cache: bool = True`，在 `use_cache=False` 时初始化 `InMemoryGraphIndex` 并完全跳过 `.quipu/history.sqlite` 的创建。
