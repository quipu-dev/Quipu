好的，我们现在开始执行“阶段四：统一与收敛”以及“阶段五：清理”中的核心任务：**统一全局常量 `EMPTY_TREE_HASH` 以及提取 `QuipuEngine` 协议**。

根据你的 `rg` 结果，`EMPTY_TREE_HASH` 目前散落在各处的函数内部或作为硬编码字符串存在。我们将把它们全部指向 `pyquipu-spec`。

## [WIP] refactor: 统一全局常量与提取 Engine 协议

### 用户需求

1.  将全项目中所有的 `EMPTY_TREE_HASH` 字面量和本地定义迁移至 `quipu.spec.constants`。
2.  在 `spec` 包中定义 `QuipuEngine` 协议，以解耦应用层对引擎实现的直接依赖。
3.  更新相关组件的导入路径。

### 评论

统一常量和定义引擎协议是确立 `spec` 包作为系统“宪法”地位的最后几步。这消除了代码库中最后的硬编码“魔术值”，并为应用层与引擎层之间建立了清晰、可模拟（Mockable）的契约。

### 目标

1.  清理 `application`、`cli`、`engine` 以及 `test-utils` 中重复定义的 `EMPTY_TREE_HASH`。
2.  在 `pyquipu-spec` 中创建 `protocols/engine.py`。
3.  重构 `QuipuApplication` 和测试夹具，使其使用 `QuipuEngine` 协议进行类型标注。

### 基本原理

*   **消除魔术值**: `EMPTY_TREE_HASH` 是系统的逻辑起点，将其集中管理可以防止因拼写错误或规范变更导致的不一致。
*   **面向契约编程**: 应用层不应该关心 `Engine` 类的具体实现，它只需要知道 `Engine` 提供了哪些能力。`QuipuEngine` 协议为这种解耦提供了技术支撑。

### 标签

#intent/refine #flow/ready #priority/high #comp/spec #comp/engine #comp/application #comp/cli #scope/api #ai/instruct #task/domain/architecture #task/object/unification #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 定义 Engine 协议

我们在 `spec` 中定义引擎的行为契约。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/engine.py
~~~~~
~~~~~python
from typing import Protocol, Dict, Optional, List, runtime_checkable
from ..models.graph import QuipuNode
from .storage import HistoryReader, HistoryWriter


@runtime_checkable
class QuipuEngine(Protocol):
    """定义 Quipu 状态引擎的核心行为契约"""

    root_dir: Path
    reader: HistoryReader
    writer: HistoryWriter
    history_graph: Dict[str, QuipuNode]
    current_node: Optional[QuipuNode]

    def align(self) -> str: ...
    def visit(self, target_hash: str) -> None: ...
    def capture_drift(self, current_hash: str, message: Optional[str] = None) -> QuipuNode: ...
    def create_plan_node(
        self, input_tree: str, output_tree: str, plan_content: str, summary_override: Optional[str] = None
    ) -> QuipuNode: ...
    def checkout(self, target_hash: str) -> None: ...
    def back(self) -> Optional[str]: ...
    def forward(self) -> Optional[str]: ...
    def find_nodes(
        self, summary_regex: Optional[str] = None, node_type: Optional[str] = None, limit: int = 10
    ) -> List[QuipuNode]: ...
    def close(self) -> None: ...
~~~~~

#### Acts 2: 统一 Application 层常量与类型

重构 `QuipuApplication`，使用集中化的常量和协议。

~~~~~act
patch_file
packages/pyquipu-application/src/quipu/application/controller.py
~~~~~
~~~~~python.old
from quipu.acts import register_core_acts
from quipu.engine.state_machine import Engine
from quipu.spec.exceptions import ExecutionError as CoreExecutionError
~~~~~
~~~~~python.new
from quipu.acts import register_core_acts
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.protocols.engine import QuipuEngine
from quipu.spec.exceptions import ExecutionError as CoreExecutionError
~~~~~

