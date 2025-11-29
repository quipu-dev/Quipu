import pytest
import click
from typer.testing import CliRunner
from quipu.cli.main import app
from quipu.engine.state_machine import Engine


@pytest.fixture
def dirty_workspace(quipu_workspace):
    """
    提供一个包含历史记录和未提交变更的工作区。
    - State A: file.txt -> "v1"
    - State B (HEAD): file.txt -> "v2"
    - Dirty State: file.txt -> "v3"
    """
    work_dir, _, engine = quipu_workspace
    file_path = work_dir / "file.txt"

    # State A
    file_path.write_text("v1")
    hash_a = engine.git_db.get_tree_hash()
    engine.capture_drift(hash_a, message="State A")

    # State B (HEAD)
    file_path.write_text("v2")
    engine.capture_drift(engine.git_db.get_tree_hash(), message="State B")

    # Dirty State
    file_path.write_text("v3")

    return work_dir, engine, hash_a


# --- Tests for `quipu run` ---


def test_run_command_user_cancellation(runner: CliRunner, quipu_workspace, monkeypatch):
    """
    不友好路径测试: 验证当用户输入 'n' 时，`run` 操作会被正确取消。
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

    def mock_getchar_n(echo):
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)

    result = runner.invoke(app, ["run", "-w", str(work_dir)], input=plan_content)

    assert result.exit_code == 2, f"CLI command should have been cancelled. Stderr:\n{result.stderr}"
    assert "操作已取消" in result.stderr
    assert not output_file.exists()


def test_run_command_in_non_interactive_env(runner: CliRunner, quipu_workspace, monkeypatch):
    """
    不友好路径测试: 验证在非交互式环境 (无法 getchar) 中，`run` 操作会自动中止。
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

    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)
    result = runner.invoke(app, ["run", "-w", str(work_dir)], input=plan_content)

    assert result.exit_code == 2
    assert "操作已取消" in result.stderr
    assert "(non-interactive)" in result.stderr
    assert not output_file.exists()


# --- Tests for `quipu discard` ---


def test_discard_user_cancellation(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `discard` 操作可以被用户取消。"""
    work_dir, _, _ = dirty_workspace

    def mock_getchar_n(echo):
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)
    result = runner.invoke(app, ["discard", "-w", str(work_dir)])

    assert result.exit_code == 1  # typer.Abort exits with 1
    assert "操作已取消" in result.stderr
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


def test_discard_in_non_interactive_env(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `discard` 在非交互式环境中安全中止。"""
    work_dir, _, _ = dirty_workspace

    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)
    result = runner.invoke(app, ["discard", "-w", str(work_dir)])

    assert result.exit_code == 1
    assert "(non-interactive)" in result.stderr
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


# --- Tests for `quipu checkout` ---


def test_checkout_user_cancellation(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `checkout` 操作可以被用户取消。"""
    work_dir, _, hash_a = dirty_workspace

    def mock_getchar_n(echo):
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)
    result = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(work_dir)])

    assert result.exit_code == 1
    assert "操作已取消" in result.stderr
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


def test_checkout_in_non_interactive_env(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `checkout` 在非交互式环境中安全中止。"""
    work_dir, _, hash_a = dirty_workspace

    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)
    result = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(work_dir)])

    assert result.exit_code == 1
    assert "(non-interactive)" in result.stderr
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."
