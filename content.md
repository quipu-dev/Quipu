# feat-build: 将核心 acts 打包进 quipu-runtime

## 目标
将核心 `acts` 目录重构为 `quipu-runtime` 包的一部分，确保在 `pip install` 后，核心指令能够被可靠地加载和执行，从而优化用户体验并增强系统的健壮性。

## 基本原理
当前 `acts` 目录作为项目根目录下的松散文件，依赖于不稳定的路径发现逻辑，导致在已安装的环境中无法被找到。

本计划将 `acts` 目录移动到 `packages/quipu-runtime/src/quipu/` 路径下，并将其转换为一个常规的 Python 包。我们将更新 `quipu-runtime` 的 `pyproject.toml` 以确保 `setuptools` 将此包及其内容包含在分发版中。

最后，我们将修改 `quipu-cli` 中的插件加载器，使用标准的 `importlib.resources` 库来定位已安装的内置 `acts` 包。这种方法与 Python 的安装机制完全解耦，确保无论 `quipu` 被安装在何处，其核心功能都立即可用。

## 标签
#feat #refactor #build #chore

---

## Script

### Act 1: 将 acts 目录移动到 quipu-runtime 包内

这是物理结构调整的第一步，将 `acts` 归入其逻辑属主 `quipu-runtime`。

~~~~~act
move_file acts packages/quipu-runtime/src/quipu/acts
~~~~~

### Act 2: 将新的 acts 目录转换为 Python 包

创建一个 `__init__.py` 文件，使 Python 的导入系统能够将 `quipu.acts` 识别为一个常规包。

~~~~~act
write_file packages/quipu-runtime/src/quipu/acts/__init__.py
~~~~~

~~~~~python

~~~~~

### Act 3: 更新 quipu-runtime 的打包配置

修改 `quipu-runtime/pyproject.toml`，确保 `setuptools` 能够发现并打包新的 `quipu.acts` 命名空间。

~~~~~act
replace packages/quipu-runtime/pyproject.toml
~~~~~

~~~~~toml
[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~toml
[tool.setuptools.packages.find]
where = ["src"]
~~~~~

### Act 4: 更新 CLI 控制器以使用 importlib.resources 加载内置插件

这是核心逻辑变更。我们将修改 `quipu-cli` 的 `controller.py`，用可靠的包资源 API 替代旧的、基于文件路径猜测的插件加载方式。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/controller.py
~~~~~

~~~~~python
        # 加载插件
        load_plugins(executor, PROJECT_ROOT / "acts") # 内置
        _load_extra_plugins(executor, project_root)       # 外部 (也基于 project_root)
~~~~~

~~~~~python
        # 加载插件
        # 1. 加载打包在 quipu-runtime 内的内置 Acts
        try:
            import importlib.resources
            # 使用新的 API 获取已安装包内模块的路径
            with importlib.resources.as_file(importlib.resources.files('quipu.acts')) as acts_path:
                load_plugins(executor, acts_path)
        except (ModuleNotFoundError, FileNotFoundError):
            logger.warning("⚠️  无法加载内置 Acts，可能是 quipu-runtime 包不完整。")
        
        # 2. 加载外部插件
        _load_extra_plugins(executor, project_root)
~~~~~