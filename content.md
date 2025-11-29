好的，我将执行这项重构任务。

这个重构的核心目标是解决 `quipu-cli` 内部的循环依赖与代码重复问题。我将创建一个统一的 UI 工具模块 `quipu.cli.ui_utils`，将所有用户确认逻辑集中于此，然后更新 `controller` 和 `commands` 模块以使用这个新的标准函数。

## [WIP] refactor(cli): 创建 ui_utils 模块以解决循环依赖

### 用户需求
根据之前的分析，需要重构 `quipu-cli` 以解决内部的循环依赖和代码重复问题。具体方案是创建一个新的 `quipu.cli.ui_utils` 模块，将通用的 UI 函数（如 `_prompt_for_confirmation`）移入其中，并让 `controller` 和 `commands` 模块都依赖它。

### 评论
这是一项关键的架构改进。通过集中化 UI 交互逻辑，我们不仅解决了潜在的循环依赖，还消除了重复代码，确保了整个命令行工具在用户确认流程上行为一致且健壮。这项重构直接提升了代码的可维护性和开发者体验。

### 目标
1.  创建 `packages/quipu-cli/src/quipu/cli/ui_utils.py` 文件，并实现一个统一的、健壮的 `prompt_for_confirmation` 函数。
2.  从 `packages/quipu-cli/src/quipu/cli/commands/helpers.py` 中移除旧的确认函数。
3.  更新所有使用旧函数的命令（`cache`, `navigation`, `workspace`）以调用新的 `ui_utils` 函数。
4.  更新 `packages/quipu-cli/src/quipu/cli/controller.py`，移除其内部重复的确认逻辑，并改为使用新的 `ui_utils` 函数。

### 基本原理
通过引入一个专门的 `ui_utils` 模块，我们建立了一个清晰的依赖关系：高层的 `controller` 和底层的 `commands` 都可以安全地依赖这个通用的工具模块，而它们之间不再需要直接或间接的相互依赖。新的 `prompt_for_confirmation` 函数将整合之前分散在各处的 `click.getchar()` 逻辑，并提供一个能同时处理简单提示和复杂 `diff` 预览的统一接口。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #concept/ui #scope/dx #ai/instruct #task/domain/cli #task/object/refactoring #task/action/dependency-resolution #task/state/begin

---

### Script

#### Acts 1: 创建统一的 UI 工具模块

我将首先创建 `ui_utils.py` 文件，并实现一个新的、功能统一的 `prompt_for_confirmation` 函数。这个函数将整合之前分散在 `controller` 和 `helpers` 中的逻辑。

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/ui_utils.py
~~~~~
~~~~~python
import click
import typer
from typing import List, Optional


def prompt_for_confirmation(prompt: str, diff_lines: Optional[List[str]] = None, default: bool = False) -> bool:
    """
    一个健壮、统一的 CLI 确认提示器。

    它能处理可选的 diff 显示、无需回车的单字符输入，
    并在非交互式环境中优雅地降级。

    Args:
        prompt: 显示给用户的主消息。
        diff_lines: 在提示前显示的可选 diff 字符串列表。
        default: 当用户直接按回车键时的默认返回值。

    Returns:
        如果用户确认则返回 True，否则返回 False。
    """
    if diff_lines:
        typer.echo("\n🔍 变更预览:", err=True)
        for line in diff_lines:
            if line.startswith("+"):
                typer.secho(line.strip("\n"), fg=typer.colors.GREEN, err=True)
            elif line.startswith("-"):
                typer.secho(line.strip("\n"), fg=typer.colors.RED, err=True)
            elif line.startswith("^"):
                typer.secho(line.strip("\n"), fg=typer.colors.BLUE, err=True)
            else:
                typer.echo(line.strip("\n"), err=True)
        typer.echo("", err=True)

    prompt_suffix = " [Y/n]: " if default else " [y/N]: "
    typer.secho(prompt + prompt_suffix, nl=False, err=True)

    try:
        # click.getchar() 会智能地尝试从 /dev/tty 读取
        char = click.getchar(echo=False)
        click.echo(char, err=True)  # 手动回显到 stderr
    except (OSError, EOFError):
        # 在完全没有 tty 的环境中 (例如 CI runner)，会抛出异常
        click.echo(" (non-interactive)", err=True)
        return False  # 非交互式环境应安全失败

    if not char or char == "\r" or char == "\n":
        return default

    if char.lower() == "y":
        return True
    if char.lower() == "n":
        return False

    return default
