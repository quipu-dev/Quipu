好的，既然代码层面的导入已经完成更新，我现在将同步更新所有子包的 `pyproject.toml` 文件，显式地将 `pyquipu-bus` 添加到它们的依赖项和 `uv` 工作区配置中。

## [WIP] refactor: 更新各子包的依赖关系以包含 pyquipu-bus

### 用户需求
更新 `pyquipu-application`、`pyquipu-cli`、`pyquipu-engine`、`pyquipu-runtime` 和 `pyquipu-test-utils` 的 `pyproject.toml` 文件，添加对新包 `pyquipu-bus` 的依赖。

### 评论
在 Monorepo 架构中，显式声明包之间的依赖关系是确保构建一致性和 `uv` 工作区正常工作的关键。虽然有些包可能通过传递依赖获得 `pyquipu-bus`，但由于它们直接导入了 `pyquipu.bus`，按照“显式胜于隐式”的原则，必须进行显式声明。

### 目标
1.  在所有直接使用总线的子包的 `dependencies` 中添加 `pyquipu-bus`。
2.  在这些子包的 `[tool.uv.sources]` 中配置 `pyquipu-bus = { workspace = true }`。

### 基本原理
- **显式依赖**：确保每个包在独立构建或测试时都能找到其需要的依赖项。
- **工作区一致性**：通过 `uv` 的工作区源配置，强制 Python 环境使用本地源码包。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #concept/parser #scope/api #ai/instruct #task/domain/testing #task/object/pyquipu-bus #task/action/dependency-update #task/state/continue

---

### Script

#### Acts 1: 更新 pyquipu-application

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
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
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "pyquipu-runtime",
    "pyquipu-common",
    "pyquipu-bus",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~

#### Acts 2: 更新 pyquipu-cli

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "pyquipu-runtime",
    "pyquipu-common",
    "pyquipu-application",
    "typer>=0.9.0",
    "textual>=0.58.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-application = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "pyquipu-runtime",
    "pyquipu-common",
    "pyquipu-application",
    "pyquipu-bus",
    "typer>=0.9.0",
    "textual>=0.58.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-runtime = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-application = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~

#### Acts 3: 更新 pyquipu-engine

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-common",
    "pyyaml>=6.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-common",
    "pyquipu-bus",
    "pyyaml>=6.0",
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~

#### Acts 4: 更新 pyquipu-runtime

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-common",
    "typer>=0.9.0"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-common",
    "pyquipu-bus",
    "typer>=0.9.0"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~

#### Acts 5: 更新 pyquipu-test-utils

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "typer"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces",
    "pyquipu-engine",
    "pyquipu-bus",
    "typer"
]

[tool.uv.sources]
pyquipu-interfaces = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-bus = { workspace = true }
~~~~~

### 下一步建议
- **执行环境同步**：请立即运行 `uv sync`。这将扫描所有更新过的 `pyproject.toml` 文件，重新计算依赖树并更新 `uv.lock`。
- **冒烟测试**：运行 `pytest` 或尝试执行 `quipu log`，确保 `pyquipu-bus` 能够正确加载 `pyquipu-common` 中的语言包资源并输出信息。
