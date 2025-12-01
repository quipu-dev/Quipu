## [WIP] feat: 创建 pyquipu-application 包基础设施

### 用户需求
为了实现核心业务逻辑与 CLI 表现层的解耦，并为未来的 Web API 提供支持，需要创建一个名为 `pyquipu-application` 的新包。

### 目标
1.  在 `packages/` 下创建标准的 Python 包目录结构 `quipu-application`。
2.  创建 `pyproject.toml` 配置文件，声明其对 `engine`, `runtime`, `interfaces`, `common` 的依赖。
3.  将新包注册到开发环境配置 (`dev-requirements.txt`) 中。

### 基本原理
我们将遵循 Monorepo 中现有的包命名和结构规范。
- 目录名：`packages/quipu-application` (保持与 `quipu-cli` 等一致)。
- 包名：`pyquipu-application` (在 `pyproject.toml` 中定义)。
- 依赖管理：利用 `uv` 的 workspace 功能管理本地依赖。

这将为第二阶段的代码迁移提供物理载体。

### 标签
#intent/architect #flow/ready #priority/high #comp/build #task/domain/core #task/object/package-structure #task/action/creation #task/state/begin

---

### Script

#### Acts 1: 创建目录结构与配置文件

我们首先创建目录树，然后写入包配置文件，最后更新开发环境依赖列表。

~~~~~act
run_command
mkdir -p packages/quipu-application/src/pyquipu/application
~~~~~

~~~~~act
write_file packages/quipu-application/src/pyquipu/application/__init__.py
~~~~~
~~~~~python
# pyquipu-application package
~~~~~

~~~~~act
write_file packages/quipu-application/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-application"
version = "0.1.0"
authors = [
  { name="doucx", email="doucxldh@gmail.com" },
]
description = "Core application logic for Quipu, orchestrating engine and runtime."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "pyquipu-runtime",
    "pyquipu-common",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
patch_file dev-requirements.txt
~~~~~
~~~~~text
-e packages/pyquipu-cli
-e packages/pyquipu-common
~~~~~
~~~~~text
-e packages/pyquipu-cli
-e packages/pyquipu-common
-e packages/quipu-application
~~~~~

### 下一步建议
基础设施建立完成后，请运行 `quipu run` 执行此计划。
执行完毕后，我们将进入 **阶段二：迁移与解耦**，开始将 `controller.py` 等核心文件从 CLI 移动到新包中。
