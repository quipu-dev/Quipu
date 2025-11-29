好的，测试已通过，现在我们将把这次重构作为一个完整的逻辑单元进行提交。

我将生成一个 `[COMMIT]` 计划，其中包含 `git add` 和 `git commit` 指令，以持久化我们的代码结构优化。

## [COMMIT] refactor(tests): 将 Engine 导航单元测试迁移到 tests/engine

### 用户需求
测试通过后，需要将本次重构（把 `TestNavigationEngine` 单元测试类从 `tests/cli` 迁移到 `tests/engine`）创建为一个 Git 提交。

### 评论
这是一个关键的结构性改进。通过将 `Engine` 的单元测试与其所属的 `tests/engine` 目录对齐，我们使测试套件的结构更加清晰、直观，并且遵循了代码与测试对应的最佳实践。

### 目标
1.  将新创建的 `tests/engine/test_navigation.py` 和修改后的 `tests/cli/test_navigation_commands.py` 添加到 Git 暂存区。
2.  创建一个清晰的 Git 提交，记录本次重构的目的和内容。

### 基本原理
我们通过 `git add` 和 `git commit` 命令将文件变更固化到版本历史中。提交信息遵循 Conventional Commits 规范，类型为 `refactor`，范围为 `tests`，清晰地说明了这是一次对测试代码的非功能性重构，有助于自动化工具（如 CI/CD）理解变更的性质。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #concept/navigation #scope/dx #ai/instruct #task/domain/testing #task/object/test-structure #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交本次测试结构重构

我们将暂存相关文件并执行提交。

~~~~~act
git_add
tests/engine/test_navigation.py
tests/cli/test_navigation_commands.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(tests): move engine navigation unit tests to tests/engine

The `TestNavigationEngine` class, which performs unit tests on the core navigation logic of the state machine (e.g., `engine.back()`, `engine.forward()`), was previously located in `tests/cli/test_navigation_commands.py`.

This commit moves the `TestNavigationEngine` class and its related fixtures to a new file, `tests/engine/test_navigation.py`.

This change aligns the test structure with the source code structure, ensuring that engine-level unit tests reside within the `tests/engine` directory, while the `tests/cli` directory remains focused on CLI interaction and integration tests. This improves the overall organization and maintainability of the test suite.
~~~~~

### 下一步建议
我们已经完成了对测试归属的调整。根据之前的分析，下一个可以优化的点是：

-   **抽象辅助函数**：将用于创建历史节点的辅助函数（如 `create_state`, `add_commit`）提取到 `tests/helpers.py` 中，以提高测试代码的复用性。

如果你同意，我们可以开始这项工作。
