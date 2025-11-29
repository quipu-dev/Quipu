好的，我们已经成功地将用户确认逻辑统一到了标准实现。现在，我将创建一个 `[COMMIT]` 计划来持久化这些改进。

## [COMMIT] refactor(cli): Standardize user confirmation logic

### 用户需求
项目中存在多种不一致的用户确认实现方式（`typer.confirm`, `axon.py` 中的本地处理器）。需要将所有实现统一到 `ui_utils.prompt_for_confirmation`，以确保行为一致性和代码可维护性。

### 评论
这是一个重要的代码质量和开发者体验 (DX) 改进。通过将核心交互逻辑集中化，我们不仅消除了冗余代码，还保证了所有命令在交互式和非交互式环境中都有着同样健壮、可预测的行为。

### 目标
1.  已将 `export.py` 中对 `typer.confirm` 的调用替换为标准的 `prompt_for_confirmation` 函数。
2.  已将 `axon.py` 中的本地确认处理器移除，并替换为 `controller.py` 中为 `Executor` 提供的标准适配器。
3.  已将此项重构作为一个逻辑单元提交到版本历史中。

### 基本原理
此重构遵循了“不要重复自己” (DRY) 和“单一职责”的原则。通过建立一个单一、健壮的 `prompt_for_confirmation` 函数作为所有用户确认的基础，我们为整个 CLI 应用提供了一个统一的交互标准。这使得未来的维护和功能扩展（例如，增加全局的 `--force` 标志）变得更加简单和安全。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #concept/ui #scope/dx #scope/ux #ai/instruct #task/domain/cli #task/object/user-confirmation #task/action/unification #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

现在，我们将所有相关的修改添加到 Git 暂存区，并创建一个符合规范的提交。

~~~~~act
git_add
packages/quipu-cli/src/quipu/cli/commands/export.py
packages/quipu-cli/src/quipu/cli/commands/axon.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(cli): standardize user confirmation logic

Centralizes all user confirmation prompts to use the single, robust helper function `ui_utils.prompt_for_confirmation`.

Previously, user confirmation was handled inconsistently across different commands:
- `export.py` used `typer.confirm`, which behaves poorly in non-interactive (piped) environments.
- `axon.py` defined its own redundant local confirmation handler.

This commit refactors these commands to use the standard utility, ensuring consistent and predictable behavior, especially in scripted CI/CD environments. This improves code maintainability and user experience.
~~~~~

### 下一步建议
本次重构任务已完成。我们可以运行 `pytest tests/cli/test_unfriendly_paths.py` 来专门验证这些交互在各种边界条件下的健壮性，然后继续进行下一个开发任务。
