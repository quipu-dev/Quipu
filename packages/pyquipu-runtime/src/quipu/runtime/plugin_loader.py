import importlib.util
import logging
import sys
from pathlib import Path

from .executor import Executor

logger = logging.getLogger(__name__)


def load_plugins(executor: Executor, plugin_dir: Path):
    if not plugin_dir.exists():
        return

    logger.debug(f"正在从 '{plugin_dir}' 加载插件...")

    if not plugin_dir.is_dir():
        logger.warning(f"路径 '{plugin_dir}' 不是目录，跳过插件加载。")
        return

    for file_path in plugin_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue

        safe_name = f"quipu_plugin_{file_path.stem}_{abs(hash(str(file_path)))}"

        try:
            spec = importlib.util.spec_from_file_location(safe_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[safe_name] = module
                spec.loader.exec_module(module)

                if hasattr(module, "register"):
                    register_func = module.register
                    register_func(executor)
                    logger.debug(f"成功加载插件: {file_path.name}")
            else:
                logger.error(f"无法为 {file_path} 创建模块规范")
        except Exception as e:
            logger.error(f"加载插件 {file_path.name} 失败: {e}")
