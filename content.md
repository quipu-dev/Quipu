好的，分析完毕。`ruff --fix` 很可能移除了 `test_pull_only_mode` 函数中使用的 `import yaml`，因为 `yaml` 这个变量本身没有在函数体中被直接调用（而是通过 `yaml.safe_load` 和 `yaml.dump`），导致静态分析器误判。

我将创建一个计划来修正这个问题。我们将恢复被删除的导入，并添加 `noqa` 注释来防止 Ruff 再次移除它。

## [WIP] fix(tests): 修正 sync_modes 测试因 ruff 自动修复导致的导入错误

### 错误分析
在执行 `ruff check . --fix` 后，`tests/integration/test_sync_modes.py` 中的四个测试用例开始报错。根本原因是 Ruff 的自动修复功能移除了 `test_pull_only_mode` 函数中使用的 `import yaml` 语句。

虽然 `yaml` 这个模块名没有在测试函数体中被直接引用，但它的方法 (`yaml.safe_load`, `yaml.dump`) 被用于修改配置文件。静态分析器未能识别这种间接使用，因此错误地将其标记为“未使用”并删除，导致在测试运行时出现 `NameError: name 'yaml' is not defined`。

### 用户需求
需要修复 `test_sync_modes.py` 文件，使其能够再次成功运行。

### 评论
这是一个与自动化代码质量工具协作时的典型场景。通过添加 `noqa` 注释，我们可以向静态分析器提供额外的人类上下文，告诉它某个看似未使用的导入实际上是必需的，从而解决误报问题，使自动化流程更加健壮。

### 目标
1.  在 `test_sync_modes.py` 文件中恢复 `import yaml` 语句。
2.  在该导入语句末尾添加 `# noqa: F401` 注释，以防止 Ruff 再次将其移除。

### 基本原理
`# noqa: F401` 注释是一种行业标准，用于向 linter (如 Ruff, Flake8) 声明“忽略此处的 F401 (unused import) 错误”。这允许我们在代码中保留那些对于 Pytest Fixture 或其他动态机制至关重要，但无法被静态分析正确识别的导入。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/ci-fixes #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 恢复 `import yaml` 并添加 `noqa`

我们将使用 `patch_file` 来精准地修改 `test_pull_only_mode` 函数，将 `import yaml` 重新插入到函数体内部，并附带 `# noqa` 注释。将其放在函数内部可以确保其作用域仅限于此测试，避免影响文件顶部的全局导入。

> **设计说明**: 将 `import` 放在函数内部是一种常见的解决此类问题的方法，它使得导入的作用域更加明确，并且更容易被人类和工具理解其特殊用途。

~~~~~act
patch_file
tests/integration/test_sync_modes.py
~~~~~
~~~~~python
    def test_pull_only_mode(self, sync_test_environment):
        """User B pulls User A's changes, but does not push its own."""
        remote_path, user_a_path, user_b_path = sync_test_environment
        user_a_id = get_user_id_from_email("user.a@example.com")
        import yaml

        # User A creates a node and pushes
        node_a = create_node(user_a_path, "node_from_a_for_pull")
~~~~~
~~~~~python
    def test_pull_only_mode(self, sync_test_environment):
        """User B pulls User A's changes, but does not push its own."""
        remote_path, user_a_path, user_b_path = sync_test_environment
        user_a_id = get_user_id_from_email("user.a@example.com")
        import yaml  # noqa: F401

        # User A creates a node and pushes
        node_a = create_node(user_a_path, "node_from_a_for_pull")
~~~~~

### 下一步建议
- **重新运行测试**: 在执行此计划后，请在本地运行 `qtest` 以确认所有测试现在都能成功通过。
- **重新运行 Ruff**: 运行 `ruff check .` 来验证 `noqa` 注释已生效，并且 Ruff 不再报告任何错误。
- **提交修复**: 在本地验证通过后，将此修复作为一个新的提交或修正（amend）到上一个提交中，然后推送到 GitHub 以触发 CI 进行最终验证。
