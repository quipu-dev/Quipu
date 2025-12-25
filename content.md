你提出了一个非常关键的开发者体验 (DX) 优化点。在 Monorepo 结构中，如果不能通过一条命令建立起完整的开发环境，将会极大地增加新贡献者的上手难度和日常开发的复杂度。

你提供的 `Cascade` 项目是一个完美的参考。它采用了标准的“伞形包 (Umbrella Package)”模式：

1.  **根 `pyproject.toml` 作为入口**: 项目根目录的 `pyproject.toml` 定义了一个名为 `cascade` 的元包。
2.  **`[dev]` 可选依赖**: 这个元包通过 `[project.optional-dependencies]` 定义了一个 `dev` 组。
3.  **依赖聚合**: `dev` 组不仅包含了 `pytest`, `ruff` 等通用开发工具，还**显式地包含了工作区内的所有其他本地包** (如 `"cascade-application"`, `"cascade-provider-ipfs"`)。

当你运行 `uv pip install -e .[dev]` 时，`uv` 会：
1.  安装 `cascade` 这个元包。
2.  解析 `[dev]` 组，安装所有列出的开发工具。
3.  因为 `dev` 组也依赖于工作区内的其他包，`uv` 会自动找到这些本地包，解析它们各自的 `dependencies`，并将它们全部以可编辑模式安装。

这正是我们 `pyquipu` 项目所需要的。我们将完全复制这个模式。

## [WIP] chore: 聚合开发依赖到根 pyproject.toml

### 用户需求
修改项目配置，使得开发者可以通过在项目根目录运行 `uv pip install -e .[dev]` 一条命令，安装所有 `packages/*` 子包及其依赖，以及所有用于测试和代码检查的开发工具。

### 评论
这是一个至关重要的 DX 改进，它将开发环境的搭建过程从一系列零散的步骤（可能包括手动安装各个包、安装 `dev-requirements.txt`）简化为一条标准的、确定性的命令。这使得环境搭建更快、更可靠，并为自动化 CI 流程奠定了坚实的基础。

### 目标
1.  修改根目录的 `pyproject.toml` 文件，使其成为一个聚合所有子包的“伞形包”。
2.  在根 `pyproject.toml` 中定义一个 `[project.optional-dependencies]`，其中包含一个 `dev` 组。
3.  将 `dev-requirements.txt` 中的所有内容迁移到 `dev` 组中。
4.  将所有本地 `packages/*` 也作为依赖项添加到 `dev` 组中。
5.  删除现在已经冗余的 `dev-requirements.txt` 文件。

### 基本原理
我们将遵循 `Cascade` 项目的最佳实践。通过在根 `pyproject.toml` 中定义一个全面的 `[dev]` 依赖组，我们为 `uv` 提供了一个单一的、权威的入口点来理解整个项目的开发依赖图。这利用了 `uv` 对 monorepo 工作区的原生支持，实现了依赖的集中管理和一键安装。

### 标签
#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/build #task/object/dependency-management #task/action/centralize #task/state/begin

---
### Script

#### Acts 1: 改造根 pyproject.toml

我们将修改根 `pyproject.toml`，重命名项目，并添加包含所有开发依赖的 `[dev]` 组。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-monorepo"
version = "0.1.0"
description = "Quipu Development Monorepo"
requires-python = ">=3.10"
dependencies = []

[tool.uv]
# 将 packages 下的所有包纳入工作区管理
workspace.members = ["packages/*", "packages/quipu-common"]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu"
version = "0.1.0"
description = "Quipu Development Monorepo"
requires-python = ">=3.10"
dependencies = [
    "pyquipu-application",
    "pyquipu-cli",
    "pyquipu-common",
    "pyquipu-engine",
    "pyquipu-interfaces",
    "pyquipu-runtime",
]

[project.optional-dependencies]
dev = [
    # Local workspace packages
    "pyquipu-application",
    "pyquipu-cli",
    "pyquipu-common",
    "pyquipu-engine",
    "pyquipu-interfaces",
    "pyquipu-runtime",
    # Dev tools
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "ruff",
    "pre-commit"
]

[tool.uv]
# 将 packages 下的所有包纳入工作区管理
workspace.members = ["packages/*"]

[tool.uv.sources]
pyquipu-application = { workspace = true }
pyquipu-cli = { workspace = true }
pyquipu-common = { workspace = true }
pyquipu-engine = { workspace = true }
pyquipu-interfaces = { workspace = true }
pyquipu-runtime = { workspace = true }
~~~~~

#### Acts 2: 删除冗余的依赖文件

`dev-requirements.txt` 的职责已经被 `pyproject.toml` 完全接管，我们将其删除以避免混淆。

~~~~~act
delete_file
dev-requirements.txt
~~~~~

### 下一步建议
请执行此计划。
完成后，建议在一个**干净的虚拟环境**中运行 `uv pip install -e ".[dev]"`。然后可以通过 `uv pip list` 来验证是否所有的 `pyquipu-*` 包和开发工具（如 `pytest`）都已成功安装。
