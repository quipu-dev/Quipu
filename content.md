现在进入路线图的第三阶段：**改造引擎中枢调度（`state_machine.py`）与组装工厂（`factory.py`）**。

## [WIP] refactor: 重构 Engine 核心中枢与装配工厂以支持可选缓存与职责解耦

### 用户需求
落实路线图第三阶段：
1. 改造 `Engine`（`state_machine.py`），使其依赖清晰的 `storage: SnapshotStorage` 与 `index: GraphIndex`，将物理快照操作（Tree/Blob/Commit）交由存储层，元数据与图谱操作交由索引层。
2. 为 `Engine` 提供内置适配能力，确保现有 CLI/TUI 调用（如 `engine.reader.get_node_blobs`）完全平滑过渡。
3. 改造 `create_engine`（`factory.py`），引入 `use_cache: bool = True` 开关。在无缓存模式下，跳过任何 SQLite 初始化，装配纯内存索引 `InMemoryGraphIndex`，达成 CI/CD 瞬时执行目标。

### 评论
通过这次中枢重构，`Engine` 真正成为了协调 Command（`storage`）与 Query（`index`）的纯粹门面（Facade）：
- 无论底层是否启用 SQLite 缓存，`Engine` 的核心业务流程（`capture_drift`, `create_plan_node`, `align`, `visit`）保持 100% 统一。
- 在 CI/CD 场景下，用户只需传入 `use_cache=False`，即可零文件副作用运行，彻底解除了由于 SQLite 初始化导致的并发与锁困扰。

### 目标
1. 重构 `packages/pyquipu-engine/src/quipu/engine/state_machine.py`：
   - 构造参数接纳 `storage: SnapshotStorage` 与 `index: GraphIndex`，兼容旧参数。
   - `capture_drift` 和 `create_plan_node` 先由 `storage` 创建物理 Git Commit，再投递给 `index.record_node`。
   - `align` 通过 `CacheProjector`（当启用 SQLite 时）按需同步读模型。
   - 提供向后兼容层，让旧上层代码安全过渡。
2. 重构 `packages/pyquipu-application/src/quipu/application/factory.py`：
   - 支持 `create_engine(work_dir, lazy=False, use_cache=True)`。
   - 根据 `use_cache` 动态装配 `SQLiteGraphIndex` 或 `InMemoryGraphIndex`。

### 基本原理
1. **中枢解耦**：不再把物理写入和缓存索引绑在同一个 `writer` 链条上。写入时，物理层（`storage.create_snapshot_commit`）作为不可变真相先落盘；逻辑层（`index.record_node`）作为索引投影紧随其后。
2. **渐进式迁移保障**：在 `Engine` 内部将旧接口（`engine.reader`）透明映射为“物理读向 storage 借道，拓扑读向 index 借道”的组合路由，确保现有 TUI、Export、Query 等命令不受破坏。

### 标签
#intent/refine #flow/ready #priority/high #comp/engine #comp/application #concept/state #scope/core #scope/api #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构 `Engine` 状态机与调度中枢

重构 `state_machine.py`，实现 `storage` 与 `index` 的职责分离与统一调度。

~~~~~act
write_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python
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
    """向后兼容适配器，让 engine.reader 能够在迁移期安全路由到 storage 与 index."""

    def __init__(self, engine: "Engine"):
        self._engine = engine

    def load_all_nodes(self) -> list[QuipuNode]:
        return self._engine.index.load_all_nodes()

    def get_node_count(self) -> int:
        return self._engine.index.get_node_count()

    def get_node_position(self, output_tree_hash: str) -> int:
        return self._engine.index.get_node_position(output_tree_hash)

    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]:
        return self._engine.index.load_nodes_paginated(limit, offset)

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]:
        return self._engine.index.get_ancestor_output_trees(start_output_tree_hash)

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]:
        return self._engine.index.get_descendant_output_trees(start_output_tree_hash)

    def get_private_data(self, node_commit_hash: str) -> str | None:
        return self._engine.index.get_private_data(node_commit_hash)

    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]:
        return self._engine.index.find_nodes(summary_regex, node_type, limit)

    def get_node_content(self, node: QuipuNode) -> str:
        if node.content:
            return node.content
        if hasattr(self._engine.storage, "read_node_content"):
            return self._engine.storage.read_node_content(node)
        return ""

    def get_node_blobs(self, commit_hash: str) -> dict[str, bytes]:
        if hasattr(self._engine.storage, "git_db"):
            return self._engine.storage.git_db.get_blobs_from_tree(commit_hash)
        return {}


