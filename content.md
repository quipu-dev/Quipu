好的，我将执行 `MessageBus` 统一输出层规范的第一步：在 `quipu-common` 包中创建 `MessageBus` 的初始实现，并建立相应的 `locales/zh/cli.json` 资源文件。

## [WIP] feat: 为 CLI 输出实现 MessageBus 基础设施

### 用户需求
根据 `MessageBus` 统一输出层规范文档，需要搭建 `MessageBus` 的核心基础设施。这包括：
1.  在 `quipu-common` 包中创建 `MessageBus` 的核心类。
2.  建立 `locales/zh/cli.json` 语言资源文件，并添加初始消息模板。
3.  为 `quipu-common` 包添加 `typer` 依赖，因为渲染层需要它。

### 评论
这是解耦 CLI 业务逻辑与用户呈现的关键第一步。通过建立这个“输出网关”，我们为未来实现可测试、可维护、可国际化的 CLI 输出奠定了坚实的基础。

### 目标
1.  创建 `packages/quipu-common/src/quipu/common/messaging.py` 文件，包含 `MessageBus`、`MessageStore` 和 `TyperRenderer` 的初始实现。
2.  创建 `locales/zh/cli.json` 文件，并填充一些来自 `workspace` 命令的示例消息。
3.  更新 `packages/quipu-common/pyproject.toml` 文件，将 `typer` 添加为依赖项。

### 基本原理
1.  **`MessageStore`**: 负责从文件系统中加载和缓存 JSON 格式的消息模板，将内容与代码分离。
2.  **`TyperRenderer`**: 封装所有与 `typer` 相关的格式化逻辑（颜色、图标），将呈现与消息分离。
3.  **`MessageBus`**: 作为公共 API，协调 `MessageStore` 和 `TyperRenderer`，为上层应用提供语义化的输出方法（如 `.success()`, `.error()`），将意图与实现分离。
4.  **`locales/` 目录**: 作为项目级的资源目录，集中管理所有面向用户的文本，为未来的国际化做准备。

### 标签
#intent/architect #flow/ready #priority/high #comp/common #comp/cli #concept/ui #scope/dx #ai/instruct #task/domain/messaging #task/object/message-bus #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 `MessageBus` 核心逻辑

我们首先创建 `messaging.py` 文件，它将包含 `MessageBus` 基础设施的全部核心类。

~~~~~act
write_file
packages/quipu-common/src/quipu/common/messaging.py
~~~~~
~~~~~python
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import typer

logger = logging.getLogger(__name__)


class MessageStore:
    """负责加载和缓存指定语言环境下的所有消息模板。"""

    def __init__(self, locales_dir: Path, locale: str = "zh", domain: str = "cli"):
        self.locales_dir = locales_dir
        self.locale = locale
        self.domain = domain
        self._messages = self._load_messages()

    @lru_cache(maxsize=None)
    def _load_messages(self) -> Dict[str, str]:
        """从 JSON 文件加载消息模板。"""
        file_path = self.locales_dir / self.locale / f"{self.domain}.json"
        if not file_path.exists():
            logger.error(f"Message file not found: {file_path}")
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load or parse message file {file_path}: {e}")
            return {}

    def get(self, msg_id: str, default: Optional[str] = None) -> str:
        """根据消息 ID 获取消息模板。"""
        return self._messages.get(msg_id, default or f"<{msg_id} not found>")


class TyperRenderer:
    """使用 Typer 渲染消息，包含颜色和图标。"""

    ICON_MAP = {
        "success": "✅",
        "info": "⚙️",
        "warning": "⚠️",
        "error": "❌",
    }
    COLOR_MAP = {
        "success": typer.colors.GREEN,
        "info": typer.colors.BLUE,
        "warning": typer.colors.YELLOW,
        "error": typer.colors.RED,
    }

    def render(self, level: str, message: str):
        """渲染带图标和颜色的消息到 stderr。"""
        icon = self.ICON_MAP.get(level, "➡️")
        color = self.COLOR_MAP.get(level)
        typer.secho(f"{icon} {message}", fg=color, err=True)

    def render_data(self, data_string: str):
        """将原始数据渲染到 stdout。"""
        typer.echo(data_string, err=False)


