from pathlib import Path

import pytest
from quipu.acts.check import register as register_check_acts
from quipu.runtime.executor import Executor
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext


class TestCheckActs:
    @pytest.fixture(autouse=True)
    def setup_executor(self, executor: Executor):
        register_check_acts(executor)

    def test_check_files_exist_success(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "config.json").touch()
        (isolated_vault / "src").mkdir()
        (isolated_vault / "src/main.py").touch()

        file_list = "config.json\nsrc/main.py"
        func, _, _ = executor._acts["check_files_exist"]
        ctx = ActContext(executor)
        # 成功时静默完成，不应抛出任何异常
        func(ctx, [file_list])

    def test_check_files_exist_fail(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "exists.txt").touch()
        file_list = "exists.txt\nmissing.txt"

        with pytest.raises(ExecutionError, match="以下文件在工作区中未找到"):
            func, _, _ = executor._acts["check_files_exist"]
            ctx = ActContext(executor)
            func(ctx, [file_list])

    def test_check_cwd_match_success(self, executor: Executor, isolated_vault: Path):
        real_path = str(isolated_vault.resolve())
        func, _, _ = executor._acts["check_cwd_match"]
        ctx = ActContext(executor)
        func(ctx, [real_path])

    def test_check_cwd_match_fail(self, executor: Executor):
        wrong_path = "/this/path/does/not/exist"

        with pytest.raises(ExecutionError, match="工作区目录不匹配"):
            func, _, _ = executor._acts["check_cwd_match"]
            ctx = ActContext(executor)
            func(ctx, [wrong_path])
