import pytest
from quipu.acts.shell import register as register_shell_acts
from quipu.runtime.executor import Executor
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext, Statement


class TestShellActs:
    @pytest.fixture(autouse=True)
    def setup_executor(self, executor: Executor):
        register_shell_acts(executor)

    def test_run_command_success(self, executor: Executor):
        captured = []
        executor.data_handler = captured.append

        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, ["echo 'Hello Shell'"])

        assert len(captured) == 1
        assert captured[0] == "Hello Shell"

    def test_run_command_multiline_script(self, executor: Executor, isolated_vault):
        script = "touch file_a.txt\nmv file_a.txt file_b.txt"
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, [script])

        assert not (isolated_vault / "file_a.txt").exists()
        assert (isolated_vault / "file_b.txt").exists()

    def test_run_command_does_not_swallow_blocks(self, executor: Executor):
        captured = []
        executor.data_handler = captured.append

        statements: list[Statement] = [
            {"act": "run_command", "contexts": ["echo 'first'"]},
            {"act": "echo", "contexts": ["second"]},
        ]
        executor.execute(statements)

        assert captured == ["first", "second"]

    def test_run_command_failure(self, executor: Executor):
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)

        with pytest.raises(ExecutionError, match="命令执行失败"):
            func(ctx, ["exit 1"])

    def test_run_command_stderr(self, executor: Executor, caplog):
        import logging

        caplog.set_level(logging.WARNING)

        cmd = "python3 -c \"import sys; print('error msg', file=sys.stderr)\""

        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        func(ctx, [cmd])

        assert "error msg" in caplog.text

    def test_run_command_missing_args(self, executor: Executor):
        func, _, _ = executor._acts["run_command"]
        ctx = ActContext(executor)
        with pytest.raises(ExecutionError, match="run_command 需要至少 1 个参数"):
            func(ctx, [])
