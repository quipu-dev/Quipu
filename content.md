好的，我们开始实施 `MessageBus` 的基础设施。

这个计划的目标是在 `quipu-common` 包中创建 `MessageBus` 系统的核心组件，并建立存放消息模板的 `locales` 目录结构。这是实现 CLI 输出与业务逻辑解耦的第一步，也是最关键的一步。

## [WIP] feat: 在 quipu-common 中实现 MessageBus 基础设施

### 用户需求
根据 `MessageBus 统一输出层规范文档 (v1.0)`，需要创建 `MessageBus` 的初始实现，包括其核心类 (`MessageBus`, `MessageStore`, `TyperRenderer`)、消息资源文件加载逻辑，以及包含初始消息模板的 `locales/zh/cli.json` 文件。

### 评论
这是整个重构任务的基石。通过建立这个基础设施，我们为后续将所有 `typer.secho` 调用迁移到语义化的 `bus.<method>()` 调用铺平了道路。将此逻辑放在 `quipu-common` 中确保了其通用性和可复用性。

### 目标
1.  在 `packages/quipu-common/src/quipu/common/` 目录下创建一个新的 `messaging` 包。
2.  在 `messaging` 包中实现 `MessageBus` 及其依赖项。
3.  在项目根目录下创建 `locales/zh/cli.json` 文件，并添加初始的消息模板。
4.  更新 `quipu-common` 的 `pyproject.toml` 文件，添加 `typer` 作为依赖。

### 基本原理
我们将创建一个三层结构：
1.  `MessageStore`: 负责从文件系统加载和缓存 JSON 格式的消息模板。
2.  `TyperRenderer`: 负责将格式化后的消息字符串使用 `typer` 渲染到终端，处理颜色和输出流 (stdout/stderr)。
3.  `MessageBus`: 作为公共 API，协调 `Store` 和 `Renderer`，供上层应用 (CLI 命令) 调用。

同时，我们会创建一个默认的 `bus` 实例，简化在项目初期的集成工作，避免引入复杂的依赖注入。

### 标签
#intent/architect #flow/ready #priority/high #comp/common #concept/ui #scope/core #scope/dx #ai/instruct #task/domain/ui #task/object/message-bus #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 `messaging` 包与核心文件

我们在 `quipu-common` 中创建 `messaging` 包，并加入 `messages.py` (用于定位资源文件) 和 `bus.py` (核心实现)。

~~~~~act
write_file
packages/quipu-common/src/quipu/common/messaging/messages.py
~~~~~
~~~~~python
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def find_locales_dir() -> Path | None:
    """
    Find the 'locales' directory, searching upwards from this file.
    This allows finding the directory both in development (monorepo root)
    and in installed environments (site-packages).
    """
    current = Path(__file__).resolve()
    # In a monorepo dev setup, it's at the project root.
    for parent in [current] + list(current.parents):
        locales_path = parent / "locales"
        if locales_path.is_dir():
            logger.debug(f"Found locales directory at: {locales_path}")
            return locales_path
    
    logger.warning("Could not find the 'locales' directory.")
    return None
~~~~~

~~~~~act
write_file
packages/quipu-common/src/quipu/common/messaging/bus.py
~~~~~
~~~~~python
import json
import logging
from pathlib import Path
from typing import Dict, Any, Protocol

import typer

from .messages import find_locales_dir

logger = logging.getLogger(__name__)


class MessageStore:
    """Loads and provides access to message templates from a JSON file."""

    def __init__(self, locale: str = "zh"):
        self._messages: Dict[str, str] = {}
        self.locale = locale
        self._load_messages()

    def _load_messages(self):
        locales_dir = find_locales_dir()
        if not locales_dir:
            logger.error("Message resource directory 'locales' not found. UI messages will be unavailable.")
            return

        message_file = locales_dir / self.locale / "cli.json"
        if not message_file.exists():
            logger.error(f"Message file for locale '{self.locale}' not found at {message_file}")
            return

        try:
            with open(message_file, "r", encoding="utf-8") as f:
                self._messages = json.load(f)
            logger.debug(f"Successfully loaded {len(self._messages)} messages for locale '{self.locale}'.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load or parse message file {message_file}: {e}")

    def get(self, msg_id: str, default: str = "") -> str:
        """Retrieves a message template by its ID."""
        return self._messages.get(msg_id, default or f"<{msg_id}>")


