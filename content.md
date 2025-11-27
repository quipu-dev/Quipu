好的，我将为你设计一个结构化的重构方案，将 `tests` 目录按照功能模块进行分组，以提高可管理性和可维护性。

## refactor: 重构 tests 目录结构以实现模块化

### 用户需求
当前 `tests` 目录下的测试文件数量过多，呈现扁平化结构，导致难以快速定位特定模块的测试，增加了维护成本。需要将这些测试文件按照其对应的功能模块（Engine, Runtime, CLI, Integration）进行分组。

### 评论
这是一个非常必要的重构。一个结构化的测试套件能够显著提升开发者体验 (DX)，使得代码库在未来更容易扩展和维护。将测试结构与源码结构对齐，是一种行业最佳实践。

### 目标
1.  在 `tests/` 目录下创建 `engine`, `runtime`, `cli`, `integration` 四个子目录。
2.  将现有的测试文件移动到对应的新目录中。
3.  对部分测试文件进行重命名，使其职责更清晰。
4.  确保重构后，`pytest` 仍然能够发现并成功运行所有测试。

### 基本原理
本次重构遵循**关注点分离 (Separation of Concerns)** 和 **与源码对齐 (Align with Source)** 的原则。
1.  **`tests/engine/`**: 存放所有与 `quipu-engine` 强相关的测试，包括 `GitDB`、`Engine` 状态机、以及 `GitObject` 和 `SQLite` 存储后端的底层实现。
2.  **`tests/runtime/`**: 存放所有与 `quipu-runtime` 相关的测试，包括指令解析器 (`Parser`)、指令执行器 (`Executor`) 以及所有 `acts` 插件。
3.  **`tests/cli/`**: 存放所有与 `quipu-cli` 相关的测试，主要集中在用户界面（TUI, ViewModel）和顶层命令的逻辑。
4.  **`tests/integration/`**: 存放跨越多个模块的端到端 (E2E) 测试，用于验证系统作为一个整体的行为是否正确。

这种结构使得开发者在修改某个包（如 `quipu-engine`）时，可以轻松地在 `tests/engine/` 目录下找到所有相关的测试。

### 标签
#intent/refine #flow/ready #priority/high #comp/tests #scope/dx #ai/brainstorm #task/domain/testing #task/object/directory-structure #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 创建新的目录结构

首先，我们在 `tests` 目录下创建新的子目录，用于存放分组后的测试文件。

~~~~~act
write_file
~~~~~
~~~~~path
tests/engine/.gitkeep
~~~~~
~~~~~content

~~~~~

~~~~~act
write_file
~~~~~
~~~~~path
tests/runtime/.gitkeep
~~~~~
~~~~~content

~~~~~

~~~~~act
write_file
~~~~~
~~~~~path
tests/runtime/acts/.gitkeep
~~~~~
~~~~~content

~~~~~

~~~~~act
write_file
~~~~~
~~~~~path
tests/cli/.gitkeep
~~~~~
~~~~~content

~~~~~

~~~~~act
write_file
~~~~~
~~~~~path
tests/integration/.gitkeep
~~~~~
~~~~~content

~~~~~

#### Acts 2: 移动并重构测试文件

接下来，我们将逐一移动并酌情重命名现有的测试文件。为了操作的原子性，这里使用 `run_command` 指令 `mv` 来执行。

##### 移动 Engine 测试

~~~~~act
run_command
~~~~~
~~~~~bash
mv tests/test_engine.py tests/engine/test_engine.py
mv tests/test_engine_memory.py tests/engine/test_engine_memory.py
mv tests/test_git_db.py tests/engine/test_git_db.py
mv tests/test_head_and_root.py tests/engine/test_head_tracking.py
mv tests/test_storage_reader.py tests/engine/test_git_reader.py
mv tests/test_storage_writer.py tests/engine/test_git_writer.py
mv tests/test_branching.py tests/engine/test_branching.py
~~~~~

##### 移动 SQLite 相关测试 (归入 Engine)

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p tests/engine/sqlite
mv tests/test_sqlite_reader.py tests/engine/sqlite/test_reader.py
mv tests/test_sqlite_reader_integrity.py tests/engine/sqlite/test_reader_integrity.py
mv tests/test_sqlite_writer.py tests/engine/sqlite/test_writer.py
mv tests/test_sqlite_writer_idempotency.py tests/engine/sqlite/test_writer_idempotency.py
mv tests/test_hydration.py tests/engine/sqlite/test_hydrator.py
~~~~~

##### 移动 Runtime 测试

~~~~~act
run_command
~~~~~
~~~~~bash
mv tests/test_ops.py tests/runtime/test_parser_and_basic_acts.py
mv tests/test_arg_strategy.py tests/runtime/test_arg_strategy.py
mv tests/test_auto_detect.py tests/runtime/test_parser_auto_detect.py
mv tests/test_plugins.py tests/runtime/test_plugin_loader.py
mv tests/test_plugin_resilience.py tests/runtime/test_plugin_resilience.py
~~~~~

##### 移动 Acts 插件测试 (归入 Runtime)

~~~~~act
run_command
~~~~~
~~~~~bash
mv tests/test_check.py tests/runtime/acts/test_check.py
mv tests/test_git.py tests/runtime/acts/test_git.py
mv tests/test_read.py tests/runtime/acts/test_read.py
~~~~~

##### 移动 CLI 和 UI 测试

~~~~~act
run_command
~~~~~
~~~~~bash
mv tests/test_ui_logic.py tests/cli/test_tui_logic.py
mv tests/test_ui_reachability.py tests/cli/test_tui_reachability.py
mv tests/test_view_model.py tests/cli/test_view_model.py
mv tests/test_navigation.py tests/cli/test_navigation_commands.py
~~~~~

##### 移动集成测试

~~~~~act
run_command
~~~~~
~~~~~bash
mv tests/test_integration_v2.py tests/integration/test_cli_workflow.py
mv tests/test_storage_integration.py tests/integration/test_storage_selection.py
mv tests/test_isolation.py tests/integration/test_workspace_isolation.py
mv tests/test_root_invariance.py tests/integration/test_workspace_invariance.py
mv tests/test_idempotent_node.py tests/integration/test_idempotent_node.py
~~~~~

#### Acts 3: 配置文件检查

`pyproject.toml` 中的 `tool.pytest.ini_options` 已经配置了 `pythonpath`，可以正确找到 `src` 目录下的模块，因此本次文件移动**不需要**修改配置文件。`pytest` 会自动发现新路径下的 `test_*.py` 文件。

### 下一步建议
执行完此计划后，可以运行 `pytest tests/` 来验证所有的测试是否都能被正确发现并成功运行。确认无误后，这标志着本次重构任务的完成。