~~~~~act
patch_file
packages/pyquipu-application/src/quipu/application/controller.py
~~~~~
~~~~~python.old
class QuipuApplication:
    def __init__(self, work_dir: Path, confirmation_handler: ConfirmationHandler, yolo: bool = False):
        self.work_dir = work_dir
        self.confirmation_handler = confirmation_handler
        self.yolo = yolo
        self.engine: Engine = create_engine(work_dir)
        logger.info(f"Operation boundary set to: {self.work_dir}")

    def _prepare_workspace(self) -> str:
        current_hash = self.engine.git_db.get_tree_hash()

        # 1. 正常 Clean: current_node 存在且与当前 hash 一致
        is_node_clean = (self.engine.current_node is not None) and (
            self.engine.current_node.output_tree == current_hash
        )

        # 2. 创世 Clean: 历史为空 且 当前是空树 (即没有任何文件被追踪)
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        is_genesis_clean = (not self.engine.history_graph) and (current_hash == EMPTY_TREE_HASH)
~~~~~
~~~~~python.new
class QuipuApplication:
    def __init__(self, work_dir: Path, confirmation_handler: ConfirmationHandler, yolo: bool = False):
        self.work_dir = work_dir
        self.confirmation_handler = confirmation_handler
        self.yolo = yolo
        self.engine: QuipuEngine = create_engine(work_dir)
        logger.info(f"Operation boundary set to: {self.work_dir}")

    def _prepare_workspace(self) -> str:
        current_hash = self.engine.git_db.get_tree_hash()

        # 1. 正常 Clean: current_node 存在且与当前 hash 一致
        is_node_clean = (self.engine.current_node is not None) and (
            self.engine.current_node.output_tree == current_hash
        )

        # 2. 创世 Clean: 历史为空 且 当前是空树 (即没有任何文件被追踪)
        is_genesis_clean = (not self.engine.history_graph) and (current_hash == EMPTY_TREE_HASH)
~~~~~

#### Acts 3: 统一 CLI 层常量

清理 `workspace.py` 中的硬编码常量。

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python.old
import typer
from quipu.bus import bus

from ..config import DEFAULT_WORK_DIR
~~~~~
~~~~~python.new
import typer
from quipu.bus import bus
from quipu.spec.constants import EMPTY_TREE_HASH

from ..config import DEFAULT_WORK_DIR
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python.old
        with engine_context(work_dir) as engine:
            current_tree_hash = engine.git_db.get_tree_hash()
            is_node_clean = (engine.current_node is not None) and (engine.current_node.output_tree == current_tree_hash)
            EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            is_genesis_clean = (not engine.history_graph) and (current_tree_hash == EMPTY_TREE_HASH)
~~~~~
~~~~~python.new
        with engine_context(work_dir) as engine:
            current_tree_hash = engine.git_db.get_tree_hash()
            is_node_clean = (engine.current_node is not None) and (engine.current_node.output_tree == current_tree_hash)
            is_genesis_clean = (not engine.history_graph) and (current_tree_hash == EMPTY_TREE_HASH)
~~~~~

#### Acts 4: 统一 Engine 层常量

重构状态机和存储后端，彻底移除硬编码哈希。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
from typing import Any, Dict, List, Optional, Tuple

from quipu.common.identity import get_user_id_from_email
~~~~~
~~~~~python.new
from typing import Any, Dict, List, Optional, Tuple

from quipu.common.identity import get_user_id_from_email
from quipu.spec.constants import EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
    def align(self) -> str:
        # 如果使用 SQLite，先进行数据补水
        if self.db_manager:
            try:
                user_id = self._get_current_user_id()
                hydrator = Hydrator(self.git_db, self.db_manager)
                hydrator.sync(local_user_id=user_id)
            except Exception as e:
                logger.error(f"❌ 自动数据补水失败: {e}", exc_info=True)

        all_nodes = self.reader.load_all_nodes()
        self.history_graph = {node.commit_hash: node for node in all_nodes}
        if all_nodes:
            logger.info(f"从存储中加载了 {len(all_nodes)} 个历史事件，形成 {len(self.history_graph)} 个唯一状态节点。")

        current_hash = self.git_db.get_tree_hash()
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
~~~~~
~~~~~python.new
    def align(self) -> str:
        # 如果使用 SQLite，先进行数据补水
        if self.db_manager:
            try:
                user_id = self._get_current_user_id()
                hydrator = Hydrator(self.git_db, self.db_manager)
                hydrator.sync(local_user_id=user_id)
            except Exception as e:
                logger.error(f"❌ 自动数据补水失败: {e}", exc_info=True)

        all_nodes = self.reader.load_all_nodes()
        self.history_graph = {node.commit_hash: node for node in all_nodes}
        if all_nodes:
            logger.info(f"从存储中加载了 {len(all_nodes)} 个历史事件，形成 {len(self.history_graph)} 个唯一状态节点。")

        current_hash = self.git_db.get_tree_hash()
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
    def capture_drift(self, current_hash: str, message: Optional[str] = None) -> QuipuNode:
        log_message = f"📸 正在捕获工作区漂移 (Message: {message})" if message else "📸 正在捕获工作区漂移"
        logger.info(f"{log_message}，新状态 Hash: {current_hash[:7]}")

        genesis_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        input_hash = genesis_hash
~~~~~
~~~~~python.new
    def capture_drift(self, current_hash: str, message: Optional[str] = None) -> QuipuNode:
        log_message = f"📸 正在捕获工作区漂移 (Message: {message})" if message else "📸 正在捕获工作区漂移"
        logger.info(f"{log_message}，新状态 Hash: {current_hash[:7]}")

        input_hash = EMPTY_TREE_HASH
~~~~~

