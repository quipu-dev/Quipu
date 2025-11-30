好的，测试已全部通过。我们已经成功地重构了 `checkout` 逻辑，使其兼具高性能和健壮性。现在，我们将把这一系列的工作成果作为一个完整的单元进行提交。

## [COMMIT] perf(engine): Optimize checkout with robust read-tree --reset

### 用户需求
重构 `checkout` 核心逻辑，以解决性能瓶颈和在“脏”工作区/索引状态下操作失败的问题。

### 评论
这是一个里程碑式的改进。通过切换到 `git read-tree --reset -u`，我们不仅获得了数量级的性能提升（尤其是在大型仓库中），还从根本上解决了因用户本地 `git add` 操作而导致的 `checkout` 崩溃问题。这使得 Quipu 的核心“时间旅行”功能在真实、复杂的开发环境中变得稳定可靠。

### 目标
1.  已将 `pyquipu/engine/git_db.py` 中的 `checkout_tree` 方法重构为使用 `git read-tree --reset -u`。
2.  已修复 `tests/helpers.py` 中 `InMemoryDB` 的接口以兼容此变更。
3.  已创建 `tests/engine/test_checkout_behavior.py`，添加了专门的测试用例来验证新逻辑在脏索引下的健壮性和对未变更文件 mtime 的保护。
4.  将所有相关变更提交到版本历史。

### 基本原理
我们放弃了之前脆弱的、基于 `read-tree -m` 的两步合并法，因为它对当前索引的“干净”状态有严格要求。新的实现采用了 `git read-tree --reset -u <new_tree>` 这一更为健壮和高效的 Git 底层命令。`--reset` 标志强制覆盖任何本地未提交的变更（包括暂存区的），解决了 `Entry not uptodate` 错误；`-u` 标志则智能地更新工作目录，它会对比当前索引和目标树，只对真正发生变化的文件执行 I/O 操作，从而实现了我们追求的性能优化。

### 标签
#intent/refine #intent/fix #flow/ready
#comp/engine #comp/tests #concept/state #concept/navigation #scope/core
#ai/instruct
#task/domain/storage #task/object/checkout-performance #task/action/optimization #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存所有变更

我们将本次重构涉及的所有文件添加到 Git 暂存区。

~~~~~act
git_add
packages/quipu-engine/src/pyquipu/engine/git_db.py
tests/helpers.py
tests/engine/test_checkout_behavior.py
~~~~~

#### Acts 2: 创建提交

现在，我们创建一个内容详尽的提交，记录这次重要的优化。

~~~~~act
git_commit
~~~~~
~~~~~text
perf(engine): Optimize checkout with robust read-tree --reset

Refactors the core `checkout_tree` logic for significantly improved performance and robustness.

Previously, the checkout operation was either a full, inefficient write of the entire tree or a fragile two-step merge using `read-tree -m`. The merge-based approach would fail with an "Entry not uptodate" error if the user's Git index contained staged changes, making the operation unreliable in real-world scenarios.

This commit replaces the complex logic with a single, powerful command: `git read-tree --reset -u <new_tree>`.

This approach provides two key benefits:
1.  **Robustness**: The `--reset` flag ensures that any local modifications or staged changes in the index are forcefully overwritten, preventing merge conflicts and making the checkout operation atomic and predictable.
2.  **Performance**: The `-u` flag intelligently updates the working directory by comparing the current index with the target tree. It only performs I/O on files that have actually changed, preserving the modification times (mtime) of unchanged files and drastically reducing checkout times in large repositories.

Additionally, new integration tests have been added to verify both the robustness against a dirty index and the mtime-based performance optimization.
~~~~~
