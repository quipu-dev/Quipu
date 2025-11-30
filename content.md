你的判断完全正确。

我为之前的错误道歉。测试失败明确地证明了我实现的自动修剪逻辑存在根本性缺陷。它基于一个错误的假设——即历史总是线性的。在分支或从旧节点捕获漂移时，这个逻辑会错误地删除作为分支点的父节点引用，破坏了历史图谱的完整性。

你说得对，最安全、最正确的做法是立即回滚这个有缺陷的自动修剪功能，并保留手动 `prune-refs` 命令作为一个可控的、安全的替代方案。

我将生成一个计划来回滚 `GitObjectHistoryWriter` 中的修改。

## [WIP] revert: 移除有缺陷的自动引用修剪逻辑

### 错误分析
`test_branching_creation` 和 `test_capture_drift_git_object` 的失败暴露了自动引用修剪逻辑的致命缺陷。该逻辑错误地假设新创建节点的父节点总是可以被安全修剪的。然而，在分支场景下（例如从一个共同祖先创建两个不同的子节点），祖先节点必须保留其 `head` 引用，因为它仍然是一个活跃的分支点。当前的实现破坏了这一期望，导致测试失败。

### 用户需求
回滚在 `GitObjectHistoryWriter.create_node` 中引入的自动引用修剪逻辑，恢复到为每个新节点创建 `head` 引用的稳定行为。

### 评论
这是一个正确的工程决策。移除一个已知有缺陷的自动化功能，并提供一个可靠的手动工具 (`prune-refs`)，可以在保证数据安全的前提下，为未来设计更完善的、能感知图谱拓扑的修剪算法留出空间。

### 目标
1.  回滚 `packages/quipu-engine/src/pyquipu/engine/git_object_storage.py` 文件中 `create_node` 方法的修改。

### 基本原理
恢复到为每个节点创建 `head` 引用的策略。虽然这会暂时性地导致引用数量增加，但它保证了历史图谱的绝对完整性和可达性，避免了因错误修剪导致的数据丢失风险。用户可以通过 `quipu cache prune-refs` 命令手动清理线性历史中的冗余引用。

### 标签
#intent/fix #flow/ready #priority/critical #comp/engine #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/ref-management #task/action/revert #task/state/continue

---

### Script

#### Acts 1: 回滚 `GitObjectHistoryWriter` 中的修剪逻辑

我们将恢复 `create_node` 方法中的引用管理部分到其原始的、更简单的状态。

~~~~~act
patch_file
packages/quipu-engine/src/pyquipu/engine/git_object_storage.py
~~~~~
~~~~~python
        # 3. 引用管理 (QDPS v1.1 - Local Heads Namespace with Pruning)
        # 在本地工作区命名空间中为新的 commit 创建一个持久化的 head 引用。
        self.git_db.update_ref(f"refs/quipu/local/heads/{new_commit_hash}", new_commit_hash)

        # 4. 修剪父节点的冗余 head 引用
        # 新的 head 引用保证了其父节点的可达性，因此父节点的 head 引用变得冗余，可以被安全移除。
        # 这确保了只有图谱的叶子节点才持有 head 引用，显著减少了 ref 数量。
        if parent_commit:
            parent_ref = f"refs/quipu/local/heads/{parent_commit}"
            self.git_db.delete_ref(parent_ref)
            logger.debug(f"Pruned redundant parent ref: {parent_ref}")

        logger.info(f"✅ History node created as commit {new_commit_hash[:7]}")
~~~~~
~~~~~python
        # 3. 引用管理 (QDPS v1.1 - Local Heads Namespace)
        # 在本地工作区命名空间中为新的 commit 创建一个持久化的 head 引用。
        # 这是 push 操作的唯一来源，并且支持多分支图谱，因此不再删除父节点的 head。
        self.git_db.update_ref(f"refs/quipu/local/heads/{new_commit_hash}", new_commit_hash)

        logger.info(f"✅ History node created as commit {new_commit_hash[:7]}")
~~~~~

### 下一步建议
执行此计划后，所有的测试应该都能通过。`quipu cache prune-refs` 命令仍然可用，作为手动清理冗余引用的工具。