由于文件较多，我将继续在 `sqlite_storage.py` 和 `git_object_storage.py` 中应用类似的修改。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
from .git_db import GitDB
from .sqlite_db import DatabaseManager
~~~~~
~~~~~python.new
from quipu.spec.constants import EMPTY_TREE_HASH
from .git_db import GitDB
from .sqlite_db import DatabaseManager
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
        # 4. 填充根节点的 input_tree 并排序子节点
        genesis_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        for node in temp_nodes.values():
            if node.parent is None:
                node.input_tree = genesis_hash
            node.children.sort(key=lambda n: n.timestamp)
~~~~~
~~~~~python.new
        # 4. 填充根节点的 input_tree 并排序子节点
        for node in temp_nodes.values():
            if node.parent is None:
                node.input_tree = EMPTY_TREE_HASH
            node.children.sort(key=lambda n: n.timestamp)
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
            parent_info = {}
            if parent_hashes:
                p_placeholders = ",".join("?" * len(parent_hashes))
                p_cursor = conn.execute(
                    f"SELECT commit_hash, output_tree FROM nodes WHERE commit_hash IN ({p_placeholders})",
                    tuple(parent_hashes),
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
~~~~~
~~~~~python.new
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
                    # Set input_tree from parent's output_tree
                    node.input_tree = parent_info.get(parent_hash, EMPTY_TREE_HASH)

                    # Link objects if parent is in the same page
                    if parent_hash in nodes_map:
                        parent_node = nodes_map[parent_hash]
                        node.parent = parent_node
                        parent_node.children.append(node)
                else:
                    node.input_tree = EMPTY_TREE_HASH

                results.append(node)
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
from quipu.engine.git_db import GitDB
from quipu.spec.models.graph import QuipuNode
~~~~~
~~~~~python.new
from quipu.engine.git_db import GitDB
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
        # Phase 2: Link nodes (Same as before)
        for commit_hash, node in temp_nodes.items():
            parent_commit_hash = parent_map.get(commit_hash)
            if parent_commit_hash and parent_commit_hash in temp_nodes:
                parent_node = temp_nodes[parent_commit_hash]
                node.parent = parent_node
                parent_node.children.append(node)
                node.input_tree = parent_node.output_tree
            else:
                node.input_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
~~~~~
~~~~~python.new
        # Phase 2: Link nodes (Same as before)
        for commit_hash, node in temp_nodes.items():
            parent_commit_hash = parent_map.get(commit_hash)
            if parent_commit_hash and parent_commit_hash in temp_nodes:
                parent_node = temp_nodes[parent_commit_hash]
                node.parent = parent_node
                parent_node.children.append(node)
                node.input_tree = parent_node.output_tree
            else:
                node.input_tree = EMPTY_TREE_HASH
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
        # 1. 确定父节点 (Topological Parent)
        # 优先使用 Engine 提供的确切父节点，仅在未提供时回退到 Tree 反查
        parent_commit = kwargs.get("parent_commit_hash")
        if not parent_commit:
            parent_commit = self.git_db.get_commit_by_output_tree(input_tree)

        parents = [parent_commit] if parent_commit else None

        if not parent_commit and input_tree != "4b825dc642cb6eb9a060e54bf8d69288fbee4904":
            logger.warning(
                f"⚠️  Could not find parent commit for input state {input_tree[:7]}. This node may be detached."
            )
~~~~~
~~~~~python.new
        # 1. 确定父节点 (Topological Parent)
        # 优先使用 Engine 提供的确切父节点，仅在未提供时回退到 Tree 反查
        parent_commit = kwargs.get("parent_commit_hash")
        if not parent_commit:
            parent_commit = self.git_db.get_commit_by_output_tree(input_tree)

        parents = [parent_commit] if parent_commit else None

        if not parent_commit and input_tree != EMPTY_TREE_HASH:
            logger.warning(
                f"⚠️  Could not find parent commit for input state {input_tree[:7]}. This node may be detached."
            )
~~~~~

#### Acts 5: 统一测试工具常量

更新 `test_utils`，使其成为常量的分发者，同时确保测试逻辑的一致性。

~~~~~act
patch_file
packages/pyquipu-test-utils/src/quipu/test_utils/helpers.py
~~~~~
~~~~~python.old
from typer.testing import CliRunner

from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter

# --- Constants ---

# The correct hash for an empty git tree.
EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
~~~~~
~~~~~python.new
from typer.testing import CliRunner

from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import HistoryReader, HistoryWriter
~~~~~

### 下一步建议

我们已经完成了所有核心逻辑文件中 `EMPTY_TREE_HASH` 的迁移。为了保持计划的简洁，我没有在本次 Act 中列出对所有测试文件字面量的替换。

如果你同意，我将生成一个后续计划，通过 `run_command` 使用 `sed` 或简单的 Python 脚本一次性清理测试目录下的硬编码字符串，并执行 `[COMMIT]`。在那之后，我们就完成了整个架构重构路线图。
