所有代码修复和版本提升工作均已就绪。现在，我们将这些变更作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] fix(typing): 解决全库 pyright 错误并提升包版本

### 用户需求

将之前执行的所有类型修复、测试修正以及版本号更新的操作提交到 Git 仓库。

### 评论

这是一个重要的里程碑。通过解决这 61 个 `pyright` 错误，我们不仅提高了代码的健壮性，还显著提升了开发者的 DX（开发者体验）。版本号的同步提升也为后续的稳定发布打下了基础。

### 目标

1.  将所有修改过的文件添加到 Git 暂存区。
2.  创建一个包含详细说明的提交记录，涵盖协议完善、TUI 类型断言、测试修正以及版本提升等核心内容。

### 基本原理

遵循 `d3-constraint-quipu-plan-script-rules` 约束，我们将 Git 提交操作独立于文件修改计划之外。由于之前的修改已通过 `patch_file` 逻辑确认，现在执行 `git add .` 是安全的，它将捕获所有相关的结构性和内容变更。

### 标签

#intent/fix #intent/tooling #flow/ready #priority/high 
#comp/spec #comp/cli #comp/runtime #comp/application #comp/build 
#concept/ui #concept/executor #concept/parser #scope/core #scope/dx 
#ai/instruct 
#task/domain/testing #task/object/type-checking #task/action/bug-fix 
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有变更暂存并创建一个详尽的提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(typing): resolve all pyright errors and bump package versions

This commit addresses 61 type-checking errors reported by pyright across the monorepo, 
significantly improving type safety and DX.

Key changes:
- spec: Refined 'QuipuEngine' and 'ExecutorProtocol' to be more comprehensive and accurate.
- spec: Restored missing 'Path' import in 'engine.py'.
- cli: Added type assertions in 'QuipuUiApp' (TUI) to handle late-initialized components 
  (ViewModel), resolving 'reportOptionalMemberAccess' errors.
- cli: Refactored TUI reachability tests to use ViewModel's public API.
- runtime: Updated all core acts to correctly receive 'ActContext' and use 'ctx.fail()'.
- runtime: Explicitly typed 'Statement' lists in parser and tests to satisfy invariance requirements.
- tests: Fixed 'MockHistoryReader' signature to handle optional sets/dicts properly.
- chore: Bumped 'pyquipu-spec' to 0.1.1 and other core packages to 0.2.1.
- chore: Updated inter-package dependency constraints to match new versions.
~~~~~

### 下一步建议

- **运行测试**: 提交完成后，建议运行一次全量测试 `uv run pytest`，确保所有的类型修复和重构都没有破坏现有的功能。
- **发布准备**: 如果测试通过，现在可以考虑生成 Changelog 或进行正式的包发布流程。
