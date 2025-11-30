好的，我们来分析并实现 `性能优化：tree写入.md` 中描述的高性能 `checkout` 方案。

你的分析文档完全正确。当前 `checkout` 的实现方式虽然有效，但在处理大型仓库时性能较低，因为它执行的是“tree-vs-working-directory”的完全同步。我们可以通过实现文档中建议的“方式二：使用底层命令”，利用 `git read-tree -m` 将其升级为高效的“tree-vs-tree”比较，从而只更新发生变更的文件。

这将是一次对核心性能至关重要的重构。

## [WIP] perf: 优化 checkout 性能，实现 tree-vs-tree 高效切换

### 用户需求
根据 `性能优化：tree写入.md` 文件的分析，需要重构 `quipu-engine` 的 `checkout` 逻辑。目标是利用 Git 的 `tree-vs-tree` 差异比较能力，替换当前“将工作目录强制重置为目标 Tree”的低效实现，从而在切换历史状态时，只对发生变更的文件进行 I/O 操作，大幅提升性能。

### 评论
这是一个关键的性能优化。对于拥有大量文件（如大型代码库、数据集）的工作区而言，每次 `checkout` 都全量写入是不可接受的。实现 tree-vs-tree 的高效切换，将使得 Quipu 在真实世界的复杂项目中的可用性提升一个数量级，是实现“将 Linux 内核仓库作为 Quipu 工作区”这类场景的必要前提。

### 目标
1.  修改 `pyquipu.engine.git_db.GitDB.checkout_tree` 方法，使其能接受一个可选的 `old_tree_hash` 参数。
2.  当 `old_tree_hash` 被提供时，使用 `git read-tree -m <old_tree> <new_tree>` 命令来高效地更新 Git 索引。
3.  当 `old_tree_hash` 未提供时，平滑回退到现有的 `git read-tree <new_tree>` 逻辑，确保向后兼容。
4.  更新上层调用者 `pyquipu.engine.state_machine.Engine.checkout`，在执行切换时，传入当前状态的 `tree_hash` 作为 `old_tree_hash`。

### 基本原理
优化的核心在于改变与 Git 交互的方式。我们不再简单地命令 Git：“让工作目录变成 `new_tree` 的样子”，而是更精确地告诉它：“计算出从 `old_tree` 变为 `new_tree` 所需的最小变更集，并只应用这些变更”。

`git read-tree -m old_tree new_tree` 指令正是为此设计的。它在 Git 内部（内存和索引文件）高效地完成了 Tree 的 diff 操作，并生成了一个更新后的索引。随后的 `git checkout-index -a -f` 则只需根据这个已经包含“最小变更集”的索引来更新工作目录，从而避免了对未变更文件的不必要I/O操作。通过 `Engine` 中维护的 `.quipu/HEAD` 文件，我们可以轻易获取 `old_tree_hash`，将这个优化无缝集成到现有的工作流中。

### 标签
#intent/refine #flow/ready #priority/high
#comp/engine #concept/state #concept/navigation #scope/core
#ai/instruct
#task/domain/storage #task/object/checkout-performance #task/action/optimization #task/state/begin

---

### Script

#### Acts 1: 增强 `GitDB.checkout_tree` 以支持 tree-vs-tree 模式

我们将首先修改底层的 `git_db.py`。新的 `checkout_tree` 方法将接受一个可选的 `old_tree_hash`，并根据其是否存在来决定是走快速路径还是慢速路径。

~~~~~act
patch_file
packages/quipu-engine/src/pyquipu/engine/git_db.py
~~~~~
~~~~~python
    def checkout_tree(self, tree_hash: str):
        """
        将工作区强制重置为目标 Tree 的状态。
        这是一个底层方法，上层应确保工作区的未提交更改已被处理。
        """
        bus.info("engine.git.info.checkoutStarted", short_hash=tree_hash[:7])

        # 1. 使用 read-tree 更新索引，这是一个安全的操作
        self._run(["read-tree", tree_hash])

        # 2. 从更新后的索引检出文件，-a (all) -f (force)
        self._run(["checkout-index", "-a", "-f"])
~~~~~
~~~~~python
    def checkout_tree(self, new_tree_hash: str, old_tree_hash: Optional[str] = None):
        """
        将工作区强制重置为目标 Tree 的状态。
        如果提供了 old_tree_hash，将执行 tree-vs-tree 高效 diff，只更新变更文件。
        否则，回退到全量更新。
        """
        bus.info("engine.git.info.checkoutStarted", short_hash=new_tree_hash[:7])

        # 1. 更新索引。根据是否存在 old_tree_hash 选择不同策略。
        if old_tree_hash:
            # 快速路径: tree-vs-tree diff, 只更新索引中的差异项
            logger.debug(f"执行 tree-vs-tree 高效检出: {old_tree_hash[:7]} -> {new_tree_hash[:7]}")
            # 注意：这里的参数顺序是 -m <stage1_tree> <stage2_tree> ...
            # 在两路合并的场景下，可以理解为 old -> new
            self._run(["read-tree", "-m", old_tree_hash, new_tree_hash])
        else:
            # 慢速路径: 将整个新 tree 读入索引
            logger.debug(f"执行全量检出: {new_tree_hash[:7]}")
            self._run(["read-tree", new_tree_hash])

        # 2. 从更新后的索引检出文件，-a (all) -f (force)
        # 此时 checkout-index 只会操作在 read-tree 步骤中被标记为已更改的文件
        self._run(["checkout-index", "-a", "-f"])
~~~~~

#### Acts 2: 更新 `Engine.checkout` 以利用性能优化

现在，我们需要修改 `state_machine.py` 中的上层逻辑，使其在调用 `checkout_tree` 时传入当前工作区的 `tree_hash`。我们可以通过 `_read_head()` 方法方便地获取这个值。

~~~~~act
patch_file
packages/quipu-engine/src/pyquipu/engine/state_machine.py
~~~~~
~~~~~python
    def checkout(self, target_hash: str):
        self.git_db.checkout_tree(target_hash)
        self._write_head(target_hash)
        self.current_node = None
        for node in self.history_graph.values():
            if node.output_tree == target_hash:
                self.current_node = node
                break
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
~~~~~
~~~~~python
    def checkout(self, target_hash: str):
        # 获取切换前的 tree hash 作为 "old_tree"
        current_head_hash = self._read_head()

        # 调用已优化的 checkout_tree 方法
        self.git_db.checkout_tree(new_tree_hash=target_hash, old_tree_hash=current_head_hash)

        self._write_head(target_hash)
        self.current_node = None
        for node in self.history_graph.values():
            if node.output_tree == target_hash:
                self.current_node = node
                break
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
~~~~~

### 下一步建议
我们已经完成了核心逻辑的重构。现在最关键的步骤是验证其正确性和性能提升。

1.  **功能测试**: 需要编写一个新的集成测试，模拟一个包含不变文件和变更文件的仓库。在执行 `checkout` 后，断言：
    *   变更文件内容已更新。
    *   不变文件的 `mtime` (修改时间) **没有** 发生变化。这可以通过 `os.path.getmtime` 来验证，是优化是否生效的决定性证据。
2.  **性能基准测试 (可选但推荐)**: 在一个大型仓库上（例如，克隆一个 linux kernel 仓库），对优化前后的 `checkout` 操作进行计时，量化性能提升。

如果你同意，我将为你生成实现上述功能测试的计划。
