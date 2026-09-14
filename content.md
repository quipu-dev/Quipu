我们将严格按照《Quipu Engine 存储与索引层解耦实施路线图》，启动重构的第一阶段：在 `pyquipu-spec` 中重定义纯粹的 `SnapshotStorage` 与 `GraphIndex` 契约协议，并实现无 IO 开销的 `InMemoryGraphIndex`。

## [WIP] refactor: 重定义存储与索引层协议并实现内存索引

### 用户需求
根据解耦实施路线图，废除将 Git 与 SQLite 视为平级存储后端的伪对等抽象（`HistoryReader` / `HistoryWriter`），明确划分物理快照存储（`SnapshotStorage`）与图谱元数据索引（`GraphIndex`）的职责边界，并为无缓存模式提供内存索引实现。

### 评论
这是一次关键的架构正骨手术。通过分离“物理快照存储”（Git Plumbing 唯一真实源）与“图谱元数据索引”（SQLite/Memory 读模型投影），不仅彻底消除了 SQLite 写入器强行包装 Git 写入器的抽象错位，还使 Quipu Engine 具备在 CI/CD 中通过 `use_cache=False` 瞬时纯内存运行的能力。

### 目标
1. 在 `pyquipu-spec` 的 `quipu.spec.protocols.storage` 中定义标准的 `SnapshotStorage` 与 `GraphIndex` 运行时协议，同时保留旧协议别名以平滑过渡。
2. 更新 `quipu.spec.protocols.engine` 中的 `QuipuEngine` 契约，接纳 `storage: SnapshotStorage` 与 `index: GraphIndex`。
3. 在 `pyquipu-engine` 中创建 `quipu.engine.memory_index`，实现轻量、线程安全、纯内存的 `InMemoryGraphIndex`。

### 基本原理
遵循 CQRS 架构原则：
- `SnapshotStorage` 负责底层物理状态的捕获（`capture_workspace`）、还原（`restore_workspace`）与 Git 对象读取（`read_blob`, `read_tree_blobs`），不承载业务图谱关系。
- `GraphIndex` 负责拓扑图节点与元数据（`QuipuNode`）的增删查改和追溯（`get_ancestors`, `get_descendants`, `query_nodes`），不存物理文件实体。
- 阶段一先行落地规约层与内存基准实现，为后续 `GitSnapshotStorage`、`SQLiteGraphIndex` 及 `CacheProjector` 的改造打下坚固基础。

### 标签
#intent/refine #flow/ready #priority/high #comp/engine #comp/interfaces #concept/state #scope/core #scope/api #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重定义存储与索引层协议

我们在 `pyquipu-spec` 中定义 `SnapshotStorage` 与 `GraphIndex` 协议，并保留向前兼容性以确保过渡期间系统稳定。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/storage.py
~~~~~
~~~~~python
from typing import Any, Protocol, runtime_checkable

from ..models.graph import QuipuNode


@runtime_checkable
class SnapshotStorage(Protocol):
    """定义物理快照存储的契约 (Source of Truth).

    仅负责工作区物理状态的捕获、还原以及物理对象 (Blob/Tree/Commit) 的读写，
    不承载图谱拓扑与业务元数据查询。
    """

    def get_tree_hash(self) -> str: ...

    def capture_workspace(self, message: str | None = None) -> str: ...

    def restore_workspace(self, tree_hash: str) -> None: ...

    def read_blob(self, blob_hash: str) -> bytes: ...

    def read_tree_blobs(self, tree_hash: str) -> dict[str, bytes]: ...

    def get_diff_stat(self, old_tree: str, new_tree: str, count: int = 30) -> str: ...

    def get_diff_name_status(self, old_tree: str, new_tree: str) -> list[tuple[str, str]]: ...


@runtime_checkable
class GraphIndex(Protocol):
    """定义图谱拓扑与元数据索引层的契约 (Read-Model / Query Cache).

    仅维护 QuipuNode 节点元数据、拓扑父子关系和轻量缓存，
    不负责文件物理实体的落盘。
    """

    def record_node(self, node: QuipuNode) -> None: ...

    def get_node(self, commit_hash: str) -> QuipuNode | None: ...

    def get_node_count(self) -> int: ...

    def get_node_position(self, output_tree_hash: str) -> int: ...

    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]: ...

    def load_all_nodes(self) -> list[QuipuNode]: ...

    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]: ...

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]: ...

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]: ...

    def get_private_data(self, node_commit_hash: str) -> str | None: ...


# --- 向后兼容别名 (过渡期保留，后续阶段清理) ---


@runtime_checkable
class HistoryReader(Protocol):
    def load_all_nodes(self) -> list[QuipuNode]: ...
    def get_node_content(self, node: QuipuNode) -> str: ...
    def get_node_blobs(self, commit_hash: str) -> dict[str, bytes]: ...
    def find_nodes(
        self, summary_regex: str | None = None, node_type: str | None = None, limit: int = 10
    ) -> list[QuipuNode]: ...
    def get_node_count(self) -> int: ...
    def load_nodes_paginated(self, limit: int, offset: int) -> list[QuipuNode]: ...
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> set[str]: ...
    def get_private_data(self, node_commit_hash: str) -> str | None: ...
    def get_descendant_output_trees(self, start_output_tree_hash: str) -> set[str]: ...
    def get_node_position(self, output_tree_hash: str) -> int: ...


@runtime_checkable
class HistoryWriter(Protocol):
    def create_node(
        self, node_type: str, input_tree: str, output_tree: str, content: str, **kwargs: Any
    ) -> QuipuNode: ...
~~~~~

#### Acts 2: 更新 `QuipuEngine` 核心协议

让 `QuipuEngine` 明确声明包含 `storage` 和 `index` 组件。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/engine.py
~~~~~
~~~~~python
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
~~~~~

#### Acts 3: 在 `pyquipu-engine` 中实现 `InMemoryGraphIndex`

为无缓存（CI/CD 或快速执行）场景提供纯内存的高性能 `GraphIndex` 实现。

~~~~~act
write_file
packages/pyquipu-engine/src/quipu/engine/memory_index.py
~~~~~
~~~~~python
import logging
import re
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import GraphIndex

logger = logging.getLogger(__name__)


class InMemoryGraphIndex(GraphIndex):
    """纯内存图谱索引实现。

    适用于 CI/CD 环境、单元测试或不需要持久化 SQLite 缓存的极简瞬时场景。
    """

    def __init__(self):
        self._nodes: dict[str, QuipuNode] = {}
        self._private_data: dict[str, str] = {}

    def record_node(self, node: QuipuNode) -> None:
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
~~~~~

### 下一步建议
我们已经完成了路线图的阶段一（协议定义）和阶段二的 `InMemoryGraphIndex`。建议接下来的执行方向：
1. **阶段二续（底层存储纯化与提炼）**：
   - 编写 `quipu.engine.git_storage.GitSnapshotStorage`，承接所有 Git plumbing 操作，产出纯净的快照存储实现。
   - 改造 `quipu.engine.sqlite_storage` 为符合 `GraphIndex` 协议的 `SQLiteGraphIndex`，完全废除伪装代理逻辑。
   - 将 `hydrator.py` 改造为单向投影器 `CacheProjector`。
2. **阶段三（引擎装配）**：
   - 更新 `Engine` 构造函数，支持 `use_cache: bool = True`，在无缓存时自动装配 `InMemoryGraphIndex`。