class Renderer(Protocol):
    """Protocol defining the interface for a message renderer."""

    def success(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def data(self, data_string: str) -> None: ...


class TyperRenderer:
    """A renderer that uses Typer for colored and styled CLI output."""

    def success(self, message: str) -> None:
        typer.secho(message, fg=typer.colors.GREEN, err=True)

    def info(self, message: str) -> None:
        typer.secho(message, fg=typer.colors.BLUE, err=True)

    def warning(self, message: str) -> None:
        typer.secho(message, fg=typer.colors.YELLOW, err=True)

    def error(self, message: str) -> None:
        typer.secho(message, fg=typer.colors.RED, err=True)

    def data(self, data_string: str) -> None:
        typer.echo(data_string, err=False) # Explicitly to stdout


class MessageBus:
    """The central service for all user-facing CLI output."""

    def __init__(self, store: MessageStore, renderer: Renderer):
        self._store = store
        self._renderer = renderer

    def _render(self, level: str, msg_id: str, **kwargs: Any) -> None:
        template = self._store.get(msg_id)
        try:
            message = template.format(**kwargs)
        except KeyError as e:
            message = f"<Formatting error for '{msg_id}': missing key {e}>"
            logger.warning(message)
        
        render_method = getattr(self._renderer, level)
        render_method(message)

    def success(self, msg_id: str, **kwargs: Any) -> None:
        self._render("success", msg_id, **kwargs)

    def info(self, msg_id: str, **kwargs: Any) -> None:
        self._render("info", msg_id, **kwargs)

    def warning(self, msg_id: str, **kwargs: Any) -> None:
        self._render("warning", msg_id, **kwargs)

    def error(self, msg_id: str, **kwargs: Any) -> None:
        self._render("error", msg_id, **kwargs)

    def data(self, data_string: str) -> None:
        self._renderer.data(data_string)


# --- Default Instance ---
# A default instance that can be easily imported and used.
# This avoids the need for complex dependency injection in the early stages.
_default_store = MessageStore(locale="zh")
_default_renderer = TyperRenderer()
bus = MessageBus(store=_default_store, renderer=_default_renderer)
~~~~~

~~~~~act
write_file
packages/quipu-common/src/quipu/common/messaging/__init__.py
~~~~~
~~~~~python
from .bus import bus, MessageBus

__all__ = ["bus", "MessageBus"]
~~~~~

#### Acts 2: 创建 `locales` 目录和消息文件

现在，我们在项目根目录创建 `locales/zh/cli.json` 文件，并填入一些初始的消息。

~~~~~act
run_command
mkdir -p locales/zh
~~~~~

~~~~~act
write_file
locales/zh/cli.json
~~~~~
~~~~~json
{
  "common.error.generic": "❌ 系统错误: {error}",
  "common.prompt.cancel": "\n🚫 操作已取消。",
  "workspace.save.success": "📸 快照已保存: {short_hash}{msg_suffix}",
  "workspace.save.noChanges": "✅ 工作区状态未发生变化，无需创建快照。",
  "workspace.save.error": "❌ 创建快照失败: {error}"
}
~~~~~

#### Acts 3: 更新 `quipu-common` 的依赖

最后，我们将 `typer` 添加到 `quipu-common` 的依赖项中，因为 `TyperRenderer` 需要它。

~~~~~act
patch_file
packages/quipu-common/pyproject.toml
~~~~~
~~~~~toml
dependencies = []
~~~~~
~~~~~toml
dependencies = [
    "typer>=0.9.0"
]
~~~~~

### 下一步建议
基础设施已经准备就绪。下一步是进行试点重构：

1.  选择一个简单的命令，例如 `quipu save` (位于 `packages/quipu-cli/src/quipu/cli/commands/workspace.py`)。
2.  将 `workspace.py` 中所有的 `typer.secho` 调用替换为对 `bus.success`, `bus.error` 等方法的调用。
3.  更新 `tests/cli/test_workspace_commands.py`，使用 `unittest.mock` 来 Mock `MessageBus` 实例，并断言其方法调用，而不是检查 `result.stderr` 中的字符串。

如果你同意，我将为你生成执行此试点重构的计划。
