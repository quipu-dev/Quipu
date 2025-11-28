好的。所有测试均已通过，我们已经成功地实现了 `--json` 功能，并修复了所有相关的测试。现在是时候将这个完整的工作单元提交到版本控制中了。

## [COMMIT] feat(cli):为 log 和 find 命令添加 --json 输出

### 用户需求
为 `quipu log` 和 `quipu find` 命令增加 `--json` 标志，以便将结果以机器可读的 JSON 格式输出到 `stdout`，从而支持自动化脚本和与其他工具的集成。

### 评论
这是一个关键的功能增强，它将 Quipu 从一个主要面向人类交互的工具，转变为一个能够无缝融入自动化工作流的强大平台组件。提供机器可读的输出极大地提升了 Quipu 的可编程性和开发者体验 (DX)。

### 目标
1.  已为 `log` 和 `find` 命令添加 `--json` 选项。
2.  已实现一个健壮的、基于 `dataclasses` 的动态 JSON 序列化器，避免了硬编码。
3.  已为新功能添加了全面的单元测试，并覆盖了边缘情况。
4.  已修复了因早期输出流重构 (`stdout`/`stderr` 分离) 而导致失败的所有相关测试。
5.  创建一个原子性的 Git 提交，将此功能、其测试以及所有必要的测试修复一同持久化。

### 基本原理
通过在 `query.py` 中引入 `--json` 标志和动态序列化逻辑，我们提供了一个可靠的机器可读 API。当 `--json` 被激活时，命令会绕过所有人类可读的格式化，直接将 `QuipuNode` 对象列表序列化为 JSON 数组并输出到 `stdout`。同时，对整个测试套件的修复确保了我们的改动与现有功能兼容，并验证了 CLI 行为的一致性。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/tests #concept/ui #scope/api #scope/dx #ai/brainstorm #task/domain/cli #task/object/json-output #task/action/implementation #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交功能实现及所有测试修复

现在，我们将把所有与此功能相关的修改（包括实现代码、新测试和修复的旧测试）添加到 Git 暂存区，并创建一个内容详尽的提交。

~~~~~act
git_add
~~~~~
~~~~~text
packages/quipu-cli/src/quipu/cli/commands/query.py
tests/cli/test_query_commands.py
tests/cli/test_workspace_commands.py
tests/integration/test_cli_workflow.py
tests/integration/test_storage_selection.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): add --json output to log and find commands

Introduces a `--json` flag to the `quipu log` and `quipu find` commands, enabling machine-readable output for scripting and automation purposes.

- When `--json` is specified, the command outputs a JSON array of node objects to stdout and suppresses all human-readable metadata on stderr.
- The serialization logic is dynamically built using `dataclasses.fields` to avoid hardcoding and ensure maintainability as the `QuipuNode` model evolves.
- In the case of empty results, a valid empty JSON array `[]` is returned.

This change significantly improves the composability of the Quipu CLI, allowing it to be effectively integrated into automated workflows and pipelines.

Additionally, this commit includes fixes for all CLI and integration tests that were affected by the recent refactoring of output streams (`stdout`/`stderr` separation), ensuring the entire test suite is now consistent with the current implementation.
~~~~~

### 下一步建议
我们已经成功地为 Quipu CLI 添加了强大的脚本能力。下一步，我们可以考虑将这种能力扩展到其他地方：

-   **扩展 JSON 支持**: 考虑为其他可能返回列表数据的命令（如 `remote --list-subscriptions`，如果未来有的话）也添加 `--json` 支持，以保持 API 的一致性。
-   **模板化输出**: 对于更高级的用例，可以探索一个 `--format` 选项，允许用户使用 Go 模板语法来精确控制输出格式，类似于 `git log --format="..."` 或 `docker inspect --format '{{.NetworkSettings.IPAddress}}'`。
