好的，所有验证都已通过。现在我们将把这一系列修复和测试作为一个完整的、原子性的工作单元提交到版本历史中。

## [COMMIT] fix(cli): enable robust interactive confirmation in piped environments

### 用户需求
确保所有需要用户确认的 CLI 命令（如 `run`, `discard`）在 `stdin` 通过管道被重定向时，依然能够正确地与用户进行交互，而不是崩溃或错误地跳过确认。

### 评论
这是一个至关重要的鲁棒性修复，它解决了之前版本中的一个严重回归问题。通过标准化交互逻辑，Quipu CLI 的行为现在与标准的 Unix 工具链保持一致，极大地提升了其在自动化脚本和复杂 shell 工作流中的可靠性。新增的回归测试将确保此问题不会再次出现。

### 目标
1.  已将所有交互式确认逻辑统一到一个基于 `click.getchar()` 的健壮的辅助函数中。
2.  已将此修复应用于 `run`, `axon`, `checkout`, 和 `discard` 等所有相关的命令。
3.  已添加了专门的回归测试，用于验证在管道输入场景下，用户交互（接受和拒绝）的行为符合预期。
4.  创建了一个 Git 提交，将此项关键改进永久性地记录下来。

### 基本原理
我们放弃了在管道场景下不可靠的高级 `typer.confirm` 抽象，转而采用更底层的 `click.getchar()`。此函数能够直接从控制终端 (`/dev/tty`) 读取用户输入，从而完全绕开被管道占用的 `stdin`。我们将提示信息输出到 `stderr`，从 TTY 读取响应，并将这套逻辑封装在一个统一的辅助函数中，确保了整个应用行为的一致性和正确性。

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #comp/tests #concept/ui #scope/core #scope/ux #ai/instruct #task/domain/cli #task/object/exception-handling #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存所有相关的变更

我们将所有被修改和新建的文件添加到 Git 的暂存区。

`````act
git_add
packages/quipu-cli/src/quipu/cli/commands/axon.py
packages/quipu-cli/src/quipu/cli/commands/helpers.py
packages/quipu-cli/src/quipu/cli/commands/navigation.py
packages/quipu-cli/src/quipu/cli/controller.py
packages/quipu-interfaces/src/quipu/interfaces/exceptions.py
packages/quipu-runtime/src/quipu/acts/basic.py
packages/quipu-runtime/src/quipu/acts/git.py
packages/quipu-runtime/src/quipu/acts/refactor.py
packages/quipu-runtime/src/quipu/acts/shell.py
packages/quipu-runtime/src/quipu/runtime/executor.py
tests/cli/test_cli_interaction.py
tests/cli/test_workspace_commands.py
`````

#### Acts 2: 创建 Git 提交

现在，我们创建一个符合 Conventional Commits 规范的提交。

`````act
git_commit
`````
`````text
fix(cli): enable robust interactive confirmation in piped environments

This commit resolves a critical regression where commands requiring user confirmation would fail or misbehave when their standard input was piped from another process.

The root cause was an unreliable combination of `sys.stdin.isatty()` checks and the high-level `typer.confirm()` function, which could not handle TTY interaction correctly when stdin was redirected.

The fix involves:
1.  Standardizing on a single, robust helper function that uses `click.getchar()` to read directly from the controlling terminal (`/dev/tty`), bypassing the piped stdin.
2.  Ensuring prompts are written to stderr, so they are visible to the user during a pipe.
3.  Refactoring all interactive commands (`run`, `axon`, `discard`, `checkout`) to use this new centralized helper.
4.  Introducing a dedicated `OperationCancelledError` to cleanly handle the control flow for user cancellations.
5.  Adding new regression tests (`test_cli_interaction.py`) to specifically cover the piped-input confirmation scenario, preventing future regressions.
`````

### 下一步建议
我们已经成功修复了交互问题并添加了相应的测试。现在，整个任务已完成。我们可以继续处理下一个开发任务。