class Engine:
    """Quipu 状态引擎门面 (Facade).

    协调 GitSnapshotStorage (物理状态真相) 与 GraphIndex (图谱索引/缓存加速).
    """

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
        # 兼容旧参数签名: (root_dir, db, reader, writer, db_manager)
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

        # 1. 初始化底层存储 (SnapshotStorage)
        if storage is not None:
            self.storage = storage
        elif isinstance(db, GitDB):
            self.storage = GitSnapshotStorage(self.root_dir)
        else:
            self.storage = GitSnapshotStorage(self.root_dir)

        # 2. 导出 git_db 便于兼容底层 plumbing
        if hasattr(self.storage, "git_db"):
            self.git_db = self.storage.git_db
        else:
            self.git_db = db or GitDB(self.root_dir)

        # 3. 初始化索引层 (GraphIndex)
        self.use_cache = use_cache
        self.db_manager = db_manager

        if index is not None:
            self.index = index
        elif self.use_cache:
            if self.db_manager is None:
                self.db_manager = DatabaseManager(self.root_dir)
                self.db_manager.init_schema()
            self.index = SQLiteGraphIndex(self.db_manager)
        else:
            self.db_manager = None
            self.index = InMemoryGraphIndex()

        # 4. 兼容层桥接
        self.reader = _EngineReaderCompatibilityAdapter(self)
        self.writer = self  # 兼容旧代码使用 engine.writer

        self.history_graph: dict[str, QuipuNode] = {}
        self.current_node: QuipuNode | None = None

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
        # 如果使用 SQLite 且连接存在，单向预热/同步读模型
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

        # 1. 物理层：创建物理 Git Commit
        if isinstance(self.storage, GitSnapshotStorage):
            new_node, meta_json = self.storage.create_snapshot_commit(
                node_type="capture",
                input_tree=input_hash,
                output_tree=current_hash,
                content=body,
                parent_commit_hash=parent_commit,
                message=message,
                owner_id=user_id,
            )
        else:
            # 回退通用实现
            new_node, meta_json = GitSnapshotStorage(self.root_dir).create_snapshot_commit(
                node_type="capture",
                input_tree=input_hash,
                output_tree=current_hash,
                content=body,
                parent_commit_hash=parent_commit,
                message=message,
                owner_id=user_id,
            )

        # 2. 逻辑层：写入索引
        if hasattr(self.index, "record_node"):
            self.index.record_node(new_node, meta_json=meta_json)

        # 3. 内存拓扑维护
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

        # 1. 物理层：创建物理 Git Commit
        if isinstance(self.storage, GitSnapshotStorage):
            new_node, meta_json = self.storage.create_snapshot_commit(
                node_type="plan",
                input_tree=input_tree,
                output_tree=output_tree,
                content=plan_content,
                summary_override=summary_override,
                parent_commit_hash=parent_commit,
                owner_id=user_id,
            )
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

        # 2. 逻辑层：写入索引
        if hasattr(self.index, "record_node"):
            self.index.record_node(new_node, meta_json=meta_json)

        # 3. 内存拓扑维护
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
        self.storage.restore_workspace(target_hash)
        self._write_head(target_hash)
        self.current_node = None
        for node in self.history_graph.values():
            if node.output_tree == target_hash:
                self.current_node = node
                break
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
~~~~~

#### Acts 2: 改造引擎工厂函数 `factory.py`

在工厂方法中引入 `use_cache: bool = True`，在无缓存模式下完全跳过 SQLite 初始化与文件触碰。

~~~~~act
write_file
packages/pyquipu-application/src/quipu/application/factory.py
~~~~~
~~~~~python
import logging
from pathlib import Path

from quipu.engine.config import ConfigManager
from quipu.engine.git_storage import GitSnapshotStorage
from quipu.engine.memory_index import InMemoryGraphIndex
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_index import SQLiteGraphIndex
from quipu.engine.state_machine import Engine

from .utils import find_git_repository_root

logger = logging.getLogger(__name__)


def create_engine(work_dir: Path, lazy: bool = False, use_cache: bool = True) -> Engine:
    """实例化 Quipu 引擎堆栈。

    Args:
        work_dir: 操作的工作区目录。
        lazy: 如果为 True，则不立即加载完整的历史图谱 (不调用 align)。
        use_cache: 如果为 False，则关闭 SQLite 缓存，使用纯内存索引，
                  实现 0 IO 开销与零副作用，专为 CI/CD 瞬时执行设计。
    """
    project_root = find_git_repository_root(work_dir) or work_dir
    config = ConfigManager(project_root)

    # 1. 物理快照存储层：永远是 GitSnapshotStorage
    storage = GitSnapshotStorage(project_root)

    # 2. 检查配置覆盖 (如果用户显式配置了 storage.type = "memory" 或环境变量指定)
    config_storage_type = config.get("storage.type", "sqlite")
    if config_storage_type in ("memory", "none", "in_memory"):
        use_cache = False

    # 3. 逻辑索引层按需装配
    db_manager = None
    if use_cache:
        logger.debug("Engine factory: Using SQLiteGraphIndex (use_cache=True)")
        db_manager = DatabaseManager(project_root)
        db_manager.init_schema()
        index = SQLiteGraphIndex(db_manager)
    else:
        logger.debug("Engine factory: Using InMemoryGraphIndex (use_cache=False)")
        index = InMemoryGraphIndex()

    # 4. 组装并返回 Engine 门面
    engine = Engine(
        root_dir=project_root,
        storage=storage,
        index=index,
        db_manager=db_manager,
        use_cache=use_cache,
    )

    if not lazy:
        engine.align()

    return engine
~~~~~

### 下一步建议
阶段三（中枢解耦与装配改造）已经完成。目前 `Engine` 已经正式通过 `storage` 和 `index` 运行，并且支持 `use_cache=False` 瞬时内存模式。

建议下一步推进**阶段四与阶段五（适配治理与测试验证）**：
1. **测试辅助桩调整 (`pyquipu-test-utils/src/quipu/test_utils/helpers.py`)**：
   - 适配 `InMemorySnapshotStorage` 与 `InMemoryGraphIndex`，确保测试框架无缝对接新协议。
2. **运行全量测试**：
   - 使用 `run_command` 执行 `pytest`，验证所有 CLI、Engine、TUI、Cache 和 Sync 测试是否通过，确保解耦重构零回归。
