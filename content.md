你的分析完全正确。

这是一个典型的、由于 `patch_file` 操作的上下文锚点不精确而导致的 TOML 语法错误。

**根本原因：**
`hatchling` (构建后端) 在解析 `pyproject.toml` 时，严格遵守 PEP 621 规范。该规范定义了 `dependencies` 是 `[project]` 表的直接子键。

在我们之前的 `patch_file` 操作中，我们将新的元数据块注入到了 `license` 字段之后。这导致 `dependencies` 字段被错误地放置在了 `[project.urls]` 表的下方，但在下一个表（如 `[build-system]`）声明之前。根据 TOML 的解析规则，这使得 `dependencies` 被错误地解释为 `[project.urls]` 表的一部分。

`hatchling` 的验证器期望 `[project.urls]` 下的所有键值对的值都是字符串（URL），但它发现了一个名为 `dependencies` 的键，其值是一个数组（列表），因此抛出了 `TypeError`。

**次要问题：**
在审查中，我还发现所有包内的依赖版本约束仍然是 `~= 0.1.0`，而我们已经将所有子包的版本提升到了 `0.1.1`。这也是一个需要同步修复的潜在问题。

## [WIP] fix: 纠正 pyproject.toml 中 dependencies 的字段位置与版本约束

### 错误分析
`uv sync` 失败的根本原因是所有子包的 `pyproject.toml` 文件中，`dependencies` 列表被错误地放置在了 `[project.urls]` 表内，违反了 PEP 621 规范。

### 用户需求
修复 `pyproject.toml` 文件中的语法错误，使 `uv sync` 能够成功构建和安装开发环境。

### 评论
这是一个微妙但关键的结构性错误。修复此问题将确保我们的包元数据不仅对 PyPI 可见，而且对本地构建工具（如 `uv` 和 `hatchling`）也是完全合规的，从而保证了开发环境的稳定性和一致性。

### 目标
1.  在所有受影响的 `pyproject.toml` 文件中，将 `dependencies` 列表从 `[project.urls]` 表内移出，使其成为 `[project]` 表的直接子键。
2.  同步更新所有内部依赖的版本约束，从 `~= 0.1.0` 更新为 `~= 0.1.1`。

### 标签
#intent/fix #flow/ready #priority/critical
#comp/build #scope/dx
#ai/instruct
#task/domain/devops #task/object/pypi-metadata #task/action/bug-fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修复 `pyquipu-application`

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 2: 修复 `pyquipu-bus`

~~~~~act
patch_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = [
    "pyquipu-common ~= 0.1.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-common ~= 0.1.1",
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 3: 修复 `pyquipu-cli`

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
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
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 4: 修复 `pyquipu-common`

~~~~~act
patch_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = []
~~~~~
~~~~~toml.new
dependencies = []

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 5: 修复 `pyquipu-engine`

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "pyyaml >= 6.0",
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 6: 修复 `pyquipu-interfaces`

~~~~~act
patch_file
packages/pyquipu-interfaces/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = []
~~~~~
~~~~~toml.new
dependencies = []

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 7: 修复 `pyquipu-runtime`

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer >= 0.9.0"
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 8: 修复 `pyquipu-test-utils`

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
dependencies = [
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "typer"
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer"
]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

#### Acts 9: 修复门户包 `pyquipu`

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"

dependencies = [
    "pyquipu-application ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "pyquipu-cli ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-interfaces ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
]
~~~~~
~~~~~toml.new
[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~


### 下一步建议
1.  **执行计划**: 运行此计划以修正所有 `pyproject.toml` 文件。
2.  **验证**: 再次运行 `uv sync --extra dev`，这次应该会成功解析并安装所有包。
3.  **提交**: 在验证成功后，创建一个 `[COMMIT]` 计划来固化这次重要的结构性修复。
