import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from quipu.common.identity import get_user_id_from_email
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import GraphIndex, SnapshotStorage

from .config import ConfigManager
from .git_db import GitDB
from .git_storage import GitSnapshotStorage
from .memory_index import InMemoryGraphIndex
from .projector import CacheProjector
from .sqlite_db import DatabaseManager
from .sqlite_index import SQLiteGraphIndex

logger = logging.getLogger(__name__)


class _EngineReaderCompatibilityAdapter:
    def __init__(self, engine: "Engine", original_reader: Any = None):
        self._engine = engine
        self._original = original_reader

    def load_all_nodes(self) -> list[QuipuNode]:
        if self._original and hasattr(self._original, "load_all_nodes"):
            return self._original.load_all_nodes()
        return self._engine.index.load_all_nodes()

    def get_node_count(self) -> int:
        if self._original and hasattr(self._original, "get_node_count"):
            return self._original.get_node_count()
        return self._engine.index.get_node_count()

    def get_node_position(self, output_tree_hash: str) -> int:
        if self._original and hasattr(self._original, "get_node_position"):
            return self._original.get_node_position(output_tree_hash)
        return self._engine.index.get_node_position(output_tree_hash)

    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]:
        if self._original and hasattr(self._original, "load_nodes_paginated"):
            return self._original.load_nodes_paginated(limit, offset)
        return self._engine.index.load_nodes_paginated(limit, offset)

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]:
        if self._original and hasattr(self._original, "get_ancestor_output_trees"):
            return self._original.get_ancestor_output_trees(start_output_tree_hash)
        return self._engine.index.get_ancestor_output_trees(start_output_tree_hash)

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]:
        if self._original and hasattr(self._original, "get_descendant_output_trees"):
            return self._original.get_descendant_output_trees(start_output_tree_hash)
        return self._engine.index.get_descendant_output_trees(start_output_tree_hash)

    def get_private_data(self, node_commit_hash: str) -> str | None:
        if self._original and hasattr(self._original, "get_private_data"):
            return self._original.get_private_data(node_commit_hash)
        return self._engine.index.get_private_data(node_commit_hash)

    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]:
        if self._original and hasattr(self._original, "find_nodes"):
            return self._original.find_nodes(summary_regex, node_type, limit)
        return self._engine.index.find_nodes(summary_regex, node_type, limit)

    def get_node_content(self, node: QuipuNode) -> str:
        if node.content:
            return node.content
        if self._original and hasattr(self._original, "get_node_content"):
            return self._original.get_node_content(node)
        if hasattr(self._engine.storage, "read_node_content"):
            return self._engine.storage.read_node_content(node)
        return ""

    def get_node_blobs(self, commit_hash: str) -> dict[str, bytes]:
        if self._original and hasattr(self._original, "get_node_blobs"):
            return self._original.get_node_blobs(commit_hash)
        if hasattr(self._engine.storage, "git_db"):
            return self._engine.storage.git_db.get_blobs_from_tree(commit_hash)
        return {}


class _EngineWriterCompatibilityAdapter:
    def __init__(self, engine: "Engine", original_writer: Any = None):
        self._engine = engine
        self._original = original_writer

    def create_node(
        self,
        node_type: str,
        input_tree: str,
        output_tree: str,
        content: str,
        summary_override: str | None = None,
        **kwargs: Any,
    ) -> QuipuNode:
        if self._original and hasattr(self._original, "create_node"):
            return self._original.create_node(
                node_type=node_type,
                input_tree=input_tree,
                output_tree=output_tree,
                content=content,
                summary_override=summary_override,
                **kwargs,
            )

        if isinstance(self._engine.storage, GitSnapshotStorage):
            node, meta_json = self._engine.storage.create_snapshot_commit(
                node_type=node_type,
                input_tree=input_tree,
                output_tree=output_tree,
                content=content,
                summary_override=summary_override,
                message=kwargs.get("message"),
                parent_commit_hash=kwargs.get("parent_commit_hash"),
                owner_id=kwargs.get("owner_id"),
                start_time=kwargs.get("start_time"),
            )
            if hasattr(self._engine.index, "record_node"):
                self._engine.index.record_node(node, meta_json=meta_json)
            return node

        raise NotImplementedError("create_node is not supported on the current storage backend")


