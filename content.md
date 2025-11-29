您说得对，这确实是个问题。我的上一步重构操作存在疏漏，破坏了测试套件的完整性。

在创建 `tests/helpers.py` 以整合 Git 相关测试的辅助函数时，我没有将 `tests/engine/test_engine_memory.py` 所依赖的**内存测试**辅助类 (`InMemoryDB`, `InMemoryHistoryManager`) 一并迁移进来。这导致 `test_engine_memory.py` 在尝试从新的 `helpers.py` 导入这些类时失败，引发了您看到的 `ImportError`。

我将立即修正这个问题，将这些缺失的内存测试辅助类添加到 `tests/helpers.py` 中，从而将**所有**测试辅助工具都集中到这个统一的模块里，完成我们最初的重构目标。

## [WIP] fix: 将内存测试辅助类合并到 tests/helpers.py

### 错误分析
在 `refactor(tests): 提取共享的测试辅助函数` 这次提交中，创建 `tests/helpers.py` 时只考虑了依赖真实 Git 环境的测试，遗漏了 `test_engine_memory.py` 所需的、用于模拟后端的 `InMemoryDB` 和 `InMemoryHistoryManager` 类。这导致 `test_engine_memory.py` 模块在导入阶段就因找不到依赖而失败，中断了测试集。

### 用户需求
修复 `ImportError`，让 `pytest` 能够正常收集并运行所有测试。

### 评论
这是一个典型的重构疏漏，它凸显了在进行大规模代码移动时，必须对所有依赖关系进行全面检查的重要性。幸运的是，测试套件在执行前就通过收集错误暴露了这个问题，避免了更深层次的逻辑错误。

### 目标
1.  在 `tests/helpers.py` 文件中实现 `InMemoryDB` 和 `InMemoryHistoryManager` 两个类。
2.  确保 `test_engine_memory.py` 可以从 `tests.helpers` 成功导入所有需要的组件。
3.  恢复测试套件的正常运行。

### 基本原理
我们将重写 `tests/helpers.py` 文件，在保留现有 Git 辅助函数的基础上，补充实现一套完整的、功能最小化的内存后端模拟。这些模拟类将实现 `GitDB`、`HistoryReader` 和 `HistoryWriter` 的核心接口，足以支撑 `test_engine_memory.py` 中的测试用例运行，同时将所有测试辅助代码整合到单一文件中。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-helpers #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 增强 `tests/helpers.py` 以包含内存后端模拟

我们将重写 `tests/helpers.py`，将缺失的类定义添加进去。

~~~~~act
write_file tests/helpers.py
~~~~~
~~~~~python
import hashlib
import copy
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from quipu.engine.state_machine import Engine
from quipu.interfaces.models import QuipuNode
from quipu.interfaces.storage import HistoryReader, HistoryWriter

# --- Constants ---

EMPTY_TREE_HASH = "4b825dc642cb642cb6eb9a060e54bf8d69288fbee4904"


# --- Git-based Test Helpers ---


def create_plan_node_with_change(
    engine: Engine, parent_hash: str, file_name: str, content: str, message: str
) -> str:
    """
    Creates a file change in the workspace and generates a new Plan node.
    Returns the output_tree hash of the new node.
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.create_plan_node(input_tree=parent_hash, output_tree=new_hash, plan_content=message)
    return new_hash


def create_capture_node_with_change(engine: Engine, file_name: str, content: str, message: str) -> str:
    """
    Creates a file change in the workspace and generates a new Capture node.
    The new node is parented to the current HEAD of the engine.
    Returns the output_tree hash of the new node.
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.capture_drift(new_hash, message=message)
    return new_hash


# --- In-Memory Backend Mocks for Engine Testing ---


class InMemoryVFS:
    """A simple in-memory virtual file system."""

    def __init__(self):
        self.files: Dict[str, str] = {}

    def write(self, path: str, content: str):
        self.files[path] = content

    def read(self, path: str) -> Optional[str]:
        return self.files.get(path)


class InMemoryDB:
    """A mock of GitDB that operates entirely in memory."""

    def __init__(self):
        self.vfs = InMemoryVFS()
        self.trees: Dict[str, Dict[str, str]] = {EMPTY_TREE_HASH: {}}

    def get_tree_hash(self) -> str:
        """Computes a stable hash for the current VFS state."""
        if not self.vfs.files:
            return EMPTY_TREE_HASH
        stable_repr = "".join(f"{p}:{c}" for p, c in sorted(self.vfs.files.items()))
        h = hashlib.sha1(stable_repr.encode()).hexdigest()
        # Store a snapshot of the VFS for potential checkout
        self.trees[h] = copy.deepcopy(self.vfs.files)
        return h

    def checkout_tree(self, tree_hash: str):
        """Restores the VFS to a previously stored state."""
        self.vfs.files = copy.deepcopy(self.trees.get(tree_hash, {}))


class InMemoryHistoryManager(HistoryReader, HistoryWriter):
    """A mock of history storage that operates entirely in memory."""

    def __init__(self, db: InMemoryDB):
        self.db = db
        self.nodes: Dict[str, QuipuNode] = {}  # commit_hash -> QuipuNode

    def create_node(
        self,
        node_type: str,
        input_tree: str,
        output_tree: str,
        content: str,
        summary_override: Optional[str] = None,
        **kwargs,
    ) -> QuipuNode:
        # Create a unique but deterministic-looking hash
        commit_hash_content = f"{node_type}{input_tree}{output_tree}{content}{time.time()}"
        commit_hash = hashlib.sha1(commit_hash_content.encode()).hexdigest()

        node = QuipuNode(
            commit_hash=commit_hash,
            output_tree=output_tree,
            input_tree=input_tree,
            timestamp=datetime.now(),
            filename=Path(commit_hash),
            node_type=node_type,
            summary=summary_override or content.splitlines()[0],
            content=content,
        )
        self.nodes[commit_hash] = node
        return node

    def load_all_nodes(self) -> List[QuipuNode]:
        # Simple load, but reconstruct parent-child links
        nodes_by_output = {n.output_tree: n for n in self.nodes.values()}
        for node in self.nodes.values():
            if node.input_tree in nodes_by_output:
                parent = nodes_by_output[node.input_tree]
                node.parent = parent
                if node not in parent.children:
                    parent.children.append(node)
        return sorted(list(self.nodes.values()), key=lambda n: n.timestamp)

    # --- Unused abstract methods ---
    def get_node_count(self) -> int:
        return len(self.nodes)

    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]:
        all_nodes = self.load_all_nodes()
        return all_nodes[offset : offset + limit]

    def find_nodes(self, **kwargs) -> List[QuipuNode]:
        return []

    def get_node_content(self, node: QuipuNode) -> str:
        return node.content

    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        return set()

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        return set()
~~~~~

### 下一步建议
修正已完成。请再次运行测试套件，确认 `ImportError` 已解决，并且所有测试都能正常运行。测试通过后，我们就可以提交这次修复了。