~~~~~

#### Acts 2: 移除旧的辅助函数

现在从 `commands/helpers.py` 中删除旧的 `_prompt_for_confirmation` 函数及其 `click` 导入。

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/helpers.py
~~~~~
~~~~~python
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, Optional

import click
import typer
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine
~~~~~
~~~~~python
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, Optional

import typer
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/helpers.py
~~~~~
~~~~~python
def _prompt_for_confirmation(message: str, default: bool = False) -> bool:
    """
    使用单字符输入请求用户确认，无需回车。
    此实现是健壮的，即使在 stdin 被管道占用的情况下也能工作。
    """
    prompt_suffix = " [Y/n]: " if default else " [y/N]: "
    typer.secho(message + prompt_suffix, nl=False, err=True)

    try:
        # click.getchar() 会智能地尝试从 /dev/tty 读取
        char = click.getchar(echo=False)
        click.echo(char, err=True)  # 手动回显到 stderr
    except (OSError, EOFError):
        # 在完全没有 tty 的环境中 (例如 CI runner)，会抛出异常
        click.echo(" (non-interactive)", err=True)
        return False

    if char.lower() == "y":
        return True
    if char.lower() == "n":
        return False

    return default


def _find_current_node(engine: Engine, graph: Dict[str, QuipuNode]) -> Optional[QuipuNode]:
~~~~~
~~~~~python
def _find_current_node(engine: Engine, graph: Dict[str, QuipuNode]) -> Optional[QuipuNode]:
~~~~~

#### Acts 3: 更新命令模块的依赖

接下来，我会更新所有 `commands` 子模块，让它们直接从新的 `ui_utils` 导入并使用 `prompt_for_confirmation`。

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/cache.py
~~~~~
~~~~~python
import logging
from pathlib import Path
from typing import Annotated

import typer

from .helpers import engine_context, _prompt_for_confirmation
from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
~~~~~
~~~~~python
import logging
from pathlib import Path
from typing import Annotated

import typer

from .helpers import engine_context
from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
from ..ui_utils import prompt_for_confirmation
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/cache.py
~~~~~
~~~~~python
    if not force:
        prompt = f"🚨 即将删除并重建数据库 {db_path}。\n此操作不可逆。是否继续？"
        if not _prompt_for_confirmation(prompt, default=False):
            typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
            raise typer.Abort()
~~~~~
~~~~~python
    if not force:
        prompt = f"🚨 即将删除并重建数据库 {db_path}。\n此操作不可逆。是否继续？"
        if not prompt_for_confirmation(prompt, default=False):
            typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
            raise typer.Abort()
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated

import typer

from .helpers import engine_context, _find_current_node, _execute_visit, _prompt_for_confirmation
from ..config import DEFAULT_WORK_DIR
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated

import typer

