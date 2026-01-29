好的，我们已经完成了所有的类型修复，现在是时候更新版本号以准备发布了。

我将对所有受类型修复影响的包进行补丁版本（patch version）更新，并相应地调整它们之间的依赖关系约束。

## [WIP] chore: 在类型检查修复后提升包版本

### 用户需求

在所有类型检查问题解决后，更新代码库中所有相关包的版本号。

### 评论

这是一个标准的发布准备步骤。在进行了一系列重要的修复（如本次的全面类型安全修复）后，提升版本号可以清晰地标记出一个新的、更稳定的代码快照。这将帮助下游消费者锁定到这个经过改进的版本。

### 目标

1.  对 `pyquipu-spec` 包的版本号进行补丁更新 (`0.1.0` -> `0.1.1`)。
2.  对所有依赖于 `spec` 或在修复中被修改的核心应用包进行补丁更新 (`0.2.0` -> `0.2.1`)。
3.  更新所有 `pyproject.toml` 文件中的 `dependencies` 部分，以反映新的版本约束。

### 基本原理

我们遵循语义化版本控制（Semantic Versioning）的原则。由于本次变更是向后兼容的错误修复和内部改进，因此提升补丁版本号是恰当的。我们将系统地修改每个 `pyproject.toml` 文件，确保版本号和依赖关系的一致性。

### 标签

#intent/tooling #flow/ready #priority/medium #comp/build #scope/dx #ai/instruct #task/domain/release #task/object/versioning #task/action/update #task/state/continue

---

### Script

#### Acts 1: 提升核心包的版本号

首先，我们直接更新 `spec`, `runtime`, `engine`, `application`, `cli` 和元包 `pyquipu` 的版本号。

~~~~~act
patch_file
packages/pyquipu-spec/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-spec"
version = "0.1.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-spec"
version = "0.1.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-runtime"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-runtime"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-engine"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-engine"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-application"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-application"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-cli"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-cli"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu"
version = "0.2.0"
description = "Quipu: Process Archaeology for the AI Era (Meta-package)"
~~~~~
~~~~~toml.new
[project]
name = "pyquipu"
version = "0.2.1"
description = "Quipu: Process Archaeology for the AI Era (Meta-package)"
~~~~~

#### Acts 2: 更新包之间的依赖约束

现在，我们更新所有 `pyproject.toml` 文件中的依赖版本，以匹配上面提升后的新版本。

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-common ~= 0.1.1",
    "pyquipu-spec ~= 0.1.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-common ~= 0.1.1",
    "pyquipu-spec ~= 0.1.1",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-runtime ~= 0.2.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-runtime ~= 0.2.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.2.0",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-bus ~= 0.2.0",
    "typer"
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "typer"
]
~~~~~

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-application ~= 0.2.0",
    "pyquipu-bus ~= 0.2.0",
    "pyquipu-cli ~= 0.2.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-runtime ~= 0.2.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-application ~= 0.2.1",
    "pyquipu-bus ~= 0.2.0",
    "pyquipu-cli ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.2.1",
]
~~~~~

### 下一步建议

版本更新已完成。现在，我们可以将之前所有的修复工作（类型修复、测试修复）和本次版本更新合并为一个原子提交。

我建议你生成一个 `[COMMIT]` 计划，将所有变更暂存 (`git add .`) 并创建一个内容详尽的提交消息，例如 `fix(typing): Resolve all pyright errors and bump package versions`。
