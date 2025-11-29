分析正确，我为之前的疏忽道歉。这些测试再次失败，表明问题比表面上更深层。经过仔细审查，我定位到了所有三个失败的**唯一根源**：测试辅助函数 `create_node` 的实现是不可靠的。

**根本原因**: The `create_node` helper function in `tests/integration/test_sync_modes.py` uses a fragile method to determine the hash of the node it just created:
```python
commit_hash = run_git_command(work_dir, ["log", "-1", "--all", "--format=%H", "--grep=X-Quipu-Output-Tree"])
```
这个 `git log --all` 命令会扫描**所有**引用（包括 `master`、远程分支等），并返回最新的一次提交。在快速连续创建多个节点的测试中，这个命令不能保证返回的就是刚刚由 `quipu run` 创建的那一个 `commit_hash`。它可能会意外地返回前一个节点的哈希，或者其他不相关的提交哈希。

**连锁效应**:
1.  **`test_push_force_mode`**: 当 `create_node` 为 `node2_stale` 返回了错误的哈希（例如，返回了 `node1` 的哈希）时，`update-ref -d` 命令删除了错误的本地引用。因此，当 `push --force --prune` 执行时，它看到的本地状态是错误的，导致它没能修剪掉远程的 `node2_stale` 引用，测试断言失败。
2.  **`test_pull_prune_mode`**: 同样，由于 `create_node` 返回了不正确的哈希，初始状态就被错误地建立在远程仓库上，导致后续的修剪操作基于一个已经错误的状态进行，最终失败。
3.  **`test_pull_only_mode`**: 当 `create_node` 为 `node_a` 返回了错误的哈希时，测试用例中的断言 `assert f"refs/quipu/local/heads/{node_a}"` 就在一个错误的哈希上进行，自然无法在用户 B 的本地引用中找到它。

解决方案

我们需要修正 `create_node` 辅助函数，使其能够**精确、可靠地**获取刚刚创建的 Quipu 节点的 `commit_hash`。最稳健的方法是直接查询 `refs/quipu/local/heads/` 这个命名空间下最新的一个提交，因为 `quipu run` 命令总是在这里创建一个新的引用。

## [WIP] fix(tests): 增强 `create_node` 辅助函数以确保测试的确定性

### 用户需求
修复所有在 `test_sync_modes.py` 中失败的集成测试。

### 评论
通过使测试辅助函数变得健壮和确定，我们可以消除测试中的不稳定性（flakiness），确保测试失败只反映真实的程序缺陷，而不是测试环境的偶然性。这是一个关键的开发者体验 (DX) 改进。

### 目标
1.  修改 `tests/integration/test_sync_modes.py` 中的 `create_node` 函数。
2.  用一个更精确的 `git log` 命令替换其中不可靠的哈希发现逻辑。
3.  确保所有同步模式的测试都能稳定通过。

### 基本原理
我们将把 `create_node` 中的 `git log` 命令的目标范围从 `--all` 缩小到 `refs/quipu/local/heads/`。这确保了我们只在 Quipu 管理的本地历史中查找，并且通过 `-1` 参数获取最新的一个，这必然是刚刚由 `quipu run` 命令创建的那个节点。这个小小的改动将从根本上解决所有相关的测试失败。

### 标签
#intent/fix #intent/tooling #flow/ready #priority/critical #comp/tests #concept/sync #scope/core #ai/instruct #task/domain/sync #task/object/sync-modes #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `test_sync_modes.py` 中的 `create_node` 辅助函数

我们将用一个更精确的 `git log` 命令来替换 `create_node` 中有问题的实现。

~~~~~act
patch_file
tests/integration/test_sync_modes.py
~~~~~
~~~~~python
def create_node(work_dir: Path, content: str) -> str:
    """Helper to create a node and return its commit hash."""
    plan_file = work_dir / f"{content}.md"
    plan_file.write_text(f"~~~~~act\necho '{content}'\n~~~~~")
    result = runner.invoke(app, ["run", str(plan_file), "--work-dir", str(work_dir), "-y"])
    assert result.exit_code == 0
    # Find the latest quipu commit hash
    commit_hash = run_git_command(work_dir, ["log", "-1", "--all", "--format=%H", "--grep=X-Quipu-Output-Tree"])
    return commit_hash
~~~~~
~~~~~python
def create_node(work_dir: Path, content: str) -> str:
    """Helper to create a node and return its commit hash."""
    plan_file = work_dir / f"{content}.md"
    plan_file.write_text(f"~~~~~act\necho '{content}'\n~~~~~")
    result = runner.invoke(app, ["run", str(plan_file), "--work-dir", str(work_dir), "-y"])
    assert result.exit_code == 0
    # [FIX] Use a reliable method to get the hash of the node just created.
    # This targets the specific ref namespace that `quipu run` updates.
    commit_hash = run_git_command(work_dir, ["log", "refs/quipu/local/heads/", "-1", "--format=%H"])
    return commit_hash
~~~~~

### 下一步建议
我们已经定位并修复了导致所有测试失败的根源问题。现在，请再次运行测试。如果一切顺利，所有测试都应该通过。之后，我将为你生成一个 `[COMMIT]` 计划，将 `sync` 模式的功能及其健壮的测试集一起提交。