from .helpers import engine_context, _find_current_node, _execute_visit
from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python
            if not force:
                prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
                if not _prompt_for_confirmation(prompt, default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()
~~~~~
~~~~~python
            if not force:
                prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
                if not prompt_for_confirmation(prompt, default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated, Optional

import typer

from .helpers import engine_context, _prompt_for_confirmation
from ..config import DEFAULT_WORK_DIR
~~~~~
~~~~~python
from pathlib import Path
from typing import Annotated, Optional

import typer

from .helpers import engine_context
from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/commands/workspace.py
~~~~~
~~~~~python
            if not force:
                prompt = f"🚨 即将丢弃上述所有变更，并恢复到状态 {latest_node.short_hash}。\n此操作不可逆。是否继续？"
                if not _prompt_for_confirmation(prompt, default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()
~~~~~
~~~~~python
            if not force:
                prompt = f"🚨 即将丢弃上述所有变更，并恢复到状态 {latest_node.short_hash}。\n此操作不可逆。是否继续？"
                if not prompt_for_confirmation(prompt, default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()
~~~~~

#### Acts 4: 重构核心控制器

最后，我将重构 `controller.py`，移除其内部的确认处理器，并使用一个适配器来调用新的 `ui_utils.prompt_for_confirmation` 函数。这彻底消除了代码重复。

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
import logging
import re
import sys
from pathlib import Path
from typing import List
import typer
import click

from quipu.interfaces.exceptions import ExecutionError as CoreExecutionError, OperationCancelledError
from quipu.runtime.executor import Executor
~~~~~
~~~~~python
import logging
import re
import sys
from pathlib import Path
from typing import List
import typer

from quipu.interfaces.exceptions import ExecutionError as CoreExecutionError, OperationCancelledError
from quipu.runtime.executor import Executor
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
from quipu.engine.state_machine import Engine
from quipu.acts import register_core_acts
from .factory import create_engine
from .plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class QuipuApplication:
~~~~~
~~~~~python
from quipu.engine.state_machine import Engine
from quipu.acts import register_core_acts
from .factory import create_engine
from .plugin_manager import PluginManager
from .ui_utils import prompt_for_confirmation

logger = logging.getLogger(__name__)


def confirmation_handler_for_executor(diff_lines: List[str], prompt: str) -> bool:
    """
    为 Executor 的确认处理器契约提供的适配器。
    它调用统一的提示器，并在用户取消时抛出异常。
    对于 'run' 操作，默认行为是继续，除非用户按下 'n'。
    """
    # 原始逻辑是 `char.lower() != "n"`，这相当于默认为 True
    confirmed = prompt_for_confirmation(prompt=prompt, diff_lines=diff_lines, default=True)
    if not confirmed:
        raise OperationCancelledError("User cancelled the operation.")
    # 执行器的处理器不使用布尔返回值，它依赖于异常。
    # 但为保持契约一致性，我们返回 True。
    return True


class QuipuApplication:
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/quipu/cli/controller.py
~~~~~
~~~~~python
    def _setup_executor(self) -> Executor:
        """创建、配置并返回一个 Executor 实例，并注入 UI 依赖。"""

        def typer_confirmation_handler(diff_lines: List[str], prompt: str) -> bool:
            """一个封装了 Typer UI 逻辑的确认处理器。"""
            typer.echo("\n🔍 变更预览:")
            for line in diff_lines:
                if line.startswith("+"):
                    typer.secho(line.strip("\n"), fg=typer.colors.GREEN, err=True)
                elif line.startswith("-"):
                    typer.secho(line.strip("\n"), fg=typer.colors.RED, err=True)
                elif line.startswith("^"):
                    typer.secho(line.strip("\n"), fg=typer.colors.BLUE, err=True)
                else:
                    typer.echo(line.strip("\n"), err=True)
            typer.echo("", err=True)

            typer.secho(f"{prompt} [Y/n]: ", nl=False, err=True)

            try:
                char = click.getchar(echo=False)
                click.echo(char, err=True)
                confirmed = char.lower() != "n"
            except (OSError, EOFError):
                click.echo(" (non-interactive)", err=True)
                confirmed = False

            if not confirmed:
                raise OperationCancelledError("User cancelled or non-interactive.")

            return True

        executor = Executor(
            root_dir=self.work_dir,
            yolo=self.yolo,
            confirmation_handler=typer_confirmation_handler,
        )
~~~~~
~~~~~python
    def _setup_executor(self) -> Executor:
        """创建、配置并返回一个 Executor 实例，并注入 UI 依赖。"""

        executor = Executor(
            root_dir=self.work_dir,
            yolo=self.yolo,
            confirmation_handler=confirmation_handler_for_executor,
        )
~~~~~

### 下一步建议
我们已经成功地将 UI 确认逻辑集中到了 `ui_utils.py` 模块中。
- **验证**: 请运行 `tests/cli/test_cli_interaction.py` 和 `tests/cli/test_workspace_commands.py` 中的交互式测试，以确保重构后的确认流程在管道输入和直接 TTY 输入两种模式下都能正常工作。
- **扩展**: 未来可以考虑将更多的通用 CLI UI 组件（如进度条、表格渲染器）抽象到 `ui_utils` 模块中，进一步强化 CLI 的代码组织。
