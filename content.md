好的，所有测试已通过，功能已完成。现在我们将把这些变更作为一个完整的单元进行提交。

## [COMMIT] feat(cli): 实现多种 sync 模式以支持灵活的协作工作流

### 用户需求
为了适应不同的协作场景，`quipu sync` 命令需要提供比默认双向同步更精细的控制。具体需求包括：
1.  **单向推送 (`push-only`)**: 仅将本地变更推送到远程，用于备份或单向发布。
2.  **单向拉取 (`pull-only`)**: 仅从远程拉取并调和变更，不推送本地节点，用于只读订阅或在推送前审查。
3.  **强制推送 (`push-force`)**: 强制用本地 `local/heads` 覆盖远程用户目录，用于修复错误或重置远程历史。
4.  **拉取并修剪 (`pull-prune`)**: 在拉取后，删除本地那些在远程镜像中已不存在的引用，保持本地与远程的严格一致。

### 评论
这个功能是 Quipu 协作能力的一次重大升级。它将 `sync` 从一个单一用途的工具转变为一个灵活的、适应多种开发哲学的工作流引擎，无论是个人备份、团队协作还是中心化管理，都能提供支持。

### 目标
1.  在 `quipu sync` 命令中添加 `--mode` 选项，支持 `bidirectional`, `push-only`, `pull-only`, `push-force`, `pull-prune` 五种模式。
2.  在 `git_db.py` 中为 `push_quipu_refs` 添加 `force` 参数，并实现 `prune_local_from_remote` 方法。
3.  在 `remote.py` 中使用 `match` 语句分派不同的同步逻辑。
4.  创建了新的集成测试文件 `test_sync_modes.py`，对每种模式的正确行为进行了验证。
5.  修复了 `test_sync_workflow.py` 中因所有权传播逻辑变更而导致的测试失败。

### 基本原理
通过引入一个 `SyncMode` 枚举和命令分派器，我们将复杂的同步逻辑分解为一系列原子化的 Git 操作（`fetch`, `reconcile`, `push`, `prune`）。每种模式只是这些原子操作的不同组合，这使得代码清晰、可维护且易于扩展。测试套件确保了这些组合在模拟的真实多用户环境下行为正确。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/engine #concept/sync #scope/api #ai/instruct #task/domain/cli #task/object/sync-command #task/action/enhancement #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交所有相关变更

我们将所有已修改和新增的文件添加到暂存区，并创建一个内容详尽的提交来记录这项功能的完成。

~~~~~act
git_add
packages/quipu-cli/src/quipu/cli/commands/remote.py
packages/quipu-engine/src/quipu/engine/git_db.py
tests/integration/test_sync_workflow.py
tests/integration/test_sync_modes.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): implement multiple sync modes for flexible workflows

Introduces a `--mode` option to the `quipu sync` command, enabling granular control over the synchronization process. This completes the "add multiple sync modes" task.

The following modes are now supported:
- `bidirectional` (default): Fetches, reconciles, and pushes.
- `push-only`: Pushes local changes without fetching remote updates. Ideal for backups or one-way publishing.
- `pull-only`: Fetches and reconciles remote changes without pushing local nodes. Useful for read-only subscriptions.
- `push-force`: Force-pushes local heads, overwriting the user's remote namespace. Allows for history rewriting and correction.
- `pull-prune`: After fetching, prunes local heads that no longer exist on the remote mirror. Enforces strict consistency with the remote.

This is implemented by:
1.  Adding a `SyncMode` Enum and a dispatcher in `remote.py`.
2.  Enhancing `GitDB` with `force` capabilities for push operations and a new `prune_local_from_remote` method.
3.  Creating a dedicated integration test suite, `test_sync_modes.py`, to validate the behavior of each mode in a multi-user environment.
4.  Fixing related tests in `test_sync_workflow.py` to align with updated ownership propagation logic.
~~~~~

### 下一步建议
- **文档更新**: 更新项目的 `README.md` 或相关文档，向用户介绍新的 `sync` 模式及其使用场景。
- **UI 集成**: 可以在 `quipu ui` 中考虑添加一个界面，让用户可以方便地管理订阅列表和查看不同协作者的历史分支。
