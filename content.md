## [WIP] feat: 创建 Quipu Common Bus

### 用户需求
在 `packages/pyquipu-common` 中创建新的 `bus.py`，作为 Quipu 系统基于 `pyneedle-bus` 的新总线入口，负责初始化和注册资源文件。

### 评论
这是从旧的 `stitcher-bus` (或 `pyquipu-bus`) 迁移到 `pyneedle-bus` 架构的关键一步。这个文件将成为整个 Quipu 生态系统的“喉舌”，负责加载我们在上一步迁移的 JSON 资源，并配置 Needle 的反馈总线。

### 目标
1.  在 `packages/pyquipu-common/src/quipu/common/` 目录下创建 `bus.py`。
2.  实现语言检测逻辑（默认为 `zh`）。
3.  初始化 `pyneedle` 的 `I18NFactoryOperator` 并加载同级目录下的 `assets`。
4.  将配置好的 Operator 注入到全局 `bus` 单例中。

### 基本原理
我们将遵循 Needle 的最佳实践，通过 `OverlayOperator` 将 Quipu 的本地资源 (`_quipu_i18n`) 叠加在全局 Nexus 之上。这样既保证了 Quipu 自身的国际化支持，也允许未来与其他 Needle 驱动的库共存。

### 标签
#intent/build #flow/ready #priority/high #comp/interfaces #concept/ui #task/domain/ui #task/object/bus #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 创建 bus.py

~~~~~act
write_file
packages/pyquipu-common/src/quipu/common/bus.py
~~~~~
~~~~~python
import os
from pathlib import Path

from needle.bus import bus
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import nexus as global_nexus


def _detect_lang() -> str:
    """检测系统或环境变量中定义的语言。Quipu 默认为 zh。"""
    # 1. 显式覆盖
    env_lang = os.getenv("QUIPU_LANG") or os.getenv("NEEDLE_LANG")
    if env_lang:
        return env_lang

    # 2. 系统 LANG 变量
    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "zh"


# 1. 定位资产根目录与语言
# 资产目录应由迁移脚本放置在此文件同级的 assets 目录下
_assets_root = Path(__file__).parent / "assets"
_lang = _detect_lang()

# 2. 组装 Quipu 专属的 Operator
# I18NFactoryOperator 负责根据语言代码从资产目录加载 FileSystemOperator
_factory = I18NFactoryOperator(_assets_root)
_quipu_i18n = _factory(_lang)

# 3. 构造 Nexus (层叠 Operator)
# 优先级：Quipu 本地资产 > 全局默认 Nexus
_nexus = OverlayOperator([_quipu_i18n, global_nexus])

# 4. 注入到全局反馈总线
# 这样 bus.present(), bus.info() 等方法就能使用组装好的解析逻辑
bus.set_operator(_nexus)

# 5. 导出全局单例
__all__ = ["bus"]
~~~~~

### 下一步建议

现在新的总线入口已经建立，接下来的工作是：
1.  **更新依赖**: 修改 `packages/pyquipu-common/pyproject.toml`，添加 `pyneedle-bus` 依赖。
2.  **清理旧包**: 删除 `packages/pyquipu-bus`。
3.  **全局重构**: 将项目中所有引用旧 bus 的地方（`from quipu.bus import bus`）修改为新路径（`from quipu.common.bus import bus`），并使用 `L` 指针替换硬编码的字符串 ID。
