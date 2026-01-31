## [WIP] refactor: 适配 Needle 协议并修复 Bus API

### 用户需求
1.  **重构 Renderer**: 修改 `TyperRenderer` 以适配 Needle 的 `RendererProtocol` (`render(message, level, **kwargs)`).
2.  **扩展 Bus**: 在 `quipu.common.bus` 中子类化 Needle 的 `FeedbackBus`，添加 `data(data_string)` 方法以保持兼容性。
3.  **修复 API 调用**: 全局将 `bus.get(...)` 替换为 `bus.render_to_string(...)`。

### 评论
这些修改旨在弥合旧 Quipu Bus 和新 Needle Bus 之间的 API 差异。
*   `TyperRenderer` 的重构将集中处理不同级别的颜色逻辑。
*   `QuipuBus` 子类将充当适配器，让我们在不重写所有 `bus.data` 调用的情况下迁移。
*   `bus.get` -> `bus.render_to_string` 是直接的 API 映射。

### 目标
使代码库能够在新 Bus 架构下正常运行，解决最主要的 `AttributeError`。

### 基本原理
通过继承和适配，我们避免了对业务逻辑的大规模重写（尤其是数据输出部分），同时享受 Needle 带来的强大的语义指针和 I18N 能力。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #comp/common #task/domain/ui #task/object/bus #task/action/adapter #task/state/continue

---

### Script

#### Acts 1: 在 quipu.common.bus 中实现 QuipuBus

我们需要修改 `bus.py`，定义一个子类并实例化它，而不是直接使用 `needle.bus.bus`。

~~~~~act
write_file
packages/pyquipu-common/src/quipu/common/bus.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import Any, Optional, Protocol, Union

from needle.bus import FeedbackBus
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import nexus as global_nexus
from needle.spec import RendererProtocol, SemanticPointerProtocol


# --- 1. 定义扩展协议 ---
# 我们扩展 Needle 的 RendererProtocol，要求它支持 data() 方法
class QuipuRendererProtocol(RendererProtocol, Protocol):
    def data(self, data_string: str) -> None: ...


# --- 2. 定义支持 data 的 Bus 子类 ---
class QuipuBus(FeedbackBus):
    _renderer: Optional[QuipuRendererProtocol]  # type: ignore

    def data(self, data_string: str) -> None:
        """输出原始数据（如 JSON, Diff 等），通常去往 stdout。"""
        if self._renderer and hasattr(self._renderer, "data"):
            self._renderer.data(data_string)


def _detect_lang() -> str:
    """检测系统或环境变量中定义的语言。Quipu 默认为 zh。"""
    env_lang = os.getenv("QUIPU_LANG") or os.getenv("NEEDLE_LANG")
    if env_lang:
        return env_lang

    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "zh"


# --- 3. 初始化资源 ---
_assets_root = Path(__file__).parent / "assets"
_lang = _detect_lang()

_factory = I18NFactoryOperator(_assets_root)
_quipu_i18n = _factory(_lang)

_nexus = OverlayOperator([_quipu_i18n, global_nexus])

# --- 4. 实例化自定义 Bus ---
bus = QuipuBus()
bus.set_operator(_nexus)

__all__ = ["bus", "QuipuBus", "QuipuRendererProtocol"]
~~~~~

#### Acts 2: 重构 TyperRenderer

~~~~~act
write_file
packages/pyquipu-cli/src/quipu/cli/rendering.py
~~~~~
~~~~~python
from typing import Any

import typer


class TyperRenderer:
    """
    适配 Needle 的 RendererProtocol，并支持 Quipu 特有的 data() 输出。
    """

    def render(self, message: str, level: str = "info", **kwargs: Any) -> None:
        """
        实现 Needle 的标准渲染接口。
        """
        color = None
        err = True  # 默认输出到 stderr (反馈信息)

        if level == "success":
            color = typer.colors.GREEN
        elif level == "warning":
            color = typer.colors.YELLOW
        elif level == "error":
            color = typer.colors.RED
        elif level == "info":
            color = typer.colors.BLUE
        elif level == "debug":
            # Debug 可以在配置中关闭，或者输出为灰色
            # 这里简单处理，视为无色或灰色
            pass

        # Typer 的 secho 处理颜色和 stderr 输出
        typer.secho(message, fg=color, err=err)

    def data(self, data_string: str) -> None:
        """
        Quipu 特有接口：输出原始数据到 stdout。
        """
        typer.echo(data_string, err=False)
~~~~~

#### Acts 3: 替换 bus.get 为 bus.render_to_string

~~~~~act
run_command
~~~~~
~~~~~
grep -rl "bus.get(" packages/ | xargs sed -i 's/bus.get(/bus.render_to_string(/g'
~~~~~

### 下一步建议

代码现在应该可以运行了，但还存在一个巨大的隐患：
代码中充斥着大量的**字符串形式的消息 ID** (如 `"acts.basic.success"` )。
虽然 Needle 支持字符串 ID，但它的核心优势在于使用 `L` 指针 (如 `L.acts.basic.success`) 来获得类型检查和自动补全。

建议的后续步骤：
1.  **引入 L 指针**: 在需要的地方 `from needle.pointer import L`。
2.  **逐步替换**: 将字符串 ID 替换为 `L` 指针调用。这可以分模块进行。例如先从 `pyquipu-runtime` 开始。
