# refactor: Integrate Git Object Storage into Engine via dynamic factory

## 用户需求
系统目前硬编码使用基于文件系统的历史记录存储。我需要更新系统，使其能够无缝地使用新开发的、基于 Git 底层对象的存储后端 (`GitObjectHistoryWriter` / `Reader`)。

系统应该能够自动检测项目正在使用哪种存储格式，并加载相应的实现。对于新创建的项目，应默认使用新的 Git 对象存储格式。

## 评论
这是存储层改造计划的最后一步，它将激活新的存储后端，使其成为默认选项。通过实现一个动态的“存储策略工厂”，我们遵循了“组合优于继承”和“依赖注入”的设计原则，使 `Engine` 核心与具体的存储实现完全解耦，增强了系统的可维护性和可扩展性。

## 目标
1.  在 `quipu-cli` 模块中实现一个工厂函数，该函数能够：
    *   检测项目的历史记录存储格式 (新的 Git ref 格式 vs. 旧的 `.md` 文件格式)。
    *   根据检测结果，实例化并返回正确的 `HistoryReader` 和 `HistoryWriter` 实现。
    *   为新项目默认提供 `GitObjectHistoryReader/Writer`。
2.  重构 `Engine`，将历史记录的 Git Commit 创建职责完全委托给 `HistoryWriter` 接口，消除现有代码中的逻辑重复。
3.  将此工厂函数集成到 CLI 的启动流程中，完成新旧存储后端的无缝切换。

## 基本原理
我们将采用“策略模式”来管理不同的存储实现。`Engine` 类将依赖于 `HistoryReader` 和 `HistoryWriter` 这两个抽象接口，而不关心其具体实现。

在 `quipu-cli` 的 `main.py` 中，我们将创建一个 `_setup_engine` 工厂函数。此函数是系统中唯一一个需要知道所有具体存储策略（`FileSystem...` 和 `GitObject...`）的地方。它的职责是：

1.  **检测 (Detect)**: 通过检查 `refs/quipu/history` 是否存在来判断是否为新格式。如果不存在，则回退检查 `.quipu/history/` 目录是否存在以判断是否为旧格式。
2.  **决策 (Decide)**: 根据检测结果选择要使用的策略类。
3.  **注入 (Inject)**: 实例化选择好的策略类，并将它们作为依赖注入到 `Engine` 的构造函数中。

同时，为了确保职责单一，我们将从 `Engine` 中移除创建历史 Git Commit 的逻辑，因为这个职责现在完全由 `GitObjectHistoryWriter` 承担。这使得 `Engine` 更专注于业务流程编排，而 `Writer` 专注于持久化。

## 标签
#comp/engine #comp/cli #concept/history #scope/core

---

## Script

### Acts 1: 增强 `GitDB` 以支持存储格式检测

为了让工厂函数能够检测项目是否在使用新的 Git 对象存储，我们需要在 `GitDB` 中添加一个辅助方法来检查 `refs/quipu/history` 引用是否存在。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_db.py
~~~~~
~~~~~python
    def get_all_ref_heads(self, prefix: str) -> List[str]:
        """查找指定前缀下的所有 ref heads 并返回其 commit 哈希。"""
        res = self._run(["for-each-ref", f"--format=%(objectname)", prefix], check=False)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        return res.stdout.strip().splitlines()

    def log_ref(self, ref_names: Union[str, List[str]]) -> List[Dict[str, str]]:
        """获取指定引用的日志，并解析为结构化数据列表。"""
~~~~~
~~~~~python
    def get_all_ref_heads(self, prefix: str) -> List[str]:
        """查找指定前缀下的所有 ref heads 并返回其 commit 哈希。"""
        res = self._run(["for-each-ref", f"--format=%(objectname)", prefix], check=False)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        return res.stdout.strip().splitlines()

    def has_quipu_ref(self) -> bool:
        """检查是否存在任何 'refs/quipu/' 引用，用于判断存储格式。"""
        # We use show-ref and check the exit code. Exit 0 if refs exist, 1 otherwise.
        res = self._run(["show-ref", "--verify", "--quiet", "refs/quipu/"], check=False, log_error=False)
        return res.returncode == 0

    def log_ref(self, ref_names: Union[str, List[str]]) -> List[Dict[str, str]]:
        """获取指定引用的日志，并解析为结构化数据列表。"""
~~~~~

### Acts 2: 重构 `Engine` 以委托 Git Commit 创建职责

