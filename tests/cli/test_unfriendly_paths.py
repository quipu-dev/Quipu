import pytest
import click
from typer.testing import CliRunner
from quipu.cli.main import app


def test_run_command_user_cancellation(runner: CliRunner, quipu_workspace, monkeypatch):
    """
    不友好路径测试: 验证当用户输入 'n' 时，操作会被正确取消。
    """
    work_dir, _, _ = quipu_workspace
    output_file = work_dir / "output.txt"
    assert not output_file.exists()

    plan_content = f"""
```act
run_command
```
```text
echo "Should not run" > {output_file.name}
```
"""

    # 使用 monkeypatch 直接模拟 getchar 的行为，而不是通过 stdin 管道
    def mock_getchar_n(echo):
        # 我们的 confirmation_handler 会回显字符，所以我们也模拟一下
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)

    result = runner.invoke(app, ["run", "-w", str(work_dir)], input=plan_content)

    # OperationCancelledError 导致退出码为 2
    assert result.exit_code == 2, f"CLI command should have been cancelled. Stderr:\n{result.stderr}"
    assert "操作已取消" in result.stderr
    assert not output_file.exists(), "File should not have been created after cancellation."


def test_run_command_in_non_interactive_env(runner: CliRunner, quipu_workspace, monkeypatch):
    """
    不友好路径测试: 验证在非交互式环境 (无法 getchar) 中，操作会自动中止。
    """
    work_dir, _, _ = quipu_workspace
    output_file = work_dir / "output.txt"
    assert not output_file.exists()

    plan_content = f"""
```act
run_command
```
```text
echo "Should not run" > {output_file.name}
```
"""

    # 模拟 click.getchar() 失败，就像在 CI 环境中一样
    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)

    # 在这种情况下，不需要 'input'，因为 getchar 会直接失败
    result = runner.invoke(app, ["run", "-w", str(work_dir)], input=plan_content)

    # 同样，应该以退出码 2 退出
    assert result.exit_code == 2, f"CLI command should fail safely. Stderr:\n{result.stderr}"
    assert "操作已取消" in result.stderr
    # 验证我们的非交互式环境处理逻辑被触发
    assert "(non-interactive)" in result.stderr
    assert not output_file.exists(), "File should not be created in a non-interactive environment."
