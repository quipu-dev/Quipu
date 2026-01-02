好的，我们已经顺利完成了本地化字符串的清理、补全以及 CLI 帮助文本的完善。现在我将生成一个 `[COMMIT]` 计划，将这些改进作为一个完整的逻辑单元提交到 Git 仓库中。

## [COMMIT] chore: improve localization coverage and CLI help documentation

### 用户需求

用户希望将之前执行的一系列改进（包括本地化字符串的修复、新增本地化检查脚本以及完善 CLI 命令的帮助文本）正式提交到仓库。

### 评论

这是一个非常高质量的清理和优化任务。通过引入 `check_locales.py` 脚本，我们为项目的长期维护提供了自动化保障。同时，完善 CLI 的帮助文本极大地提升了终端用户的开箱即用体验。这是一个逻辑完备、对 DX 和 UX 都有显著提升的工作单元。

### 目标

1.  将新创建的 `scripts/check_locales.py` 脚本添加到 Git 暂存区。
2.  将所有修改过的本地化 JSON 文件和 CLI 命令 Python 文件添加到暂存区。
3.  创建一个详细的 Git Commit，记录本次改进的核心内容。

### 基本原理

遵循 `[COMMIT]` 阶段的规范，本计划仅包含 `git_add` 和 `git_commit` 操作。我们将所有相关的变更（工具、配置、文案、代码文档）打包在一起提交，以保持 Git 历史的清晰和原子性。

### 标签

#intent/tooling #flow/ready #priority/medium #comp/cli #comp/common #scope/dx #scope/ux #ai/instruct #task/domain/testing #task/object/localization-and-help #task/action/completion #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将新脚本和所有受影响的文件添加到暂存区，并生成提交记录。

~~~~~act
git_add
scripts/check_locales.py
packages/quipu-common/src/pyquipu/common/locales/zh/runtime.json
packages/quipu-common/src/pyquipu/common/locales/zh/acts.json
packages/quipu-common/src/pyquipu/common/locales/zh/cli.json
packages/quipu-cli/src/pyquipu/cli/commands/axon.py
packages/quipu-cli/src/pyquipu/cli/commands/export.py
packages/quipu-cli/src/pyquipu/cli/commands/navigation.py
packages/quipu-cli/src/pyquipu/cli/commands/query.py
packages/quipu-cli/src/pyquipu/cli/commands/remote.py
packages/quipu-cli/src/pyquipu/cli/commands/run.py
packages/quipu-cli/src/pyquipu/cli/commands/show.py
packages/quipu-cli/src/pyquipu/cli/commands/ui.py
packages/quipu-cli/src/pyquipu/cli/commands/workspace.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
chore: enhance localization health and CLI self-documentation

This commit introduces significant improvements to the project's maintainability and user interface:

1. Localization Tooling: Added `scripts/check_locales.py`, an AST-based analysis tool to detect missing, duplicate, and potentially unused localization strings.

2. Localization Cleanup:
   - Resolved duplicate key definitions between `runtime.json` and `acts.json`.
   - Added missing keys reported by the checker: `acts.basic.error.patchContentAmbiguous`, `common.error.invalidConfig`, and `run.warning.yoloEnabled`.

3. CLI UX Enhancement: Added descriptive `help` text to all top-level commands (axon, checkout, save, log, etc.), ensuring a complete and professional experience when running `quipu --help`.

These changes ensure that the localization system remains robust and the CLI tool is self-documenting and accessible.
~~~~~

### 下一步建议

- **日常运行**: 建议将 `python scripts/check_locales.py` 作为开发过程中的常规检查项。
- **扩展脚本**: 未来可以进一步优化脚本，支持更多的语言（如英文 `en`）或更复杂的 AST 追踪模式。
- **发布准备**: 随着 CLI 帮助文本的完善，现在的工具已经具备了更好的易用性，可以考虑进行小版本的发布测试。
