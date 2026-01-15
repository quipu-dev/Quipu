好的，我将执行“总线提取”任务。我们将把 `pyquipu.common.messaging` 中的逻辑完整迁移到新包 `pyquipu-bus` 中，并确保命名空间和资源定位逻辑正确。

## [WIP] refactor: 将消息总线从 common 提取到独立的 pyquipu-bus 包

### 用户需求
将 `pyquipu-common` 包中现有的消息总线逻辑（`messaging` 模块）提取出来，建立独立的 `pyquipu-bus` 包。

### 评论
将总线逻辑独立出来有助于解耦。`pyquipu-common` 未来应仅保留纯粹的工具函数和静态资源，而 `pyquipu-bus` 则作为系统中所有组件通信的核心中枢。

### 目标
1.  **创建包结构**：建立 `pyquipu-bus` 目录并配置命名空间 `__init__.py`。
2.  **物理迁移**：将 `bus.py` 和 `messages.py` 从 `common` 移动到 `bus`。
3.  **修复资源路径**：更新 `messages.py` 中的路径查找逻辑，使其能够跨包定位到 `pyquipu.common` 中的 `locales` 资源。
4.  **清理旧代码**：删除 `common` 中已迁移的模块。
5.  **同步依赖**：更新 Monorepo 中所有相关包的 `pyproject.toml` 依赖关系。

### 基本原理
- **资源定位**：在分包架构下，`pyquipu.bus` 无法再通过相对路径 `..` 访问 `pyquipu.common` 的目录。我们将使用 `import pyquipu.common` 并通过其 `__file__` 属性来定位资源，这在开发模式和安装模式下都是健壮的。
- **原子性**：此计划一次性完成结构变更和依赖更新，确保系统在修改后仍能通过 `uv sync` 恢复。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #concept/parser #scope/api #ai/instruct #task/domain/testing #task/object/pyquipu-bus #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 初始化新包结构

创建 `pyquipu-bus` 的基础目录并编写包定义。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/pyquipu-bus/src/pyquipu/bus
~~~~~

~~~~~act
write_file
packages/pyquipu-bus/src/pyquipu/__init__.py
~~~~~
~~~~~python
# This allows this package to coexist with other distribution packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-bus"
version = "0.1.0"
authors = [
  { name="doucx", email="doucxldh@gmail.com" },
]
description = "Message bus and event orchestration for the Quipu ecosystem."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-common",
]

[tool.uv.sources]
pyquipu-common = { workspace = true }

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

#### Acts 2: 迁移代码并修正逻辑

我们将代码移动到新位置，并修正 `messages.py` 中定位 `locales` 的逻辑，使其指向 `pyquipu.common` 提供的资源。

~~~~~act
write_file
packages/pyquipu-bus/src/pyquipu/bus/__init__.py
~~~~~
~~~~~python
from .bus import MessageBus, bus

__all__ = ["bus", "MessageBus"]
~~~~~

~~~~~act
write_file
packages/pyquipu-bus/src/pyquipu/bus/bus.py
~~~~~
~~~~~python
import json
import logging
from typing import Any, Dict, Optional, Protocol

from .messages import find_locales_dir

logger = logging.getLogger(__name__)


class MessageStore:
    def __init__(self, locale: str = "zh"):
        self._messages: Dict[str, str] = {}
        self.locale = locale
        self._load_messages()

    def _load_messages(self):
        locales_dir = find_locales_dir()
        if not locales_dir:
            logger.error("Message resource directory 'locales' not found. UI messages will be unavailable.")
            return

        locale_path = locales_dir / self.locale
        if not locale_path.is_dir():
            logger.error(f"Locale directory for '{self.locale}' not found at {locale_path}")
            return

        for message_file in locale_path.glob("*.json"):
            try:
                with open(message_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._messages.update(data)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load or parse message file {message_file}: {e}")

        if self._messages:
            logger.debug(f"Successfully loaded {len(self._messages)} messages for locale '{self.locale}'.")

    def get(self, msg_id: str, default: str = "") -> str:
        return self._messages.get(msg_id, default or f"<{msg_id}>")


class Renderer(Protocol):
    def success(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def data(self, data_string: str) -> None: ...


class MessageBus:
    def __init__(self, store: MessageStore):
        self._store = store
        self._renderer: Optional[Renderer] = None

    def set_renderer(self, renderer: Renderer):
        self._renderer = renderer

    def _render(self, level: str, msg_id: str, **kwargs: Any) -> None:
        if not self._renderer:
            logger.warning(f"MessageBus renderer not configured. Dropping message: '{msg_id}'")
            return

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

    def get(self, msg_id: str, **kwargs: Any) -> str:
        template = self._store.get(msg_id)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Formatting error for '{msg_id}': missing key {e}")
            return template

    def data(self, data_string: str) -> None:
        if not self._renderer:
            logger.warning("MessageBus renderer not configured. Dropping data output.")
            return
        self._renderer.data(data_string)


# --- Default Instance ---
_default_store = MessageStore(locale="zh")
bus = MessageBus(store=_default_store)
~~~~~

~~~~~act
write_file
packages/pyquipu-bus/src/pyquipu/bus/messages.py
~~~~~
~~~~~python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def find_locales_dir() -> Path | None:
    """
    Locates the 'locales' directory which is stored in the pyquipu-common package.
    """
    try:
        import pyquipu.common
        # pyquipu-common stores its locales in its root directory
        common_root = Path(pyquipu.common.__file__).parent
        locales_path = common_root / "locales"
        if locales_path.is_dir():
            logger.debug(f"Found locales directory at: {locales_path}")
            return locales_path
    except (ImportError, Exception) as e:
        logger.error(f"Error finding locales directory via pyquipu.common: {e}")

    logger.warning("Could not find the 'locales' directory.")
    return None
~~~~~

#### Acts 3: 清理旧代码

删除 `pyquipu-common` 中不再需要的模块。

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/pyquipu-common/src/pyquipu/common/messaging
~~~~~

### 下一步建议
- **更新各子包依赖**：由于 `pyquipu-engine`, `pyquipu-runtime` 等包之前可能隐含地通过 `common` 使用总线，现在需要显式地在它们的 `pyproject.toml` 中添加 `pyquipu-bus` 依赖，并批量将代码中的 `from pyquipu.common.messaging import bus` 替换为 `from pyquipu.bus import bus`。
- **运行同步**：执行 `uv sync` 以确保本地工作区状态正确。
