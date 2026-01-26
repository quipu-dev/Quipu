你的诊断完全正确。

PyPI 的搜索引擎和包浏览器严重依赖于 `pyproject.toml` 中丰富的元数据，尤其是 `classifiers`, `keywords`, 和 `[project.urls]`。我们当前的包因为缺少这些关键信息，所以尽管成功上传，但在 PyPI 上的“可发现性”几乎为零。

我将参照 `Needle` 项目的最佳实践，为 Quipu 生态下的所有子包注入一套标准化、高质量的元数据，并提升版本号以触发 CD 管道，将这些改进发布出去。

## [WIP] feat: 为所有包注入标准元数据并提升版本号

### 用户需求
1.  **注入元数据**: 为 `packages/` 目录下的所有 `pyproject.toml` 文件添加 `classifiers`, `keywords`, 和 `[project.urls]` 字段，以提升在 PyPI 上的搜索可见性和专业性。
2.  **更新 URL**: 确保所有 `[project.urls]` 中的链接指向 `https://github.com/quipu-dev/Quipu`。
3.  **提升版本**: 将所有核心子包的版本号从 `0.1.0` 提升至 `0.1.1`，并将门户包 `pyquipu` 的版本号提升至 `0.1.2`，以触发新版本的发布。

### 评论
这是一次至关重要的“润色” (`#intent/tune`) 操作，它将 Quipu 从一个“可以工作”的项目，提升为一个“专业发布”的库。标准化的元数据是确保用户能够发现、信任并使用我们软件的基石。

### 目标
1.  为所有子包和门户包的 `pyproject.toml` 文件补全 PyPI 元数据。
2.  将所有子包的版本更新到 `0.1.1`。
3.  将门户包 `pyquipu` 的版本更新到 `0.1.2`。

### 基本原理
通过 `patch_file` 指令，我们将向每个 `pyproject.toml` 的 `[project]` 部分注入一个标准化的元数据块。版本号的提升会产生版本势能差，自动触发我们已经部署的幂等性 CD 管道，从而将包含新元数据的包发布到 PyPI。

### 标签
#intent/tune #flow/ready #priority/high
#comp/build #scope/dx #scope/ux
#ai/instruct
#task/domain/devops #task/object/pypi-metadata #task/action/standardization
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 为 `pyquipu-application` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-application"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-application"
version = "0.1.1"
~~~~~

#### Acts 2: 为 `pyquipu-bus` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-bus/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-bus"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-bus"
version = "0.1.1"
~~~~~

#### Acts 3: 为 `pyquipu-cli` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-cli"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-cli"
version = "0.1.1"
~~~~~

#### Acts 4: 为 `pyquipu-common` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-common/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-common"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-common"
version = "0.1.1"
~~~~~

#### Acts 5: 为 `pyquipu-engine` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-engine"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-engine"
version = "0.1.1"
~~~~~

#### Acts 6: 为 `pyquipu-interfaces` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-interfaces/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Typing :: Typed",
]
~~~~~
~~~~~toml.new
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
keywords = ["quipu", "devops", "interfaces", "models", "api"]

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-interfaces/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-interfaces"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-interfaces"
version = "0.1.1"
~~~~~

#### Acts 7: 为 `pyquipu-runtime` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-runtime"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-runtime"
version = "0.1.1"
~~~~~

#### Acts 8: 为 `pyquipu-test-utils` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
classifiers = [
    "Programming Language :: Python :: 3",
    "Operating System :: OS Independent",
    "Framework :: Pytest",
]
~~~~~
~~~~~toml.new
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

[project.urls]
Homepage = "https://github.com/quipu-dev/Quipu"
Repository = "https://github.com/quipu-dev/Quipu"
"Bug Tracker" = "https://github.com/quipu-dev/Quipu/issues"
~~~~~

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu-test-utils"
version = "0.1.0"
~~~~~
~~~~~toml.new
name = "pyquipu-test-utils"
version = "0.1.1"
~~~~~

#### Acts 9: 为门户包 `pyquipu` 注入元数据并提升版本

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
license = "Apache-2.0"
dependencies = [
    "pyquipu-application ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyquipu-cli ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
]

[build-system]
~~~~~
~~~~~toml.new
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

[build-system]
~~~~~

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml.old
name = "pyquipu"
version = "0.1.1"
~~~~~
~~~~~toml.new
name = "pyquipu"
version = "0.1.2"
~~~~~

### 下一步建议
- **执行计划**: 运行此计划以更新所有 `pyproject.toml` 文件。
- **创建提交**: 在计划成功执行后，创建一个 `[COMMIT]` 计划，将这些重要的元数据改进固化到 Git 历史中。合并到 `main` 后，CD 管道将自动发布这些更专业、更易于发现的新版本。