class MessageBus:
    """
    所有 CLI 命令与终端用户之间的唯一“输出网关”。
    彻底解耦“业务逻辑”与“用户呈现”。
    """

    def __init__(self, store: MessageStore, renderer: TyperRenderer):
        self._store = store
        self._renderer = renderer

    def _publish(self, level: str, msg_id: str, **kwargs):
        template = self._store.get(msg_id)
        try:
            message = template.format(**kwargs)
            self._renderer.render(level, message)
        except KeyError as e:
            # 格式化失败，打印一个有用的错误信息
            error_msg = f"MessageBus Error: Missing key {e} for msg_id '{msg_id}'"
            self._renderer.render("error", error_msg)
            logger.error(error_msg, exc_info=True)

    def success(self, msg_id: str, **kwargs):
        """报告成功的操作结果。"""
        self._publish("success", msg_id, **kwargs)

    def info(self, msg_id: str, **kwargs):
        """显示中性的、流程性的信息。"""
        self._publish("info", msg_id, **kwargs)

    def warning(self, msg_id: str, **kwargs):
        """提醒用户注意潜在问题。"""
        self._publish("warning", msg_id, **kwargs)

    def error(self, msg_id: str, **kwargs):
        """报告操作失败、错误或异常。"""
        self._publish("error", msg_id, **kwargs)

    def data(self, data_string: str):
        """输出命令的核心数据结果。"""
        self._renderer.render_data(data_string)


# --- Factory ---

_bus_instance: Optional[MessageBus] = None


def find_project_root(start_path: Path) -> Optional[Path]:
    """向上递归查找项目根目录（包含 'locales' 和 'pyproject.toml'）。"""
    current = start_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / "locales").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def get_message_bus() -> MessageBus:
    """
    获取 MessageBus 的单例实例。
    在第一次调用时，它会查找项目根目录并初始化实例。
    """
    global _bus_instance
    if _bus_instance is None:
        # 使用当前文件位置作为起点来查找项目根目录
        project_root = find_project_root(Path(__file__).parent)
        if not project_root:
            raise RuntimeError("Could not find project root with 'locales' directory.")

        locales_dir = project_root / "locales"
        store = MessageStore(locales_dir=locales_dir)
        renderer = TyperRenderer()
        _bus_instance = MessageBus(store, renderer)
    return _bus_instance
~~~~~

#### Acts 2: 创建语言资源文件

现在，我们在项目根目录下创建 `locales/zh/cli.json` 文件，并填入一些初始的消息。

~~~~~act
write_file
locales/zh/cli.json
~~~~~
~~~~~json
{
  "workspace.save.success": "📸 快照已保存: {short_hash}{msg_suffix}",
  "workspace.save.noChanges": "✅ 工作区状态未发生变化，无需创建快照。",
  "workspace.save.error": "❌ 创建快照失败: {error}",
  "workspace.discard.success": "✅ 工作区已成功恢复到节点 {short_hash}。",
  "workspace.discard.noChanges": "✅ 工作区已经是干净状态 ({short_hash})，无需操作。",
  "workspace.discard.error": "❌ 恢复状态失败: {error}",
  "error.fileNotFound": "❌ 错误: 找不到指令文件: {path}",
  "error.generic": "❌ 操作失败: {error}",
  "general.operationCancelled": "🚫 操作已取消。"
}
~~~~~

#### Acts 3: 更新 `quipu-common` 依赖

最后，我们将 `typer` 添加到 `quipu-common` 包的依赖项中。

~~~~~act
patch_file
packages/quipu-common/pyproject.toml
~~~~~
~~~~~toml
dependencies = []
~~~~~
~~~~~toml
dependencies = [
    "typer>=0.9.0",
]
~~~~~

### 下一步建议
基础设施已经搭建完毕。下一步，我们将遵循迁移路径的第二步，选择 `workspace.py` (`quipu save` 和 `quipu discard` 命令) 作为试点，将其中的 `typer.secho` 调用重构为使用我们新创建的 `MessageBus`。如果你同意，我将开始准备该计划。
