好的，我们已经完成了代码修改。现在我将生成一个 `[COMMIT]` 计划，将对 `run_command` 的修正和配套测试固化到版本历史中。

## [COMMIT] fix(runtime): 改进 run_command 以支持多行脚本

### 用户需求
修正 `run_command` 的行为，使其能够将多行脚本作为单个命令正确执行，而不是将所有行错误地拼接成一个单行命令。

### 评论
这个修复是提升 `quipu-runtime` 健壮性和易用性的重要步骤。它确保了用户可以直接在 Markdown 块中提供标准的多行 shell 脚本，例如用于复杂的 `mv` 或 `cp` 序列。

### 目标
1.  已将 `pyquipu/acts/shell.py` 中 `_run_command` 的参数连接符从空格 (` `) 更改为换行符 (`\n`)。
2.  已更新 `pyquipu/tests/runtime/acts/test_shell.py`，增加了对多行脚本执行和指令块隔离性的测试。
3.  创建一个 Git 提交，将此项改进持久化。

### 基本原理
通过在 `_run_command` 中使用换行符连接参数 (`"\n".join(args)`)，我们确保了即使解析器将多行脚本分割成了多个参数（或一个参数中包含多行），它们也能被重新构造为一个逻辑正确的 shell 脚本。Shell 在执行时会逐行处理这些命令。

### 标签
#intent/fix #flow/ready #priority/medium #comp/runtime #concept/executor #scope/ux #ai/instruct #task/domain/runtime #task/object/acts #task/action/refinement #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

现在，我们将修改后的文件添加到 Git 暂存区，并创建一个内容详尽的提交。

~~~~~act
git_add
packages/quipu-runtime/src/pyquipu/acts/shell.py
tests/runtime/acts/test_shell.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(runtime): Improve run_command to support multi-line scripts

The internal implementation of `run_command` was incorrectly joining block-style arguments using a space (`" ".join(args)`). This corrupted multi-line scripts, as each line passed from the parser block was treated as a separate argument, which were then glued together with spaces.

Changed the joining mechanism to use a newline (`"\n".join(args)`).

This allows users to pass complex multi-line shell scripts (e.g., chained `mv` commands or multi-line `if` statements) directly within a content block, significantly enhancing the utility and UX of the act.
~~~~~

### 下一步建议
核心的 `run_command` 功能现在更加健壮。建议进行全局测试，验证所有其他 Acts（如 `git_commit`、`write_file` 等）是否仍然能正确处理多块输入。此外，下一步可以考虑继续处理 [吞噬代码块检测.md](current_prompts/00_当前/吞噬代码块检测.md) 中提出的通用问题，以确保 Act 参数的界限始终清晰。
