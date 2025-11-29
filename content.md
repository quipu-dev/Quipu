分析正确。

这是一个典型的 `ImportError`，它暴露了我上一步计划中的一个疏忽。`unittest.mock` 模块本身并不导出一个名为 `mock` 的对象供我们导入；`mock` 是 `unittest` 下的一个模块。当我们需要使用 `mock.ANY` 或 `mock.MagicMock` 时，正确的导入方式是 `from unittest import mock`。然而，更符合 Python 风格且更简洁的做法是直接导入我们需要的具体对象，例如 `MagicMock` 和 `ANY`。

我之前生成的代码错误地混合了两种方式，导致了 `ImportError`。我将立即修正这个问题。

## [WIP] fix: 修正 `test_unfriendly_paths.py` 中的 ImportError

### 错误分析
测试执行失败，原因为 `ImportError: cannot import name 'mock' from 'unittest.mock'`。这是因为在 `tests/cli/test_unfriendly_paths.py` 文件中，使用了错误的导入语句 `from unittest.mock import MagicMock, mock`。

正确的做法是直接从 `unittest.mock` 导入需要使用的 `MagicMock` 和 `ANY` 对象。

### 用户需求
修正 `tests/cli/test_unfriendly_paths.py` 文件中的导入语句和相关的代码，解决 `ImportError`，使测试套件能够正常运行。

### 评论
这是一个简单的编码错误，但它阻断了我们的开发流程。立即修复它是恢复测试套件健康、继续进行重构任务的必要步骤。

### 目标
1.  修改 `test_unfriendly_paths.py` 中的导入语句为 `from unittest.mock import MagicMock, ANY`。
2.  将代码中所有对 `mock.ANY` 的引用修改为 `ANY`。

### 基本原理
遵循 Python 标准库的导入规范。直接导入所需的类和常量，而不是试图导入模块本身作为命名空间（除非使用 `from unittest import mock` 这种形式）。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 `test_unfriendly_paths.py`

我将使用 `write_file` 完整地重写该文件，以确保所有导入和引用都得到正确修正。

```````act
write_file
tests/cli/test_unfriendly_paths.py
```````
```````python
import pytest
import click
from typer.testing import CliRunner
from unittest.mock import MagicMock, ANY

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
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.run.bus", mock_bus)
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

    assert result.exit_code == 2
    mock_bus.warning.assert_called_once_with("run.error.cancelled", error=ANY)
    assert not output_file.exists()


def test_run_command_in_non_interactive_env(runner: CliRunner, quipu_workspace, monkeypatch):
    """
    不友好路径测试: 验证在非交互式环境 (无法 getchar) 中，`run` 操作会自动中止。
    """
    work_dir, _, _ = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.run.bus", mock_bus)
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
    mock_bus.warning.assert_called_once_with("run.error.cancelled", error=ANY)
    assert not output_file.exists()


# --- Tests for `quipu discard` ---


def test_discard_user_cancellation(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `discard` 操作可以被用户取消。"""
    work_dir, _, _ = dirty_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.workspace.bus", mock_bus)

    def mock_getchar_n(echo):
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)
    result = runner.invoke(app, ["discard", "-w", str(work_dir)])

    assert result.exit_code == 1  # typer.Abort exits with 1
    mock_bus.warning.assert_called_once_with("common.prompt.cancel")
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


def test_discard_in_non_interactive_env(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `discard` 在非交互式环境中安全中止。"""
    work_dir, _, _ = dirty_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.workspace.bus", mock_bus)

    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)
    result = runner.invoke(app, ["discard", "-w", str(work_dir)])

    assert result.exit_code == 1  # typer.Abort exits with 1
    mock_bus.warning.assert_called_once_with("common.prompt.cancel")
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


# --- Tests for `quipu checkout` ---


def test_checkout_user_cancellation(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `checkout` 操作可以被用户取消。"""
    work_dir, _, hash_a = dirty_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.navigation.bus", mock_bus)

    def mock_getchar_n(echo):
        click.echo("n", err=True)
        return "n"

    monkeypatch.setattr(click, "getchar", mock_getchar_n)
    result = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(work_dir)])

    assert result.exit_code == 1
    mock_bus.warning.assert_called_once_with("common.prompt.cancel")
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."


def test_checkout_in_non_interactive_env(runner: CliRunner, dirty_workspace, monkeypatch):
    """不友好路径测试: 验证 `checkout` 在非交互式环境中安全中止。"""
    work_dir, _, hash_a = dirty_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.navigation.bus", mock_bus)

    def mock_getchar_fail(echo):
        raise EOFError("Simulating non-interactive environment")

    monkeypatch.setattr(click, "getchar", mock_getchar_fail)
    result = runner.invoke(app, ["checkout", hash_a[:7], "-w", str(work_dir)])

    assert result.exit_code == 1
    mock_bus.warning.assert_called_once_with("common.prompt.cancel")
    assert (work_dir / "file.txt").read_text() == "v3", "File should not be changed."
```````

### 下一步建议
测试障碍已清除。我们现在可以安全地回到主线上，继续执行重构计划的第七阶段：迁移最后一批独立功能命令 (`remote`, `export`, `ui`) 到 `MessageBus`。
