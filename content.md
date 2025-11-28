好的，测试已通过。现在我将创建 Git 提交来保存这次重构。

## commit: refactor(cli): 将 CLI 命令拆分到模块并重构 TUI 状态

### 用户需求
将最近完成的 `quipu-cli` 代码重构（包括 CLI 命令模块化和 TUI 状态管理优化）及其相关的测试修复，作为一个原子提交保存到版本控制历史中。

### 评论
这次重构显著提升了 `quipu-cli` 的代码结构和可维护性。提交这些变更是完成任务的关键一步，为后续的功能开发和测试覆盖率提升奠定了坚实的基础。

### 目标
1.  将所有已修改、新增的文件暂存。
2.  创建一个清晰、遵循 Conventional Commits 规范的 Git 提交。

### 基本原理
使用 `git add` 来暂存所有变更，然后使用 `git commit` 并附带一个详细的提交信息，以记录本次重构的目的和具体内容。这确保了版本历史的可读性和可追溯性。

### 标签
#intent/tooling #flow/done #comp/cli #comp/tests #scope/dx #ai/instruct #task/domain/ui #task/object/refactor #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存所有变更

~~~~~act
git_add
~~~~~
~~~~~
.
~~~~~

#### Acts 2: 创建提交

~~~~~act
git_commit
~~~~~
~~~~~
refactor(cli): Split CLI commands into modules and refactor TUI state

This major refactoring improves the maintainability and structure of the
quipu-cli package.

- Command logic is factored out from the monolithic main.py into
  dedicated modules under `quipu.cli.commands`. main.py now serves as
  a clean registration entrypoint.

- TUI state management logic (e.g., visibility toggles, node
  selection) has been moved from the `QuipuUiApp` (View) to the
  `GraphViewModel`, better aligning with the MVVM pattern and simplifying
  the UI component.

- An integration test was updated to reflect the new module structure.
~~~~~

### 下一步建议
重构已经完成并提交。下一步，我们可以开始为新拆分出的命令模块和 `GraphViewModel` 编写更详尽的单元测试，以提高整体的测试覆盖率。
