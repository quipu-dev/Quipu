好的，我看到了测试结果。这是一个典型的、在大型重构后出现的“连锁反应”错误。

你的分析是正确的，这是一个同类错误。根本原因在于我们上一步的重构。

### 错误分析
我们在 `tests/conftest.py` 中集中化了 `engine_instance` 和 `git_workspace` 等 **Engine 层**的 Fixture。然而，我们忽略了 `tests/runtime/` 目录下的测试有其自身的依赖：一个 `Executor` 实例。

在重构之前，这个 `executor` fixture 很可能是在一个（现在不存在的）`tests/runtime/conftest.py` 中定义的。我们的重构无意中删除了或未迁移这个对 `runtime` 测试至关重要的 Fixture，导致所有依赖它的测试在启动时都因“找不到 Fixture”而失败。

### 用户需求
修复 `tests/runtime/` 目录下的所有测试，为它们提供所需的 `executor` fixture。

### 评论
这是一个非常好的教训，它强调了在重构时需要考虑所有子系统的特定依赖。修复这个问题将使我们的测试结构更加健壮和清晰：`tests/` 下有全局 Fixture，而 `tests/runtime/` 下有其作用域内专用的 Fixture。

### 目标
1.  创建一个新的 `tests/runtime/conftest.py` 文件。
2.  在该文件中定义一个名为 `executor` 的 Fixture。
3.  这个 Fixture 将为每个测试函数提供一个独立的 `Executor` 实例，该实例在一个临时的、隔离的文件目录 (`tmp_path`) 中运行，以确保测试之间不会相互干扰。
4.  同时定义一个 `isolated_vault` fixture，使其返回 executor 的工作目录，以兼容现有测试。

### 基本原理
Pytest 会在测试文件的目录及其父目录中查找 `conftest.py` 文件来加载 Fixture。通过在 `tests/runtime/` 目录下创建一个 `conftest.py` 并定义 `executor`，我们就能让该目录及其子目录下的所有测试文件自动发现并使用这个 Fixture，从而解决依赖缺失的问题。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/fixtures #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 为 `runtime` 测试创建专用的 `conftest.py`

我们将创建 `tests/runtime/conftest.py` 文件，并定义 `executor` 和 `isolated_vault` 这两个缺失的 Fixture。

~~~~~act
write_file
tests/runtime/conftest.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from quipu.runtime.executor import Executor
from quipu.acts.basic import register as register_basic_acts


@pytest.fixture
def executor(tmp_path: Path) -> Executor:
    """
    为运行时测试提供一个隔离的 Executor 实例。
    - 在独立的临时目录 (tmp_path) 中运行。
    - 自动注册基础 acts。
    - 默认以非交互模式 (yolo=True) 运行。
    """
    # yolo=True 避免在测试中出现交互式提示，这对于非 CLI 测试至关重要
    instance = Executor(root_dir=tmp_path, yolo=True)
    # 自动注册基础指令，因为大多数测试都依赖它们
    register_basic_acts(instance)
    return instance


@pytest.fixture
def isolated_vault(executor: Executor) -> Path:
    """
    提供 Executor 实例的根工作目录。
    这是一个便利性的 fixture，用于需要直接操作文件系统的测试。
    """
    return executor.root_dir
~~~~~

### 下一步建议
这个计划应该能修复所有 `fixture 'executor' not found` 的错误。请执行此计划，然后再次运行完整的测试套件 (`pytest`)，确认问题已解决并且没有引入新的错误。
