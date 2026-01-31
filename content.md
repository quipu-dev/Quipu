好的，现在 L 指针已经在代码中全面使用，我们需要更新项目的依赖项和版本号来反映这一变化。

我将生成一个计划，通过一系列 `patch_file` 操作来更新所有 `pyproject.toml` 文件，添加对 `pyneedle-pointer` 的依赖，并相应地提升所有受影响包的版本。

## [WIP] chore: 添加 pyneedle-pointer 依赖并更新版本

### 用户需求
在所有 `pyproject.toml` 文件中添加对 `pyneedle-pointer` 的依赖，并更新所有 Quipu 包的版本号以反映此次重构。

### 评论
这是一个关键的依赖管理步骤。通过在 `pyquipu-common` 中引入 `pyneedle-pointer`，我们正式确立了 `L` 指针作为项目的一等公民。版本号的统一提升（从 `0.2.x` 到 `0.3.0`）清晰地向用户表明这是一个包含新特性和重要内部改进的版本。

### 目标
1.  在 `pyquipu-common` 和 `pyquipu-test-utils` 中添加对 `pyneedle-pointer` 的依赖。
2.  将 `pyquipu-common` 的版本提升至 `0.2.0`。
3.  将所有其他受影响的 Quipu 包（`engine`, `runtime`, `application`, `cli`, `test-utils`, `pyquipu`）的版本提升至 `0.3.0`。
4.  在所有包中同步更新对其他 Quipu 包的版本约束。

### 基本原理
我们将对每个 `pyproject.toml` 文件进行精确的 `patch` 操作。首先修改最底层的 `pyquipu-common`，然后逐层向上修改依赖它的包，确保整个依赖图的一致性。这个过程是机械的，但对于保持 monorepo 的健康至关重要。

### 标签
#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/dependency-management #task/object/versions #task/action/update #task/state/begin

---

### Script

#### Acts 1: 更新 `pyquipu-common`
这是最基础的包，我们在这里引入 `pyneedle-pointer`。

~~~~~act
patch_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-common"
version = "0.1.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common utilities and helpers for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "common", "utils"]

dependencies = [
    "pyneedle-bus ~= 0.1.4",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-common"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common utilities and helpers for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "common", "utils"]

dependencies = [
    "pyneedle-bus ~= 0.1.4",
    "pyneedle-pointer ~= 0.2.1",
]
~~~~~

#### Acts 2: 更新依赖 `common` 的核心包

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-engine"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The state and history engine for Quipu, powered by Git plumbing."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Version Control",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "engine", "state", "git"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-engine"
version = "0.3.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The state and history engine for Quipu, powered by Git plumbing."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Version Control",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "engine", "state", "git"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-runtime"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The stateless execution runtime for Quipu."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "runtime", "executor", "automation"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-runtime"
version = "0.3.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The stateless execution runtime for Quipu."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "runtime", "executor", "automation"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~

#### Acts 3: 更新上层应用包

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-application"
version = "0.2.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core application logic for Quipu, orchestrating engine and runtime."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Build Tools",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "history", "git", "engine"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-application"
version = "0.3.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Core application logic for Quipu, orchestrating engine and runtime."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Build Tools",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "history", "git", "engine"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-runtime ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.2.1",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.3.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-cli"
version = "0.2.1"
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-cli"
version = "0.3.0"
~~~~~

#### Acts 4: 更新测试工具包
测试工具包也需要 `L` 指针。

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-test-utils"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common testing utilities for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Framework :: Pytest",
    "Topic :: Software Development :: Testing",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "testing", "pytest"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyneedle-bus ~= 0.1.4",
    "typer"
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-test-utils"
version = "0.3.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Common testing utilities for the Quipu ecosystem."
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Framework :: Pytest",
    "Topic :: Software Development :: Testing",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "testing", "pytest"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyneedle-bus ~= 0.1.4",
    "pyneedle-pointer ~= 0.2.1",
    "typer"
]
~~~~~

#### Acts 5: 更新元包和根配置

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu"
version = "0.2.1"
description = "Quipu: Process Archaeology for the AI Era (Meta-package)"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Environment :: Console",
    "Topic :: Software Development :: Version Control",
    "Topic :: Software Development :: Build Tools",
]
keywords = ["quipu", "devops", "cli", "tui", "git", "history", "automation", "ai"]

dependencies = [
    "pyquipu-application ~= 0.2.1",
    "pyquipu-cli ~= 0.2.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.1",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.2.1",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu"
version = "0.3.0"
description = "Quipu: Process Archaeology for the AI Era (Meta-package)"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Environment :: Console",
    "Topic :: Software Development :: Version Control",
    "Topic :: Software Development :: Build Tools",
]
keywords = ["quipu", "devops", "cli", "tui", "git", "history", "automation", "ai"]

dependencies = [
    "pyquipu-application ~= 0.3.0",
    "pyquipu-cli ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.3.0",
]
~~~~~

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[project.optional-dependencies]
dev = [
    "pyquipu",
    "pyquipu-test-utils",
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "ruff",
    "pre-commit"
]
~~~~~
~~~~~toml.new
[project.optional-dependencies]
dev = [
    "pyquipu",
    "pyquipu-test-utils",
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "ruff",
    "pre-commit",
    "pyneedle-pointer",
]
~~~~~

### 下一步建议
依赖项和版本号已更新。现在是时候将这些变更作为一个完整的单元提交了。如果你同意，我将生成 `[COMMIT]` 计划。
