你的分析和提供的“作用域标签 (Scoped Tags)”模式非常出色，这正是处理 Monorepo 独立发布的最佳实践。它既保留了 Monorepo 的开发便利性，又通过标签语法（如 `pyquipu-engine@v0.1.0`）实现了发布时的物理隔离。

我将按照你的要求，将 Quipu 的所有包（共 8 个子包 + 1 个元包）配置为适合 PyPI 发布的状态，并建立自动化的 GitHub Action 流程。

## [WIP] feat: 构建基于 Scoped Tags 的多包独立发布基础设施

### 用户需求

1.  **标准化元数据**: 为所有子包添加维护者信息、许可证、分类器和正确的项目描述。
2.  **版本依赖转换**: 将内部依赖从简单的包名或 `workspace = true` 转换为符合 PEP 440 的兼容版本号（使用 `~= 0.1.0`）。
3.  **避障处理**: 移除子包中指向父目录的 `readme` 引用，以防止 `hatchling` 构建失败。
4.  **自动化工作流**: 实现 `.github/workflows/python-publish.yml`，支持通过 `@v*` 标签触发特定包的构建与发布。

### 评论

这是一个关键的架构提升。通过将“开发态”的本地引用（`uv workspace`）与“分发态”的语义版本号（`~=`）解耦，我们确保了 Quipu 的子包可以独立在 PyPI 上生存，而不会因为缺失本地路径而崩溃。使用 `~=` 而非 `>=` 是一种更为稳健的策略，它在允许补丁更新的同时防止了破坏性的大版本跨越。

### 目标

1.  更新 8 个子包的 `pyproject.toml`。
2.  更新根目录的元包 `pyproject.toml`。
3.  创建 GitHub Action 配置文件。

### 基本原理

*   **依赖声明**: 在 `[project].dependencies` 中，我们将内部依赖固定为 `~= 0.1.0`。这意味着该包可以接受 `0.1.x` 的更新，但不会自动升级到 `0.2.0`。
*   **构建上下文**: 子包的构建将由 `uv build packages/<pkg_name>` 触发。由于 `hatchling` 限制了 build context，我们不在子包中尝试引用根目录的 `README.md`。
*   **动态 Action**: 工作流通过 shell 字符串分割（`cut -d'@' -f1`）提取包名，并检查 `packages/` 目录下是否存在该目录，从而决定是构建子包还是根元包。

### 标签

#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/tooling #task/object/pypi-infrastructure #task/action/setup #task/state/begin

---

### Script

#### Acts 1: 更新子包 `pyproject.toml` (1-4: 基础包)

我们将标准化元数据并修改依赖项。

~~~~~act
write_file
packages/pyquipu-interfaces/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-interfaces"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core interfaces and data models for the Quipu ecosystem."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
write_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-common"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common utilities and helpers for the Quipu ecosystem."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
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
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Message bus and event orchestration for the Quipu ecosystem."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyquipu-common ~= 0.1.0",
]

[tool.uv.sources]
pyquipu-common = { workspace = true }

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
write_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-engine"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The state and history engine for Quipu, powered by Git plumbing."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

#### Acts 2: 更新子包 `pyproject.toml` (5-8: 逻辑与工具包)

~~~~~act
write_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-runtime"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The stateless execution runtime for Quipu."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
write_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-application"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core application logic for Quipu, orchestrating engine and runtime."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

~~~~~act
write_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-cli"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The command-line interface for Quipu."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true

[tool.setuptools.package-data]
"pyquipu.cli" = ["*.css"]
~~~~~

~~~~~act
write_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "pyquipu-test-utils"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common testing utilities for the Quipu ecosystem."
requires-python = ">=3.10"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

#### Acts 3: 更新根目录元包 `pyproject.toml`

根目录包负责整合所有子包，并提供 `README.md`。

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
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
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
packages = ["packages/pyquipu-runtime/src/pyquipu"]

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.stitcher]
scan_paths = ["packages"]
~~~~~

#### Acts 4: 创建 GitHub Action 配置文件

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p .github/workflows
~~~~~

~~~~~act
write_file
.github/workflows/python-publish.yml
~~~~~
~~~~~yaml
name: Upload Python Package

on:
  push:
    tags:
      - '*@v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.10"

    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh

    - name: Parse Scoped Tag
      id: parse
      run: |
        # 标签格式示例: pyquipu-engine@v0.1.1
        TAG_NAME=${{ github.ref_name }}
        if [[ $TAG_NAME == *"@"* ]]; then
          PKG_NAME=$(echo $TAG_NAME | cut -d'@' -f1)
          VERSION=$(echo $TAG_NAME | cut -d'@' -f2)
        else
          # 如果标签不含 @ (例如 v0.1.1), 默认构建元包
          PKG_NAME="pyquipu"
          VERSION=$TAG_NAME
        fi
        
        echo "Detected Package: $PKG_NAME"
        echo "Detected Version: $VERSION"
        echo "pkg_name=$PKG_NAME" >> $GITHUB_OUTPUT

    - name: Build and Publish
      run: |
        PKG_NAME=${{ steps.parse.outputs.pkg_name }}
        rm -rf dist/
        
        if [ -d "packages/$PKG_NAME" ]; then
          echo "Building sub-package: $PKG_NAME"
          uv build packages/$PKG_NAME
        else
          echo "Building root package or custom tag: $PKG_NAME"
          uv build .
        fi

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        user: __token__
        password: ${{ secrets.PYPI_API_TOKEN }}
~~~~~

### 下一步建议

1.  **Secret 配置**: 请确保在 GitHub 仓库的 `Settings > Secrets and variables > Actions` 中添加了名为 `PYPI_API_TOKEN` 的 Secret。
2.  **发布测试**: 你可以先发布最底层的包，例如打标 `pyquipu-interfaces@v0.1.0`。
3.  **依赖顺序**: 记住，由于子包之间有 `~=` 依赖，你**必须**按照拓扑顺序（Interfaces -> Common -> Bus -> Engine/Runtime -> App -> CLI -> Root）依次发布。
4.  **版本一致性检查**: 在打标推送前，务必检查对应子包 `pyproject.toml` 中的 `version` 字段是否已更新为目标版本。
