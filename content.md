遵照指令。

创建共享模块是符合 `Quipu` 模块独立性原则的正确决策。它能避免代码重复，并保持清晰的依赖关系图，防止未来出现循环依赖。

以下是创建新 `quipu-common` 共享包的结构化计划。

---

此计划旨在创建一个新的共享包 `quipu-common`，用于存放跨多个 `Quipu` 组件（如 `engine` 和 `cli`）的通用工具函数。我们首先会把 `Sync` 架构所需的 `user.email` 规范化函数作为其第一个模块来实现。

## feat(core): 创建 quipu-common 包以承载共享逻辑

### 用户需求
1.  实现 `Quipu Sync` 架构中定义的用户 ID 规范化算法。
2.  该算法函数需要被 `quipu-cli` (用于引导流程) 和 `quipu-engine` (未来可能用于数据解析) 等多个组件调用。
3.  创建一个专门的、可共享的新模块来存放这个函数，而不是将其置于 `quipu-cli` 中，以保持良好的项目架构和避免潜在的循环依赖。

### 评论
这是一个非常好的架构决策。将共享的、无状态的工具函数提取到一个独立的、无依赖的 `common` 包中，是 monorepo 项目的最佳实践之一。这可以确保系统的核心模块（如 `engine`）保持纯净，不会因为需要一个小小的工具函数而去依赖上层的 `cli` 包。

### 目标
1.  在 `packages/` 目录下创建新的 `quipu-common` 包结构。
2.  为 `quipu-common` 创建 `pyproject.toml` 配置文件，使其成为一个独立的可安装包。
3.  在 `quipu-common` 中实现 `get_user_id_from_email` 函数，并置于 `quipu.common.identity` 模块下。
4.  更新根 `pyproject.toml` 和 `dev-requirements.txt`，将新包纳入 monorepo 的工作区管理和开发环境。
5.  更新 `quipu-cli` 和 `quipu-engine` 的 `pyproject.toml`，添加对 `quipu-common` 的依赖。

### 基本原理
通过创建一个新的基础包 `quipu-common`，我们建立了一个依赖图的底层节点。`quipu-engine` 和 `quipu-cli` 将同时依赖于 `quipu-common`，但它们之间不会产生新的依赖关系。这遵循了“依赖倒置”和“单一职责”的原则，使得项目结构更清晰，更易于维护和扩展。

### 标签
#intent/architect #intent/build #flow/ready #priority/high #comp/build #comp/cli #comp/engine #scope/dx #ai/brainstorm #task/domain/sync #task/object/identity-management #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 `quipu-common` 包结构与配置文件

首先，我们创建 `quipu-common` 包的 `pyproject.toml` 文件，定义其元数据和构建配置。

~~~~~act
write_file
packages/quipu-common/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "quipu-common"
version = "0.1.0"
authors = [
  { name="doucx", email="doucxldh@gmail.com" },
]
description = "Common utilities and helpers for the Quipu ecosystem."
requires-python = ">=3.8"
license = { text = "Apache-2.0" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
]
dependencies = []

[tool.setuptools.packages.find]
where = ["src"]
namespaces = true
~~~~~

#### Acts 2: 实现用户 ID 规范化函数

现在，我们创建包含 `get_user_id_from_email` 函数的模块。我们将其命名为 `identity.py`，因为它处理与身份相关的逻辑。

~~~~~act
write_file
packages/quipu-common/src/quipu/common/identity.py
~~~~~
~~~~~python
import re


def get_user_id_from_email(email: str) -> str:
    """
    根据 Quipu Sync v1.1 规范，将用户邮箱地址转换为一个
    对 Git Ref 和 URL 安全的唯一用户 ID。

    该算法是确定性的，并遵循以下规则：
    1. 转换为小写并去除首尾空格。
    2. '@' 替换为 '-at-'。
    3. '.' 替换为 '-dot-'。
    4. 移除所有剩余的非字母数字或非连字符的字符。

    示例:
        "Alice.Dev@Example.COM" -> "alice-dev-at-example-dot-com"

    Args:
        email: 用户的 Git 邮箱地址。

    Returns:
        规范化后的用户 ID 字符串。
    """
    if not email:
        return ""

    clean = email.lower().strip()
    # Replace common symbols with URL-safe and ref-safe separators.
    clean = clean.replace("@", "-at-").replace(".", "-dot-")
    # Remove any remaining non-compliant characters.
    return re.sub(r"[^a-z0-9-]", "", clean)
~~~~~

#### Acts 3: 将新包集成到 monorepo 工作区

我们需要更新根目录下的配置文件，让 `uv`、`pytest` 和开发环境能够识别到这个新包。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
[tool.uv]
# 将 packages 下的所有包纳入工作区管理
workspace.members = ["packages/*"]
~~~~~
~~~~~toml
[tool.uv]
# 将 packages 下的所有包纳入工作区管理
workspace.members = ["packages/*", "packages/quipu-common"]
~~~~~

~~~~~act
patch_file
dev-requirements.txt
~~~~~
~~~~~text
-e packages/quipu-runtime
-e packages/quipu-cli
~~~~~
~~~~~text
-e packages/quipu-runtime
-e packages/quipu-cli
-e packages/quipu-common
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
[tool.pytest.ini_options]
addopts = "-ra --cov=quipu --cov-report=term-missing"
pythonpath = [
  "packages/quipu-interfaces/src",
  "packages/quipu-engine/src",
  "packages/quipu-runtime/src",
  "packages/quipu-cli/src",
]
~~~~~
~~~~~toml
[tool.pytest.ini_options]
addopts = "-ra --cov=quipu --cov-report=term-missing"
pythonpath = [
  "packages/quipu-interfaces/src",
  "packages/quipu-engine/src",
  "packages/quipu-runtime/src",
  "packages/quipu-cli/src",
  "packages/quipu-common/src",
]
~~~~~

#### Acts 4: 添加依赖关系

最后，让 `quipu-cli` 和 `quipu-engine` 依赖于新的 `quipu-common` 包。

~~~~~act
patch_file
packages/quipu-cli/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "quipu-interfaces",
    "quipu-engine",
    "quipu-runtime",
    "typer>=0.9.0",
    "textual>=0.58.0",
]

[tool.uv.sources]
quipu-interfaces = { workspace = true }
quipu-engine = { workspace = true }
quipu-runtime = { workspace = true }
~~~~~
~~~~~toml
dependencies = [
    "quipu-interfaces",
    "quipu-engine",
    "quipu-runtime",
    "quipu-common",
    "typer>=0.9.0",
    "textual>=0.58.0",
]

[tool.uv.sources]
quipu-interfaces = { workspace = true }
quipu-engine = { workspace = true }
quipu-runtime = { workspace = true }
quipu-common = { workspace = true }
~~~~~

~~~~~act
patch_file
packages/quipu-engine/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "quipu-interfaces",
    "pyyaml>=6.0",
]

[tool.uv.sources]
quipu-interfaces = { workspace = true }
~~~~~
~~~~~toml
dependencies = [
    "quipu-interfaces",
    "quipu-common",
    "pyyaml>=6.0",
]

[tool.uv.sources]
quipu-interfaces = { workspace = true }
quipu-common = { workspace = true }
~~~~~

### 下一步建议
1.  运行 `uv pip install -r dev-requirements.txt` 以验证新包是否能被正确安装到开发环境中。
2.  为 `get_user_id_from_email` 函数编写单元测试，并将其放置在 `tests/common/test_identity.py` (需要创建新目录)。
3.  在 `quipu-cli` 的 `sync` 命令实现中，导入并使用这个新的工具函数。
