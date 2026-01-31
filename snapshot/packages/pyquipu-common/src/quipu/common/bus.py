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