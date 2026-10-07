import shutil
import subprocess
from pathlib import Path

import pytest
from quipu.acts.git import register as register_git_acts
from quipu.runtime.executor import Executor
from quipu.spec.protocols.runtime import ActContext, Statement


@pytest.mark.skipif(not shutil.which("git"), reason="Git 命令未找到，跳过 Git 测试")
class TestGitActs:
    @pytest.fixture(autouse=True)
    def setup_git_env(self, executor: Executor, isolated_vault: Path):
        register_git_acts(executor)

        # 执行初始化
        func, _, _ = executor._acts["git_init"]
        ctx = ActContext(executor)
        func(ctx, [])

        # 配置测试用的 user，防止 CI/Test 环境报错
        subprocess.run(["git", "config", "user.email", "quipu@test.com"], cwd=isolated_vault, check=True)
        subprocess.run(["git", "config", "user.name", "Quipu Bot"], cwd=isolated_vault, check=True)

    def test_git_workflow(self, executor: Executor, isolated_vault: Path):
        # 1. 创建文件
        target_file = isolated_vault / "README.md"
        target_file.write_text("# Test Repo", encoding="utf-8")

        # 2. Git Add
        git_add, _, _ = executor._acts["git_add"]
        ctx = ActContext(executor)
        git_add(ctx, ["README.md"])

        # 验证状态 (porcelain 输出 ?? 代表未追踪，A 代表已添加)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=isolated_vault, text=True)
        assert "A  README.md" in status

        # 3. Git Commit
        git_commit, _, _ = executor._acts["git_commit"]
        git_commit(ctx, ["Initial commit"])

        # 验证提交日志
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=isolated_vault, text=True)
        assert "Initial commit" in log

    def test_git_init_idempotent(self, executor: Executor):
        # setup_git_env 已经 init 过了，再次 init 应当静默无异常
        func, _, _ = executor._acts["git_init"]
        ctx = ActContext(executor)
        func(ctx, [])

    def test_git_status_output_stream(self, executor: Executor, isolated_vault: Path):
        (isolated_vault / "untracked.txt").write_text("new file")

        captured = []
        executor.data_handler = captured.append

        stmts: list[Statement] = [{"act": "git_status", "contexts": []}]
        executor.execute(stmts)

        assert len(captured) == 1
        assert "untracked.txt" in captured[0]
