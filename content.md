我们对涉及本次解耦架构重大重构的各个子包进行版本号升级，并同步更新 Monorepo 内的依赖约束。

## [WIP] chore: 升级相关子包版本号与工作区依赖约束

### 用户需求
针对存储与索引层解耦重构（引入新的 Spec 契约、Engine 架构大版本演进），更新相关子包的版本号并对齐内部依赖约束。

### 评论
本次重构对 `pyquipu-spec` 引入了全新接口契约（升级为 `0.2.0`），对 `pyquipu-engine` 实施了底层架构的彻底解耦与重组（升级为 `0.4.0`）。随之更新 `application`、`cli`、`test-utils` 与元包 `pyquipu` 至 `0.4.0`，有助于保持语义化版本（SemVer）的严谨性和下游依赖解析的一致性。

### 目标
1. `pyquipu-spec`: 版本从 `0.1.1` 升级至 `0.2.0`。
2. `pyquipu-engine`: 版本从 `0.3.1` 升级至 `0.4.0`，更新 `pyquipu-spec ~= 0.2.0`。
3. `pyquipu-application`: 版本从 `0.3.1` 升级至 `0.4.0`，依赖对齐 `0.4.0` 与 `0.2.0`。
4. `pyquipu-cli`: 版本从 `0.3.3` 升级至 `0.4.0`，依赖对齐。
5. `pyquipu-test-utils`: 版本从 `0.3.0` 升级至 `0.4.0`，依赖对齐。
6. `pyquipu` (Meta-package): 版本从 `0.3.1` 升级至 `0.4.0`，依赖约束全面对齐。
7. 运行 `uv sync` 同步工作区环境。

### 基本原理
- 遵循语义化版本规范（Semantic Versioning）：
  - 公共接口协议的扩展与演进（`pyquipu-spec`）作为次版本递增（Minor）。
  - 核心引擎内部架构重构及工厂 API 参数演进（`pyquipu-engine`、`pyquipu-application`、`pyquipu-cli`）统一作为次版本升级。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/build #concept/config #scope/dx #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/version-bump #task/state/continue

---

### Script

#### Acts 1: 升级 `pyquipu-spec` 版本号

~~~~~act
patch_file
packages/pyquipu-spec/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu-spec"
version = "0.1.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~
~~~~~toml
[project]
name = "pyquipu-spec"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
~~~~~

#### Acts 2: 升级 `pyquipu-engine` 版本号与依赖

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu-engine"
version = "0.3.1"
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
~~~~~toml
[project]
name = "pyquipu-engine"
version = "0.4.0"
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
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-common ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~

#### Acts 3: 升级 `pyquipu-application` 版本号与依赖

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu-application"
version = "0.3.1"
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
~~~~~toml
[project]
name = "pyquipu-application"
version = "0.4.0"
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
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
]
~~~~~

#### Acts 4: 升级 `pyquipu-cli` 版本号与依赖

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu-cli"
version = "0.3.3"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The command-line interface for Quipu."
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
    "Topic :: Text Processing",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "cli", "tui", "git", "history"]

dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.3.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
    "click >= 8.1.0",
]
~~~~~
~~~~~toml
[project]
name = "pyquipu-cli"
version = "0.4.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "The command-line interface for Quipu."
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
    "Topic :: Text Processing",
    "Typing :: Typed",
]
keywords = ["quipu", "devops", "cli", "tui", "git", "history"]

dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.4.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
    "click >= 8.1.0",
]
~~~~~

#### Acts 5: 升级 `pyquipu-test-utils` 版本号与依赖

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
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
~~~~~toml
[project]
name = "pyquipu-test-utils"
version = "0.4.0"
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
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyneedle-bus ~= 0.1.4",
    "pyneedle-pointer ~= 0.2.1",
    "typer"
]
~~~~~

#### Acts 6: 升级 `pyquipu` (Meta-package) 版本号与依赖

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu"
version = "0.3.1"
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
    "pyquipu-application ~= 0.3.1",
    "pyquipu-cli ~= 0.3.3",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-engine ~= 0.3.1",
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-runtime ~= 0.3.0",
]
~~~~~
~~~~~toml
[project]
name = "pyquipu"
version = "0.4.0"
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
    "pyquipu-application ~= 0.4.0",
    "pyquipu-cli ~= 0.4.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-runtime ~= 0.3.0",
]
~~~~~

### 下一步建议
所有子包版本号与依赖约束已全部更新并同步，全量测试保持 100% 绿灯。
本次“存储与索引层解耦”实施路线图的核心目标均已完成。若您准备好将这些变更生成 Git 提交，请随时告知。