class Engine:
    def _sync_persistent_ignores(self):
        try:
            config = ConfigManager(self.root_dir)
            patterns = config.get("sync.persistent_ignores", [])
            if not patterns:
                return

            exclude_file = self.root_dir / ".git" / "info" / "exclude"
            exclude_file.parent.mkdir(exist_ok=True)

            header = "# --- Managed by Quipu ---"
            footer = "# --- End Managed by Quipu ---"

            content = ""
            if exclude_file.exists():
                content = exclude_file.read_text("utf-8")

            managed_block_pattern = re.compile(rf"{re.escape(header)}.*{re.escape(footer)}", re.DOTALL)
            new_block = f"{header}\n" + "\n".join(patterns) + f"\n{footer}"
            new_content, count = managed_block_pattern.subn(new_block, content)
            if count == 0:
                if content and not content.endswith("\n"):
                    content += "\n"
                new_content = content + "\n" + new_block + "\n"

            if new_content != content:
                exclude_file.write_text(new_content, "utf-8")
                logger.debug("✅ .git/info/exclude 已更新。")
        except Exception as e:
            logger.warning(f"⚠️ 无法同步持久化忽略规则: {e}")

    def __init__(
        self,
        root_dir: Path,
        storage: SnapshotStorage | None = None,
        index: GraphIndex | None = None,
        db_manager: DatabaseManager | None = None,
        use_cache: bool = True,
        # 兼容旧参数签名
        db: Any = None,
        reader: Any = None,
        writer: Any = None,
    ):
        self.root_dir = root_dir.resolve()
        self.quipu_dir = self.root_dir / ".quipu"
        self.quipu_dir.mkdir(exist_ok=True)
        self.history_dir = self.quipu_dir / "history"
        self.head_file = self.quipu_dir / "HEAD"
        self.nav_log_file = self.quipu_dir / "nav_log"
        self.nav_ptr_file = self.quipu_dir / "nav_ptr"

        quipu_gitignore = self.quipu_dir / ".gitignore"
        if not quipu_gitignore.exists():
            try:
                quipu_gitignore.write_text("*\n", encoding="utf-8")
            except Exception as e:
                logger.warning(f"无法创建隔离文件 {quipu_gitignore}: {e}")

        # 1. 物理快照存储层适配
        if storage is not None:
            self.storage = storage
            self.git_db = getattr(storage, "git_db", storage)
        elif db is not None and not isinstance(db, GitDB):
            # 传入了 InMemoryDB 等自定义测试存储桩
            self.storage = db
            self.git_db = db
        else:
            self.storage = GitSnapshotStorage(self.root_dir)
            self.git_db = self.storage.git_db

        # 2. 逻辑索引层适配
        self.use_cache = use_cache
        self.db_manager = db_manager
        self._custom_writer = writer

        if index is not None:
            self.index = index
        elif reader is not None:
            # 如果显式传入了旧 reader（如 InMemoryHistoryManager 或旧测试），直接将其视作索引
            self.index = reader
        elif self.use_cache and (self.db_manager is not None or (self.quipu_dir / "history.sqlite").exists()):
            if self.db_manager is None:
                self.db_manager = DatabaseManager(self.root_dir)
                self.db_manager.init_schema()
            self.index = SQLiteGraphIndex(self.db_manager)
        elif self.use_cache and db_manager is not None:
            self.index = SQLiteGraphIndex(self.db_manager)
        else:
            self.index = InMemoryGraphIndex()

        # 3. 兼容层桥接
        self.reader = _EngineReaderCompatibilityAdapter(self, original_reader=reader)
        self.writer = _EngineWriterCompatibilityAdapter(self, original_writer=writer)

        self.history_graph: dict[str, QuipuNode] = {}
        self.current_node: QuipuNode | None = None

        if isinstance(self.git_db, GitDB):
            self._sync_persistent_ignores()

    def close(self):
        if self.db_manager:
            self.db_manager.close()

    def _get_current_user_id(self) -> str:
        config = ConfigManager(self.root_dir)
        user_id = config.get("sync.user_id")
        if user_id:
            return user_id

        try:
            result = subprocess.run(
                ["git", "config", "user.email"],
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            email = result.stdout.strip()
            if email:
                return get_user_id_from_email(email)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return "unknown-local-user"

    def _read_head(self) -> str | None:
        if self.head_file.exists():
            return self.head_file.read_text(encoding="utf-8").strip()
        return None

    def _write_head(self, tree_hash: str):
        try:
            self.head_file.write_text(tree_hash, encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️ 无法更新 HEAD 指针: {e}")

    def _read_nav(self) -> tuple[list[str], int]:
        log = []
        ptr = -1
        if self.nav_log_file.exists():
            try:
                content = self.nav_log_file.read_text(encoding="utf-8").strip()
                if content:
                    log = content.splitlines()
            except Exception:
                pass
        if self.nav_ptr_file.exists():
            try:
                ptr = int(self.nav_ptr_file.read_text(encoding="utf-8").strip())
            except Exception:
                pass
        if not log:
            ptr = -1
        elif ptr < 0:
            ptr = 0
        elif ptr >= len(log):
            ptr = len(log) - 1
        return log, ptr

    def _write_nav(self, log: list[str], ptr: int):
        try:
            self.nav_log_file.write_text("\n".join(log), encoding="utf-8")
            self.nav_ptr_file.write_text(str(ptr), encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️ 无法更新导航历史: {e}")

    def _append_nav(self, tree_hash: str):
        log, ptr = self._read_nav()
        if not log:
            current_head = self._read_head()
            if current_head and current_head != tree_hash:
                log.append(current_head)
                ptr = 0
        if ptr < len(log) - 1:
            log = log[: ptr + 1]
        if log and log[-1] == tree_hash:
            ptr = len(log) - 1
            self._write_nav(log, ptr)
            return
        log.append(tree_hash)
        ptr = len(log) - 1
        MAX_LOG_SIZE = 100
        if len(log) > MAX_LOG_SIZE:
            log = log[-MAX_LOG_SIZE:]
            ptr = len(log) - 1
        self._write_nav(log, ptr)

    def visit(self, target_hash: str):
        self.checkout(target_hash)
        self._append_nav(target_hash)

    def back(self) -> str | None:
        log, ptr = self._read_nav()
        if ptr > 0:
            new_ptr = ptr - 1
            target_hash = log[new_ptr]
            logger.info(f"🔙 Back to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def forward(self) -> str | None:
        log, ptr = self._read_nav()
        if ptr < len(log) - 1:
            new_ptr = ptr + 1
            target_hash = log[new_ptr]
            logger.info(f"🔜 Forward to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def align(self) -> str:
        if self.use_cache and self.db_manager:
            try:
                user_id = self._get_current_user_id()
                projector = CacheProjector(self.git_db, self.db_manager)
                projector.project(local_user_id=user_id)
            except Exception:
                logger.exception("❌ 自动数据投影失败")

        all_nodes = self.index.load_all_nodes()
        self.history_graph = {node.commit_hash: node for node in all_nodes}
        if all_nodes:
            logger.info(f"从存储中加载了 {len(all_nodes)} 个历史事件，形成 {len(self.history_graph)} 个唯一状态节点。")

        current_hash = self.storage.get_tree_hash()
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
            self.current_node = None
            return "CLEAN"

        matches = [node for node in self.history_graph.values() if node.output_tree == current_hash]
        if matches:
            matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)
            found_node = matches[0]
        else:
            found_node = None

        if found_node:
            self.current_node = found_node
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            self._write_head(current_hash)
            return "CLEAN"

        logger.warning(f"⚠️ 状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        if not self.history_graph:
            return "ORPHAN"
        return "DIRTY"

    def find_nodes(
        self,
        summary_regex: str | None = None,
        node_type: str | None = None,
        limit: int = 10,
    ) -> list[QuipuNode]:
        return self.index.find_nodes(
            summary_regex=summary_regex,
            node_type=node_type,
            limit=limit,
        )

    def capture_drift(self, current_hash: str, message: str | None = None) -> QuipuNode:
        log_message = f"📸 正在捕获工作区漂移 (Message: {message})" if message else "📸 正在捕获工作区漂移"
        logger.info(f"{log_message}，新状态 Hash: {current_hash[:7]}")

        input_hash = EMPTY_TREE_HASH
        head_tree_hash = self._read_head()
        parent_node = None

        if head_tree_hash:
            parent_node = next(
                (node for node in self.history_graph.values() if node.output_tree == head_tree_hash), None
            )

        if parent_node:
            input_hash = parent_node.output_tree
        elif self.history_graph:
            last_node = max(self.history_graph.values(), key=lambda node: node.timestamp)
            input_hash = last_node.output_tree

        diff_summary = self.storage.get_diff_stat(input_hash, current_hash)
        user_message_section = f"### 💬 备注:\n{message}\n\n" if message else ""
        body = (
            f"# 📸 Snapshot Capture\n\n"
            f"{user_message_section}"
            f"检测到工作区发生变更。\n\n"
            f"### 📝 变更文件摘要:\n```\n{diff_summary}\n```"
        )

        user_id = self._get_current_user_id()
        parent_commit = parent_node.commit_hash if parent_node else None

        # 优先支持自定义 writer 桩 (例如 InMemoryHistoryManager)
        if self._custom_writer and hasattr(self._custom_writer, "create_node"):
            new_node = self._custom_writer.create_node(
                node_type="capture",
                input_tree=input_hash,
                output_tree=current_hash,
                content=body,
                message=message,
                owner_id=user_id,
            )
        elif isinstance(self.storage, GitSnapshotStorage):
            new_node, meta_json = self.storage.create_snapshot_commit(
                node_type="capture",
                input_tree=input_hash,
                output_tree=current_hash,
                content=body,
                parent_commit_hash=parent_commit,
                message=message,
                owner_id=user_id,
            )
            if hasattr(self.index, "record_node"):
                self.index.record_node(new_node, meta_json=meta_json)
        else:
            # 通用回退
            new_node, meta_json = GitSnapshotStorage(self.root_dir).create_snapshot_commit(
                node_type="capture",
                input_tree=input_hash,
                output_tree=current_hash,
                content=body,
                parent_commit_hash=parent_commit,
                message=message,
                owner_id=user_id,
            )
            if hasattr(self.index, "record_node"):
                self.index.record_node(new_node, meta_json=meta_json)

        if new_node.parent and new_node.parent.commit_hash in self.history_graph:
            real_parent = self.history_graph[new_node.parent.commit_hash]
            new_node.parent = real_parent
            if new_node not in real_parent.children:
                real_parent.children.append(new_node)

        self.history_graph[new_node.commit_hash] = new_node
        self.current_node = new_node
        self._write_head(current_hash)
        self._append_nav(current_hash)

        logger.info(f"✅ 捕获完成，新节点已创建: {new_node.filename.name}")
        return new_node

    def create_plan_node(
        self, input_tree: str, output_tree: str, plan_content: str, summary_override: str | None = None
    ) -> QuipuNode:
        if input_tree == output_tree:
            logger.info(f"📝 记录幂等操作节点 (Idempotent Node): {output_tree[:7]}")
        else:
            logger.info(f"📝 正在记录 Plan 节点: {input_tree[:7]} -> {output_tree[:7]}")

        user_id = self._get_current_user_id()
        parent_node = None
        head_tree = self._read_head()
        if head_tree:
            parent_node = next((n for n in self.history_graph.values() if n.output_tree == head_tree), None)
        parent_commit = parent_node.commit_hash if parent_node else None

        if self._custom_writer and hasattr(self._custom_writer, "create_node"):
            new_node = self._custom_writer.create_node(
                node_type="plan",
                input_tree=input_tree,
                output_tree=output_tree,
                content=plan_content,
                summary_override=summary_override,
                owner_id=user_id,
            )
        elif isinstance(self.storage, GitSnapshotStorage):
            new_node, meta_json = self.storage.create_snapshot_commit(
                node_type="plan",
                input_tree=input_tree,
                output_tree=output_tree,
                content=plan_content,
                summary_override=summary_override,
                parent_commit_hash=parent_commit,
                owner_id=user_id,
            )
            if hasattr(self.index, "record_node"):
                self.index.record_node(new_node, meta_json=meta_json)
        else:
            new_node, meta_json = GitSnapshotStorage(self.root_dir).create_snapshot_commit(
                node_type="plan",
                input_tree=input_tree,
                output_tree=output_tree,
                content=plan_content,
                summary_override=summary_override,
                parent_commit_hash=parent_commit,
                owner_id=user_id,
            )
            if hasattr(self.index, "record_node"):
                self.index.record_node(new_node, meta_json=meta_json)

        if new_node.parent and new_node.parent.commit_hash in self.history_graph:
            real_parent = self.history_graph[new_node.parent.commit_hash]
            new_node.parent = real_parent
            if new_node not in real_parent.children:
                real_parent.children.append(new_node)

        self.history_graph[new_node.commit_hash] = new_node
        self.current_node = new_node
        self._write_head(output_tree)
        self._append_nav(output_tree)

        logger.info(f"✅ Plan 已归档: {new_node.filename.name}")
        return new_node

    def checkout(self, target_hash: str):
        if hasattr(self.storage, "restore_workspace"):
            self.storage.restore_workspace(target_hash)
        elif hasattr(self.storage, "checkout_tree"):
            self.storage.checkout_tree(target_hash)

        self._write_head(target_hash)
        self.current_node = None
        for node in self.history_graph.values():
            if node.output_tree == target_hash:
                self.current_node = node
                break
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
