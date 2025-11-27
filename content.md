好的，测试已经验证了我们的重构是成功的。现在，我将为你创建这次重构和测试的提交。

## refactor(engine)+test: 显式传递父节点以修复幂等操作的父子关系

### 错误分析
在 `quipu-engine` 的写入流程中，`SQLiteHistoryWriter` 依赖于通过 `output_tree` 哈希反查 Git 来确定父节点。这个机制在幂等操作（即 `input_tree == output_tree`）时会失效，因为 Git 中存在多个 Commit 指向同一个 Tree。这导致写入器错误地将新创建的节点记录为它自己的父节点，在数据库中形成自引用边，从而破坏了历史图谱的结构。

### 用户需求
为修复幂等操作 bug 的重构代码和新增的单元测试创建一个 Git 提交。

### 评论
这是一个关键的架构级修复。通过将“隐式反查”改为“显式传递”，我们从根本上消除了数据流中的歧义性，确保了无论操作类型如何，历史图谱的父子关系都能被准确无误地记录下来。新增的单元测试将为这个核心逻辑提供长期的保障。

### 目标
将以下变更提交到版本历史中：
1.  对 `packages/quipu-engine/src/quipu/core/git_object_storage.py` 的修改，使其在返回的 `QuipuNode` 中包含父节点引用。
2.  对 `packages/quipu-engine/src/quipu/core/sqlite_storage.py` 的修改，使其使用传递来的父节点引用，而不是反查。
3.  新增测试文件 `tests/test_sqlite_writer_idempotency.py`，用于验证此修复的正确性。

### 基本原理
通过 `git add` 暂存所有相关文件，然后使用 `git commit` 将这些逻辑上关联的变更作为一个原子单元提交到版本库中。

### 标签
#intent/refine #intent/tooling #flow/done #priority/high
#comp/engine #comp/tests #concept/state #scope/core
#ai/instruct
#task/domain/storage
#task.object/sqlite-backend
#task.action/bug-fix
#task/state/end

---

### Script

#### Acts 1: 提交重构与测试

~~~~~act
git_add
~~~~~
~~~~~text
packages/quipu-engine/src/quipu/core/git_object_storage.py
packages/quipu-engine/src/quipu/core/sqlite_storage.py
tests/test_sqlite_writer_idempotency.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(engine)+test: 显式传递父节点以修复幂等操作的父子关系

重构了 `quipu-engine` 的写入流程，以解决在幂等操作中父子关系记录错误的问题。

问题根源在于 `SQLiteHistoryWriter` 依赖 `output_tree` 反查父节点，
当 `input_tree == output_tree` 时，此反查会错误地返回当前节点自身，
导致在数据库中形成自引用边，破坏了历史图谱。

本次修改通过以下方式解决此问题：
1. `GitObjectHistoryWriter` 现在会在返回的 `QuipuNode` 对象中显式地
   附加一个包含父 Commit 哈希的 `parent` 引用。
2. `SQLiteHistoryWriter` 被修改为直接使用这个传递来的 `parent`
   引用来记录边关系，完全移除了不稳定的反查逻辑。

新增了 `test_sqlite_writer_idempotency.py` 单元测试，专门用于
验证在连续进行幂等操作时，父子链能够被正确地线性记录。
~~~~~

### 下一步建议
这个关于 SQLite 存储后端的 bug 修复任务已经完成。现在 `engine` 层的稳定性和数据一致性得到了显著提升。我们可以放心地继续进行 `quipu ui` 的性能优化工作了。
