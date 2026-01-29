## [WIP] chore(build): Bump package versions to 0.2.0 for spec refactor

### 用户需求

在完成“从 Interfaces 到 Spec”的重大架构重构后，根据语义化版本规范，更新所有受影响包的版本号及其内部依赖。

### 评论

这是一个至关重要的维护操作。通过将版本号从 `0.1.x` 提升到 `0.2.0`，我们清晰地向所有依赖方传达了这是一个包含破坏性变更的新版本生态。这避免了依赖地狱，并确保了 Monorepo 内部依赖图的健康与一致性。

### 目标

1.  将所有受影响的核心 `pyquipu-*` 包的版本号统一提升至 `0.2.0`。
2.  更新每个 `pyproject.toml` 文件中的 `dependencies` 部分，使其依赖约束与新的 `0.2.0` 版本生态对齐。
3.  确保 `pyquipu-spec` 及其依赖方正确设置为 `0.1.0`。

### 基本原理

遵循 SemVer 规范，在 `0.y.z` 阶段，次版本号的增加用于标记破坏性的 API 变更。本次重构完全删除了 `pyquipu-interfaces` 包并重塑了核心类型定义，属于典型的破坏性变更，因此需要将版本从 `0.1.x` 升级到 `0.2.0`。

### 标签

#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/build-system #task/object/versioning #task/action/update #task/state/continue

---

### Script

#### Acts 1: 更新 `pyquipu-application`

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-application"
version = "0.1.1"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-application"
version = "0.2.0"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-runtime ~= 0.2.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
]
~~~~~

#### Acts 2: 更新 `pyquipu-bus`

~~~~~act
patch_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-bus"
version = "0.1.1"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Message bus and event orchestration for the Quipu ecosystem."
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
keywords = ["quipu", "devops", "bus", "event"]

dependencies = [
    "pyquipu-common ~= 0.1.1",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-bus"
version = "0.2.0"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
description = "Message bus and event orchestration for the Quipu ecosystem."
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
keywords = ["quipu", "devops", "bus", "event"]

dependencies = [
    "pyquipu-common ~= 0.1.1",
    "pyquipu-spec ~= 0.1.0",
]
~~~~~

#### Acts 3: 更新 `pyquipu-cli`

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-cli"
version = "0.1.1"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-runtime ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-application ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-cli"
version = "0.2.0"
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

#### Acts 4: 更新 `pyquipu-engine`

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-engine"
version = "0.1.1"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "pyyaml >= 6.0",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-engine"
version = "0.2.0"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "pyyaml >= 6.0",
]
~~~~~

#### Acts 5: 更新 `pyquipu-runtime`

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-runtime"
version = "0.1.1"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-runtime"
version = "0.2.0"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-bus ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~

#### Acts 6: 更新 `pyquipu-test-utils`

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu-test-utils"
version = "0.1.1"
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "typer"
]
~~~~~
~~~~~toml.new
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
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-bus ~= 0.2.0",
    "typer"
]
~~~~~

#### Acts 7: 更新 `pyquipu` 元包

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu"
version = "0.1.2"
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
    "pyquipu-application ~= 0.1.1",
    "pyquipu-bus ~= 0.1.1",
    "pyquipu-cli ~= 0.1.1",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.1.1",
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.1",
]
~~~~~
~~~~~toml.new
[project]
name = "pyquipu"
version = "0.2.0"
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
    "pyquipu-application ~= 0.2.0",
    "pyquipu-bus ~= 0.2.0",
    "pyquipu-cli ~= 0.2.0",
    "pyquipu-common ~= 0.1.1",
    "pyquipu-engine ~= 0.2.0",
    "pyquipu-spec ~= 0.1.0",
    "pyquipu-runtime ~= 0.2.0",
]
~~~~~

### 下一步建议

所有版本号和依赖项都已更新。这是本次宏观任务的最后一次文件修改。

请确认此计划，我将生成最终的 `[COMMIT]` 计划来结束整个重构工作。