当前 `Engine` 的 `capture_drift` 和 `create_plan_node` 方法中包含了创建 Git Commit 的逻辑，这与 `GitObjectHistoryWriter` 的职责重复了。我们将移除这部分代码，使 `Engine` 只负责调用 `writer` 接口。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~
~~~~~python
        new_node = self.writer.create_node(
            node_type="capture",
            input_tree=input_hash,
            output_tree=current_hash,
            content=body,
            message=message
        )

        last_commit_hash = None
        res = self.git_db._run(["rev-parse", "refs/quipu/history"], check=False)
        if res.returncode == 0:
            last_commit_hash = res.stdout.strip()
        commit_msg = f"Axon Save: {message}" if message else f"Axon Capture: {current_hash[:7]}"
        parents = [last_commit_hash] if last_commit_hash else None
        new_commit_hash = self.git_db.commit_tree(current_hash, parent_hashes=parents, message=commit_msg)
        self.git_db.update_ref("refs/quipu/history", new_commit_hash)

        self.history_graph[current_hash] = new_node
        self.current_node = new_node
~~~~~
~~~~~python
        new_node = self.writer.create_node(
            node_type="capture",
            input_tree=input_hash,
            output_tree=current_hash,
            content=body,
            message=message
        )

        self.history_graph[current_hash] = new_node
        self.current_node = new_node
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~
~~~~~python
        new_node = self.writer.create_node(
            node_type="plan",
            input_tree=input_tree,
            output_tree=output_tree,
            content=plan_content
        )

        parent_commit = None
        try:
            res = self.git_db._run(["rev-parse", "refs/quipu/history"], check=False)
            if res.returncode == 0:
                parent_commit = res.stdout.strip()
        except Exception: pass
        commit_msg = f"Axon Plan: {output_tree[:7]}"
        parents = [parent_commit] if parent_commit else None
        new_commit_hash = self.git_db.commit_tree(output_tree, parent_hashes=parents, message=commit_msg)
        self.git_db.update_ref("refs/quipu/history", new_commit_hash)

        self.history_graph[output_tree] = new_node
        self.current_node = new_node
~~~~~
~~~~~python
        new_node = self.writer.create_node(
            node_type="plan",
            input_tree=input_tree,
            output_tree=output_tree,
            content=plan_content
        )

        self.history_graph[output_tree] = new_node
        self.current_node = new_node
~~~~~

### Acts 3: 在 CLI 层实现存储策略工厂

现在，我们在 `quipu-cli` 的 `main.py` 中重写 `_setup_engine` 函数，将其改造为一个能够根据项目状态选择并注入正确存储策略的工厂。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
from quipu.core.state_machine import Engine
from quipu.core.history import load_all_history_nodes
from quipu.core.models import QuipuNode
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
import inspect
import subprocess
~~~~~
~~~~~python
from quipu.core.state_machine import Engine
from quipu.core.history import load_all_history_nodes
from quipu.core.models import QuipuNode
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.core.git_db import GitDB
import inspect
import subprocess
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
def _setup_engine(work_dir: Path) -> Engine:
    """辅助函数：实例化完整的 Engine 堆栈"""
    real_root = _resolve_root(work_dir)
    # 注意: 当前硬编码为文件系统存储。未来这里可以加入逻辑来检测项目类型。
    history_dir = real_root / ".quipu" / "history"
    reader = FileSystemHistoryReader(history_dir)
    writer = FileSystemHistoryWriter(history_dir)
    engine = Engine(real_root, reader=reader, writer=writer)
    engine.align()  # 对齐以加载历史图谱
    return engine
~~~~~
~~~~~python
def _setup_engine(work_dir: Path) -> Engine:
    """
    辅助函数：实例化完整的 Engine 堆栈。
    自动检测存储格式 (Git Object vs. File System) 并加载相应后端。
    """
    real_root = _resolve_root(work_dir)
    
    # 1. 创建 GitDB 实例用于检测和注入
    git_db = GitDB(real_root)
    
    # 2. 检测存储格式并选择策略
    # 优先检测新格式 (Git refs)
    if git_db.has_quipu_ref():
        logger.debug("Detected Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
    # 回退检测旧格式 (FS directory)
    elif (real_root / ".quipu" / "history").exists():
        logger.debug("Detected File System storage format (legacy).")
        history_dir = real_root / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
    # 默认在新项目中使用新格式
    else:
        logger.debug("No existing history found. Defaulting to Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)

    # 3. 注入依赖并实例化 Engine
    engine = Engine(real_root, reader=reader, writer=writer)
    engine.align()  # 对齐以加载历史图谱
    return engine
~~~~~