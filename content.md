===== 结构化计划

## fix: 修复集成测试中的文件路径引用错误

### 错误分析
在 `tests/integration/test_sync_workflow.py` 的集成测试中，测试用例 `test_onboarding_and_first_push` 和 `test_pruning_on_push` 调用 `quipu run` 命令时，传递了相对路径 `"plan.md"` (以及 `plan2.md`, `plan3.md`) 作为参数。
由于 `CliRunner` 在执行时保持当前工作目录（通常是项目根目录），而 `plan.md` 实际上是在 `user_a_path` 临时目录中创建的。因此，`quipu run` 命令内部的 `file.exists()` 检查失败，导致命令以退出码 1 终止。
这进一步导致后续的 `quipu sync` 操作没有数据可推送，进而导致依赖于远程数据的后续测试用例（订阅与拉取、修剪）全部失败（级联故障）。

### 用户需求
- 修复 `test_sync_workflow.py` 中的文件路径引用问题，确保 `quipu run` 能正确找到并执行计划文件。
- 确保集成测试能够顺利通过，验证 Sync 功能的正确性。

### 评论
这是一个典型的测试环境配置问题。虽然 `quipu run` 接受 `--work-dir` 参数来指定 Quipu 操作的逻辑根目录，但 `file` 参数作为 CLI 的输入，其路径解析是相对于调用时的 CWD 的（由 shell 或 `CliRunner` 决定）。因此，必须传递文件的绝对路径。

### 目标
- 修改 `test_sync_workflow.py`，在调用 `runner.invoke` 时使用 plan 文件的绝对路径。

### 基本原理
- 使用 `str(user_a_path / "plan.md")` 替代 `"plan.md"`，确保 CLI 接收到正确的文件路径。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/integration-test #task/action/fix-path #task/state/begin

---

### Script

#### Acts 1: 修复 test_sync_workflow.py 中的路径引用

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python
        # Create a Quipu node for User A
        (user_a_path / "plan.md").write_text("~~~~~act\necho 'hello'\n~~~~~")
        result = runner.invoke(app, ["run", "plan.md", "--work-dir", str(user_a_path), "-y"])
        assert result.exit_code == 0

        # Run sync for the first time
~~~~~
~~~~~python
        # Create a Quipu node for User A
        (user_a_path / "plan.md").write_text("~~~~~act\necho 'hello'\n~~~~~")
        result = runner.invoke(app, ["run", str(user_a_path / "plan.md"), "--work-dir", str(user_a_path), "-y"])
        assert result.exit_code == 0

        # Run sync for the first time
~~~~~

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python
        # Create two new nodes
        (user_a_path / "plan2.md").write_text("~~~~~act\necho 'plan2'\n~~~~~")
        (user_a_path / "plan3.md").write_text("~~~~~act\necho 'plan3'\n~~~~~")
        runner.invoke(app, ["run", "plan2.md", "--work-dir", str(user_a_path), "-y"])
        runner.invoke(app, ["run", "plan3.md", "--work-dir", str(user_a_path), "-y"])

        runner.invoke(app, ["sync", "--work-dir", str(user_a_path), "--remote", "origin"])
~~~~~
~~~~~python
        # Create two new nodes
        (user_a_path / "plan2.md").write_text("~~~~~act\necho 'plan2'\n~~~~~")
        (user_a_path / "plan3.md").write_text("~~~~~act\necho 'plan3'\n~~~~~")
        runner.invoke(app, ["run", str(user_a_path / "plan2.md"), "--work-dir", str(user_a_path), "-y"])
        runner.invoke(app, ["run", str(user_a_path / "plan3.md"), "--work-dir", str(user_a_path), "-y"])

        runner.invoke(app, ["sync", "--work-dir", str(user_a_path), "--remote", "origin"])
~~~~~

### 下一步建议
执行修复后，重新运行 `pytest tests/integration/test_sync_workflow.py` 验证修复结果。如果所有测试通过，说明 Sync 功能的核心流程（Onboarding, Push, Fetch, Prune）均工作正常。
