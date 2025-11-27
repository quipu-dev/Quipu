好的，我们将创建一个提交来正式结束这次重构。

## refactor(core): 最终完成标识符模糊性问题的解决

### 用户需求
用户要求创建一个 Git 提交，以封装最近所有关于标识符模糊性问题的修复和重构，并正式标志此宏观任务的结束。

### 评论
这个提交标志着一次关键架构重构的成功完成。通过建立清晰的 API 契约和数据模型，系统的长期可维护性和开发者体验得到了显著提升。

### 目标
在 Git 历史中创建一个原子性的、描述清晰的提交，记录本次重构的所有变更。

### 基本原理
使用 `git add` 和 `git_commit` 指令将当前工作区的所有变更暂存并提交，完成版本控制周期。

### 标签
#intent/refine #flow/ready #priority/high
#comp/engine #comp/cli #comp/interfaces #concept/history #scope/api
#ai/instruct
#task/domain/storage #task/object/api-contract #task/action/refactor
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交所有变更

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~message
refactor(core): Resolve identifier ambiguity

This commit concludes a major refactoring to eliminate the ambiguity between 'commit_hash' and 'output_tree_hash' throughout the Quipu codebase.

Key changes:
- QuipuNode now explicitly includes 'commit_hash'.
- HistoryReader APIs are updated with precise parameter names (e.g., 'get_ancestor_output_trees').
- Upper layers (ViewModel, TUI, CLI) are adapted to use the new explicit identifiers.
- Removed reliance on parsing 'QuipuNode.filename' to derive the commit hash.

This change significantly improves the clarity and robustness of the core data model and storage interfaces, reducing the risk of future bugs related to identifier confusion.
~~~~~

### 下一步建议
标识符重构任务已完成。我们可以继续推进下一个宏观任务，例如 `Quipu Sync` 架构的实现或 `SQLite` 存储的进一步完善。
