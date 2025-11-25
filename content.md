# chore: 为拆分后的包创建 pyproject.toml 配置文件

## 目标
为 `packages/` 目录下的 `quipu-interfaces`、`quipu-engine`、`quipu-runtime` 和 `quipu-cli` 四个包，以及项目根目录，创建 `pyproject.toml` 文件。这些文件将定义每个包的元数据、依赖关系和安装配置。

## 基本原理
`pyproject.toml` 是现代 Python 项目的标准配置文件。通过为每个包创建独立的配置文件，我们能够：
1.  **明确依赖**：清晰地声明每个包依赖于哪些其他包 (`quipu-interfaces`) 或第三方库 (`typer`)。
2.  **可安装性**：使每个包都可以通过 `pip install -e .` 进行本地编辑模式安装，从而在开发环境中解决模块导入问题。
3.  **入口点**：为 `quipu-cli` 包定义一个命令行入口点，使其安装后能直接通过 `quipu` 命令执行。
4.  **工作区管理**：顶层的 `pyproject.toml` 将整个 `packages` 目录声明为一个命名空间，便于统一管理和测试。

## 标签
完成核心模块的重构。 #chore #build #packages

---

## Script

### Act 1: 创建 `quipu-interfaces` 的配置文件

这是最基础的包，不依赖于项目内的其他包。

~~~~~act
write_file packages/quipu-interfaces/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-interfaces"
version = "0.1.0"
authors = [
  { name="doux", email="douxldh@gmail.com" },
]
description = "Core interfaces and data models for the Quipu ecosystem."
readme = "README.md"
requires-python = ">=3.8"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
write_file packages/quipu-interfaces/README.md
~~~~~
~~~~~markdown
# Quipu Interfaces

This package provides the core interfaces, abstract base classes, and data models that are shared across all other Quipu packages. It ensures a consistent and stable API for inter-module communication.
~~~~~

### Act 2: 创建 `quipu-engine` 的配置文件

此包依赖 `quipu-interfaces`。

~~~~~act
write_file packages/quipu-engine/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-engine"
version = "0.1.0"
authors = [
  { name="doux", email="douxldh@gmail.com" },
]
description = "The state and history engine for Quipu, powered by Git plumbing."
requires-python = ">=3.8"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "quipu-interfaces",
    "pyyaml>=6.0",
]

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

### Act 3: 创建 `quipu-runtime` 的配置文件

此包依赖 `quipu-interfaces`。

~~~~~act
write_file packages/quipu-runtime/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-runtime"
version = "0.1.0"
authors = [
  { name="doux", email="douxldh@gmail.com" },
]
description = "The stateless execution runtime for Quipu, responsible for parsing and executing instructions."
requires-python = ">=3.8"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "quipu-interfaces",
    "typer>=0.9.0"
]

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

### Act 4: 创建 `quipu-cli` 的配置文件

此包是胶水层，依赖所有其他包，并定义了命令行入口点。

~~~~~act
write_file packages/quipu-cli/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-cli"
version = "0.1.0"
authors = [
  { name="doux", email="douxldh@gmail.com" },
]
description = "The command-line interface for Quipu, coordinating the engine and runtime."
requires-python = ">=3.8"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "quipu-interfaces",
    "quipu-engine",
    "quipu-runtime",
    "typer>=0.9.0",
    "textual>=0.58.0",
]

[project.scripts]
quipu = "quipu.cli.main:app"

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

### Act 5: 创建顶层 `pyproject.toml` 进行工作区管理

这个文件用于统一管理所有包，并配置开发工具如 `pytest`。

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

[tool.setuptools]
py-modules = []

[tool.setuptools.packages.find]
where = ["packages"]
include = ["quipu*"]

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