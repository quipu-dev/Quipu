好的，我理解了你的需求。我们将专注于改进 `run_command`，使其能够健壮地处理多行脚本，并且确保它不会“吞噬”后续的指令块。`git_commit` 的修改将跳过。

这是一个健壮性提升，可以显著改善在 `plan` 中编写复杂 shell 脚本的用户体验。

我将生成一个计划，首先修改 `run_command` 的实现，然后为其添加两个关键的测试用例：一个验证多行脚本的正确执行，另一个验证它不会干扰后续的 `act`。

## [WIP] fix(runtime): 改进 run_command 以支持多行脚本

### 错误分析
当前 `run_command` 的实现 (`pyquipu.acts.shell._run_command`) 使用 ` " ".join(args)` 来组合其接收到的所有参数。这对于单行命令或通过 `shlex` 解析的行内参数是有效的。

然而，当用户在代码块中提供一个多行脚本时，`Executor` 在 `exclusive` 模式下可能会将脚本的每一行或每一个代码块作为一个独立的字符串元素传递给 `_run_command`。`" ".join()` 会将这些行错误地拼接成一个单行的、无效的命令，而不是一个多行脚本。

### 用户需求
1.  修改 `run_command` 的实现，使其能将来自代码块的多个参数或一个包含多行的参数，正确地组合成一个可执行的多行 shell 脚本。
2.  确保 `run_command` 在处理完其参数后，不会“吞噬”后续为其他 `act` 准备的代码块。

### 评论
这是一个重要的用户体验改进。它使得 `run_command` 成为一个更强大、更符合直觉的工具，用户可以直接粘贴多行脚本到代码块中执行，而无需将它们手动合并或用分号连接。

### 目标
1.  修改 `pyquipu/packages/quipu-runtime/src/pyquipu/acts/shell.py` 中的 `_run_command` 函数，将参数的连接方式从 ` ` (空格) 改为 `\n` (换行符)。
2.  在 `pyquipu/tests/runtime/acts/test_shell.py` 中增加一个新的测试用例，验证 `run_command` 可以成功执行一个多行脚本。
3.  在同一个测试文件中增加第二个测试用例，通过直接调用 `executor.execute` 来验证一个多行 `run_command` 指令后面紧跟另一个 `act` 时，第二个 `act` 能够被正确执行。

### 基本原理
通过将 ` " ".join(args)` 修改为 `"\n".join(args)`，我们可以确保无论 `args` 列表是包含一个带换行符的字符串，还是包含多个分别代表一行的字符串，最终都能被重建成一个正确的、逐行执行的 shell 脚本。

`run_command` 已被注册为 `arg_mode="exclusive"`，这个模式本身就防止了它主动吞噬不属于它的代码块。我们将通过一个专门的测试用例来锁定并验证这一行为，确保未来的修改不会破坏这种隔离性。

### 标签
#intent/fix #flow/ready #priority/medium #comp/runtime #concept/executor #scope/ux #ai/instruct #task/domain/runtime #task/object/acts #task/action/refinement #task/state/begin

---

### Script

#### Acts 1: 修改 `run_command` 的实现

我们将 `shell.py` 中 `_run_command` 函数的实现从使用空格连接参数改为使用换行符。

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/shell.py
~~~~~
~~~~~python
    command = " ".join(args)
~~~~~
~~~~~python
    command = "\n".join(args)
~~~~~

#### Acts 2: 增强 `test_shell.py` 以覆盖新行为和边界情况

现在，我们将重写测试文件，加入新的测试用例来验证多行脚本的执行和指令块的隔离性。

~~~~~act
write_file
tests/runtime/acts/test_shell.py
~~~~~
~~~~~python
import pytest
from pyquipu.acts.shell import register as register_shell_acts
from pyquipu.interfaces.exceptions import ExecutionError
from pyquipu.interfaces.types import ActContext
from pyquipu.runtime.executor import Executor


class TestShellActs:
    @pytest.fixture(autouse=True)
    def setup_executor(self, executor: Executor):
        register_shell_acts(executor)

    def test_run_command_success(self, executor: Executor, mock_runtime_bus):
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, ["echo 'Hello Shell'"])

        mock_runtime_bus.info.assert_called_with("acts.shell.info.executing", command="echo 'Hello Shell'")
        mock_runtime_bus.data.assert_called_with("Hello Shell")

    def test_run_command_multiline_script(self, executor: Executor, isolated_vault, mock_runtime_bus):
        """验证多行脚本可以被正确执行。"""
        script = "touch file_a.txt\nmv file_a.txt file_b.txt"
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, [script])

        assert not (isolated_vault / "file_a.txt").exists()
        assert (isolated_vault / "file_b.txt").exists()
        mock_runtime_bus.info.assert_called_with("acts.shell.info.executing", command=script)

    def test_run_command_does_not_swallow_blocks(self, executor: Executor, mock_runtime_bus):
        """
        验证 run_command 不会吞噬后续指令。
        这是一个更底层的测试，直接使用 executor.execute。
        """
        # 模拟解析器输出两个独立的指令
        statements = [
            {"act": "run_command", "contexts": ["echo 'first'"]},
            {"act": "echo", "contexts": ["second"]},
        ]
        executor.execute(statements)

        # 验证 run_command 的输出
        mock_runtime_bus.data.assert_any_call("first")
        # 验证第二个 echo 指令的输出
        mock_runtime_bus.data.assert_any_call("second")
        assert mock_runtime_bus.data.call_count == 2

    def test_run_command_failure(self, executor: Executor, mock_runtime_bus):
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)

        # 验证失败返回码
        with pytest.raises(ExecutionError, match="acts.shell.error.failed"):
            func(ctx, ["exit 1"])

    def test_run_command_stderr(self, executor: Executor, mock_runtime_bus):
        # 构造一个向 stderr 输出的命令
        cmd = 'python3 -c "import sys; print(\'error msg\', file=sys.stderr)"'

        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, [cmd])

        # 检查是否捕获了 warning
        assert mock_runtime_bus.warning.called
        args, kwargs = mock_runtime_bus.warning.call_args
        assert args[0] == "acts.shell.warning.stderrOutput"
        assert "error msg" in kwargs["output"]

    def test_run_command_missing_args(self, executor: Executor):
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match="acts.error.missingArgs"):
            func(ctx, [])
~~~~~

### 下一步建议
我们已经完成了对 `run_command` 的核心逻辑修改和测试增强。现在，这些变更已经准备好被提交。如果你同意，我将生成一个 `[COMMIT]` 计划来将这些修改固化到版本历史中。
