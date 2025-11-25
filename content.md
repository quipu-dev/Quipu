# build: 采用依赖委托模式正确配置 Monorepo

## 目标
修改根 `pyproject.toml`，从“包发现”模式切换到“依赖委托”模式，以正确地在开发环境中安装所有子包，并最终解决 `quipu` 命令的 `ModuleNotFoundError`。

## 基本原理
`setuptools` 的 `find_packages` 功能难以处理我们这种包含多个 `src`-layout 的 Monorepo 结构，导致开发模式 (`pip install -e .`) 安装不完整。

我们将改变策略：不再让顶层包自己去寻找所有模块，而是让它通过 `[project.dependencies]` 明确声明对本地子包的依赖。`pip` 会解析这些本地依赖，并分别对每个子包执行正确的、独立的开发模式安装。这确保了每个子包的 `src` 目录都被正确地链接到 Python 环境中，从而构建出完整的 `quipu` 命名空间。

## 标签
#fix #build #chore

---

## Script

### Act 1: 重构根 pyproject.toml 以使用本地路径依赖

此操作将移除 `[tool.setuptools.packages.find]` 并添加 `[project.dependencies]`，将安装逻辑委托给各个子包。

~~~~~act
write_file pyproject.toml
~~~~~

~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-dev"
version = "0.1.0"
description = "Metapackage for the Quipu monorepo development environment."
requires-python = ">=3.8"
dependencies = [
    "quipu-interfaces @ file:./packages/quipu-interfaces",
    "quipu-engine @ file:./packages/quipu-engine",
    "quipu-runtime @ file:./packages/quipu-runtime",
    "quipu-cli @ file:./packages/quipu-cli",
]

[project.scripts]
quipu = "quipu.cli.main:app"

[tool.setuptools]
py-modules = []

[tool.pytest.ini_options]
pythonpath = [
    ".",
    "packages/quipu-interfaces/src",
    "packages/quipu-engine/src",
    "packages/quipu-runtime/src",
    "packages/quipu-cli/src",
]
testpaths = ["tests"]
log_cli = true
log_cli_level = "INFO"
~~~~~