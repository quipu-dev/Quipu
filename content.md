这些警告是因为 `setuptools` 正在强制推行 **PEP 639** 标准。该标准改变了在 `pyproject.toml` 中声明许可证的方式：它现在要求使用一个简单的 SPDX 表达式字符串（如 `"Apache-2.0"`），而不是旧的表结构 `{ text = "..." }`，并且不再建议在 `classifiers` 中重复声明许可证。

正如你提供的 `Stitcher` 参考配置所示，使用 **`hatchling`** 作为构建后端是目前处理 Python Monorepo 的工业标准。它比 `setuptools` 更简洁，对工作区（Workspace）的支持也更原生。

我将生成一个计划，将 Quipu 的所有包从 `setuptools` 迁移到 `hatchling`，同时修复这些过时的许可证声明。

## [WIP] refactor: 迁移构建后端至 Hatchling 并修复 PEP 639 许可证警告

### 错误分析

1.  **许可证表废弃**: `project.license = { text = "..." }` 已被弃用。现代标准要求 `license = "SPDX-Identifier"`。
2.  **分类器冗余**: 在 `project.classifiers` 中包含 `License :: OSI Approved :: ...` 会导致冗余警告，因为 SPDX 表达式已经包含了这些信息。
3.  **构建后端陈旧**: `setuptools` 在处理复杂的 Monorepo 包发现（Package Discovery）时配置较为繁琐。

### 用户需求

1.  将所有子包和根包的构建后端切换为 `hatchling`。
2.  修复所有 `pyproject.toml` 中的许可证声明格式。
3.  移除重复的许可证分类器。
4.  标准化 `hatch` 构建目标配置。

### 评论

切换到 `hatchling` 是一个非常明智的决定。它不仅解决了当前的警告，还通过 `[tool.hatch.build.targets.wheel]` 提供了更确定的包包含逻辑，这对于在 Monorepo 中防止错误的源码被打包进 Wheel 至关重要。

### 目标

1.  修改 8 个子包的 `pyproject.toml`，更新 `build-system` 和 `license` 声明。
2.  为每个子包增加 `hatch` 专有的 `packages` 包含配置。
3.  更新根目录的 `pyproject.toml` 以保持一致性。

### 基本原理

*   **SPDX 表达式**: 遵循 PEP 639，直接使用字符串声明许可证。
*   **Hatch 目标定位**: 通过设置 `packages = ["src/quipu"]`，我们明确告诉 `hatchling` 源码位于 `src` 目录下，并以 `quipu` 作为包名。这消除了 `setuptools` 在自动发现时的不确定性。
*   **依赖稳定性**: 继续保持内部依赖使用 `~= 0.1.0` 格式。

### 标签

#intent/refine #flow/ready #priority/high #comp/build #concept/executor #scope/dx #ai/instruct #task/domain/tooling #task/object/hatchling-migration #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 更新基础子包 (Interfaces, Common, Bus, Engine)

我们将切换后端并简化许可证声明。

~~~~~act
write_file
packages/pyquipu-interfaces/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-interfaces"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core interfaces and data models for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-common"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common utilities and helpers for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-bus"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Message bus and event orchestration for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-common ~= 0.1.0",
]

[tool.uv.sources]
pyquipu-common = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-engine"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The state and history engine for Quipu, powered by Git plumbing."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyyaml >= 6.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

#### Acts 2: 更新逻辑与工具子包 (Runtime, App, CLI, Test-Utils)

~~~~~act
write_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-runtime"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The stateless execution runtime for Quipu."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "typer >= 0.9.0"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-application"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core application logic for Quipu, orchestrating engine and runtime."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

~~~~~act
write_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-cli"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The command-line interface for Quipu."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-application ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }

[project.scripts]
quipu = "quipu.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
# Hatch 默认会自动包含 package_data，如果需要显式包含：
# include = ["/src/quipu/cli/*.css"]
~~~~~

~~~~~act
write_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyquipu-test-utils"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common testing utilities for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Framework :: Pytest",
]
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "typer"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-bus = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

#### Acts 3: 更新根目录元包

~~~~~act
write_file
pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu"
version = "0.1.0"
description = "Quipu Development Monorepo - The complete toolkit."
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-application ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyquipu-cli ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
]

[project.optional-dependencies]
dev = [
    "pyquipu-application ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyquipu-cli ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
    "pyquipu-test-utils ~= 0.1.0",
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "ruff",
    "pre-commit"
]

[tool.uv]
workspace.members = ["packages/*"]

[tool.uv.sources]
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
pyquipu-cli = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-interfaces = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-test-utils = { workspace = true }

[tool.pytest.ini_options]
addopts = "-ra --cov=quipu --cov-report=term-missing"
testpaths = "tests packages"
pythonpath = [
  "packages/pyquipu-interfaces/src",
  "packages/pyquipu-engine/src",
  "packages/pyquipu-runtime/src",
  "packages/pyquipu-cli/src",
  "packages/pyquipu-common/src",
  "packages/pyquipu-application/src",
  "packages/pyquipu-test-utils/src",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
# 将根包指向 cli 或 runtime 之一作为元包入口，或者根据需要自定义
packages = ["packages/pyquipu-runtime/src/pyquipu"]

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.stitcher]
scan_paths = ["packages"]
~~~~~

### 下一步建议

1.  **验证构建**: 再次运行 `uv build packages/pyquipu-interfaces/`。你会发现输出变得非常简洁，且不再有任何警告。
2.  **清理旧产物**: 建议删除 `dist/` 目录和各个子包目录下的 `src/*.egg-info` 文件夹，因为 `hatchling` 不再需要它们。
3.  **创建提交**: 在验证所有包都能正确构建后，我们可以创建一个新的 `[COMMIT]` 计划来持久化这些重构。
