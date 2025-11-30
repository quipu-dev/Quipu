好的，这是一个合理的重构。统一项目的 Python 版本要求可以简化维护并利用新版本的语言特性。

我将生成一个计划，使用 `patch_file` 指令来精确地更新这五个文件。

## [WIP] refactor(deps): 将最低 Python 版本要求提升至 3.10

### 用户需求
用户要求将 `packages/` 目录下所有 `pyproject.toml` 文件中的 `requires-python = ">=3.8"` 更新为 `requires-python = ">=3.10"`。

### 评论
这是一个重要的维护性更新。将所有子包的 Python 版本要求与根 `pyproject.toml` (`>=3.10`) 对齐，可以确保整个项目依赖图的一致性，并允许开发者在所有模块中使用 Python 3.10 及以上版本的新特性，从而简化了开发和测试环境的管理。

### 目标
1.  修改 `quipu-interfaces` 的 `pyproject.toml`。
2.  修改 `quipu-engine` 的 `pyproject.toml`。
3.  修改 `quipu-common` 的 `pyproject.toml`。
4.  修改 `quipu-cli` 的 `pyproject.toml`。
5.  修改 `quipu-runtime` 的 `pyproject.toml`。

### 基本原理
我们将对每个目标文件使用一次 `patch_file` 操作。这是一个精确且安全的方法，因为它只会替换完全匹配的字符串 `requires-python = ">=3.8"`，确保不会意外修改其他配置。

### 标签
#intent/refine #flow/ready #priority/medium #comp/build #scope/dx #ai/instruct #task/domain/build #task/object/python-version #task/action/update #task/state/begin

---

### Script

#### Acts 1: 更新所有子包的 `pyproject.toml`

我们将依次对五个文件执行精确的字符串替换操作。

~~~~~act
patch_file
packages/quipu-interfaces/pyproject.toml
~~~~~
~~~~~text
requires-python = ">=3.8"
~~~~~
~~~~~text
requires-python = ">=3.10"
~~~~~

~~~~~act
patch_file
packages/quipu-engine/pyproject.toml
~~~~~
~~~~~text
requires-python = ">=3.8"
~~~~~
~~~~~text
requires-python = ">=3.10"
~~~~~

~~~~~act
patch_file
packages/quipu-common/pyproject.toml
~~~~~
~~~~~text
requires-python = ">=3.8"
~~~~~
~~~~~text
requires-python = ">=3.10"
~~~~~

~~~~~act
patch_file
packages/quipu-cli/pyproject.toml
~~~~~
~~~~~text
requires-python = ">=3.8"
~~~~~
~~~~~text
requires-python = ">=3.10"
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/pyproject.toml
~~~~~
~~~~~text
requires-python = ">=3.8"
~~~~~
~~~~~text
requires-python = ">=3.10"
~~~~~

### 下一步建议
- **运行测试**: 修改完成后，建议完整运行一次测试套件 (`pytest`)，以确保环境的变更没有引入任何回归问题。
- **创建提交**: 在测试通过后，创建一个 `[COMMIT]` 计划，将这些变更固化到版本历史中。
