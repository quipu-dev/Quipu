好的，测试已通过。`pytest.mark.timeout` 的警告是因为环境中可能没有安装 `pytest-timeout` 插件，但核心的逻辑测试是成功的。

现在，我将为你生成提交这些修复和测试的最终计划。

## fix(engine)+test: 防止 SQLite 因循环引用数据导致 UI 挂起

### 错误分析

在之前的实现中，`SQLiteHistoryReader` 从数据库的 `nodes` 和 `edges` 表重建内存中的历史图谱。如果 `edges` 表中存在被破坏的数据（例如，一个节点的 `child_hash` 和 `parent_hash` 相同），`load_all_nodes` 方法会构建一个包含循环引用的 `QuipuNode` 对象。上层应用（如 `quipu ui`）在遍历这个图谱的父节点时（例如，为了计算可达性），会陷入无限循环，导致程序挂起。

### 用户需求

为刚刚完成的 bug 修复和新增的单元测试创建一个 Git 提交。

### 评论

这是一个至关重要的稳定性修复。它确保了即使底层数据缓存损坏，数据读取层也能够保持健壮，不会将结构性错误传递给上层应用。新增的回归测试将永久性地防止此类问题再次发生。

### 目标

将以下变更提交到版本历史中：
1.  对 `packages/quipu-engine/src/quipu/core/sqlite_storage.py` 的修改，增加了在图重建过程中对自引用边的检查。
2.  新增测试文件 `tests/test_sqlite_reader_integrity.py`，其中包含一个用于模拟和验证此修复的单元测试。

### 基本原理

通过 `git add` 将修改后的文件和新文件暂存，然后使用 `git commit` 将这些变更作为一个原子单元提交。提交信息遵循了 Conventional Commits 规范，清晰地说明了本次提交的类型（修复与测试）和内容。

### 标签

#intent/fix #intent/tooling #flow/done #priority/critical
#comp/engine #comp/tests #concept/history #scope/core
#ai/refine
#task/domain/storage
#task.object/sqlite-backend
#task.action/bug-fix
#task/state/continue

---

### Script

#### Acts 1: 提交修复与测试

~~~~~act
git_add
~~~~~
~~~~~text
packages/quipu-engine/src/quipu/core/sqlite_storage.py
tests/test_sqlite_reader_integrity.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(engine)+test: 防止 SQLite 因循环引用数据导致 UI 挂起

修复了 `SQLiteHistoryReader` 在重建图谱时的一个严重问题。
如果 `edges` 表中存在自引用记录（即 child_hash == parent_hash），
之前的逻辑会创建一个带循环引用的内存图谱，导致上层应用（如 UI）
在遍历父节点时无限循环。

本次提交通过在图重建逻辑中增加一个检查来忽略这类损坏的边，
从而解决了此问题。

同时，新增了单元测试 `test_sqlite_reader_integrity.py`，
专门用于模拟这种数据损坏情况，以确保此问题不会再次出现。
~~~~~

### 下一步建议

提交完成后，当前的 bug 修复任务就完成了。我们可以继续推进 UI 性能优化的其他步骤，或者你可以提出新的开发需求。

关于 `pytest.mark.timeout` 的警告，如果你希望消除它并让超时功能生效，可以在 `dev-requirements.txt` 中添加 `pytest-timeout` 依赖。
