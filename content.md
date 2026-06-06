好的，测试已经全部顺利通过（包括修复后对齐权重的精准验证）。现在我将为您生成一个 `[COMMIT]` 计划，将所有的修复、性能优化以及集成测试作为一个完整的事务原子地提交到 Git 仓库中。

## [COMMIT] fix(core): 解决分布式相同树哈希状态对齐、可达性查询及导航歧义问题

### 用户需求
将本阶段修改的核心代码和新增的集成测试合并为一个原子事务提交到 Git 仓库，维护版本历史的清洁和规范性。

### 评论
将这一整套修复和质量保证用例进行完整的规范 commit 是对开发流程的最佳实践。它不仅沉淀了对分布式同态状态对齐、CTE 广度联合遍历、以及歧义规避的设计思想，而且通过 Conventional Commit 规范极大地增强了项目的版本溯源质量。

### 目标
1. 将所有相关源文件及测试用例添加至 Git 暂存区。
2. 构造一个符合 Conventional Commit 规范的高质量提交，详细罗列本次在排序权重、多起点 CTE 拓扑联合、导航模糊匹配以及自动化测试等层面的优化与设计。

### 基本原理
我们通过 `git_add` 显式列出本次修改的所有文件，随后通过 block 式的 `git_commit` 传递一份多行、富含细节的规范 Commit 消息，以此来将这一重大稳定性问题在历史中妥善沉淀。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/build #scope/core #scope/dx
#ai/delegate
#task/domain/storage
#task/object/state-alignment
#task/action/bug-fix
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存修改后的核心源文件和测试文件

将参与此次状态对齐、查询与歧义修复的所有源代码以及集成测试文件添加到 Git 暂存区。

~~~~~act
git_add
packages/pyquipu-cli/src/quipu/cli/commands/navigation.py
packages/pyquipu-cli/src/quipu/cli/commands/show.py
packages/pyquipu-engine/src/quipu/engine/state_machine.py
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
packages/pyquipu-cli/tests/integration/test_navigation_commands.py
packages/pyquipu-engine/tests/integration/test_engine.py
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
~~~~~

#### Acts 2: 提交代码到本地仓库

提交以上暂存内容，附带详细描述本次重构细节的 Conventional Commit 日志。

~~~~~act
git_commit
~~~~~
~~~~~text
fix(core): resolve duplicate state alignment, reachability query and checkout ambiguity

Corrects the sorting weight inversion during state-alignment under `reverse=True` descending sort. Changes the sort key from `(0 if parent else 1)` to `(1 if parent else 0)` to ensure connected bones of history are prioritized over detached/orphaned local drift captures when matching equivalent tree hashes.

Refactors SQLite and InMemory HistoryReaders to query and traverse from ALL matching output_tree commits concurrently, merging their ancestor/descendant sets during reachability checks. This prevents TUI views and `--reachable-only` logs from breaking or hiding connected lineages due to non-deterministic single-fetch results.

Enhances CLI `checkout` and `show` to parse prefix matching on `commit_hash` as well, and silently bypass 'notUnique' errors if the multiple matches share the exact same filesystem `output_tree` hash, automatically resolving to the best-connected lineage.

Adds full integration test coverage checking the CLI deduplication, Engine prioritized alignment, and SQLite multi-endpoint CTE query traversals.
~~~~~

### 下一步建议
- **运行同步**：提交完成后，建议在两端分别运行 `quipu sync` 将本地建立的规范历史分支同步到远端，确保多端图谱完美对齐。
- **清理引用**：由于多端同步会产生远程 refs 映射，如果本地需要整理，可以随时运行 `quipu cache prune-refs` 释放无用的本地冗余引用指针。
