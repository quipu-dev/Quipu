import pytest
import logging
from pathlib import Path
from typer.testing import CliRunner
from core.controller import run_axon, AxonResult
from main import app
from core.executor import Executor
from acts.basic import register as register_basic

# --- Fixtures ---

@pytest.fixture(autouse=True)
def reset_logging():
    """
    每次测试前后重置 logging handlers。
    这是解决 CliRunner I/O Error 的关键，防止 handler 持有已关闭的流。
    """
    root = logging.getLogger()
    # Teardown: 清理所有 handlers
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

# --- 1. Controller Layer Tests (The Core) ---
# 这些测试直接验证业务逻辑，不涉及 CLI 参数解析干扰

class TestController:
    
    @pytest.fixture
    def workspace(self, tmp_path):
        """准备一个带 git 的工作区"""
        ws = tmp_path / "ws"
        ws.mkdir()
        
        # 初始化 git (Engine 需要)
        import subprocess
        subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
        # 设置 user 避免 commit 报错
        subprocess.run(["git", "config", "user.email", "test@axon.dev"], cwd=ws, check=True)
        subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=ws, check=True)
        
        return ws

    def test_run_axon_success(self, workspace):
        """测试正常执行流程"""
        plan = """
~~~act
write_file
~~~
~~~path
hello.txt
~~~
~~~content
Hello Axon
~~~
"""
        result = run_axon(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is True
        assert result.exit_code == 0
        assert (workspace / "hello.txt").exists()
        
        # 验证 Engine 是否生成了 Plan 节点
        history_dir = workspace / ".axon" / "history"
        assert history_dir.exists()
        assert len(list(history_dir.glob("*.md"))) >= 1

    def test_run_axon_execution_error(self, workspace):
        """测试执行期间的预期错误 (如文件不存在)"""
        # 试图追加到一个不存在的文件
        plan = """
~~~act
append_file
~~~
~~~path
ghost.txt
~~~
~~~content
boo
~~~
"""
        result = run_axon(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is False
        assert result.exit_code == 1
        assert "文件不存在" in result.message

    def test_run_axon_empty_plan(self, workspace):
        """测试无有效指令"""
        plan = "Just some text, no acts."
        
        result = run_axon(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is False # 视为非成功状态（虽然不是错误，但任务未完成）
        assert result.exit_code == 0   # 但退出码为 0，不报错
        assert "未找到任何有效的" in result.message

# --- 2. CLI Layer Tests (The Shell) ---
# 这些测试验证 main.py 是否正确解析参数并传递给 Controller
# 由于 Controller 已经测过了，这里可以用 mock 来隔离

runner = CliRunner()

class TestCLIWrapper:
    
    def test_cli_help(self):
        """测试 --help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Axon" in result.stdout

    def test_cli_file_input(self, tmp_path):
        """测试从文件读取输入"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("~~~act\nend\n~~~", encoding="utf-8")
        
        # 我们不需要真的跑 git，只要看是否尝试运行即可
        # 如果 work-dir 不是 git repo，Controller 会报错或 Engine 初始化失败
        # 这里为了简单，我们让它在一个临时目录跑，预期可能是 1 (Engine init fail) 或 0 (如果 Engine 容错好)
        # 关键是不要由 CliRunner 抛出 ValueError
        
        # 初始化一个最小 git repo 避免 Engine 报错干扰 CLI 测试
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        
        result = runner.invoke(app, [str(plan_file), "--work-dir", str(tmp_path), "--yolo"])
        
        # 只要不是 Python traceback 导致的 Crash (exit_code != 0 and not handled) 就行
        # 我们的 Controller 会捕获异常返回 exit_code 1
        assert result.exit_code in [0, 1]
        assert "ValueError" not in str(result.exception)

    def test_cli_no_input_shows_usage(self, monkeypatch, tmp_path):
        """测试无输入时显示用法"""
        # 1. 临时修改 main 模块中的默认入口文件引用，防止读取当前目录下的 o.md
        # 注意：必须 patch 'main' 模块，而不是 'config' 模块，因为 main 采用了 from import
        import main
        monkeypatch.setattr(main, "DEFAULT_ENTRY_FILE", tmp_path / "non_existent.md")
        
        # 2. 同时确保 STDIN 不是 TTY，也不是管道（模拟纯交互式空运行）
        # CliRunner 默认就是这种状态，但为了保险起见，我们什么都不输入
        
        result = runner.invoke(app, []) # 无参数，无管道
        
        assert result.exit_code == 0
        assert "用法示例" in result.stderr

    def test_cli_list_acts(self):
        """测试 --list-acts"""
        result = runner.invoke(app, ["--list-acts"])
        assert result.exit_code == 0
        assert "write_file" in result.stderr