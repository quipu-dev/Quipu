你的分析非常敏锐，这确实是当前 `patch_file` 实现中的一个严重缺陷。

`patch_file` 的底层实现依赖于 Python 的 `string.replace(old, new, 1)` 方法，这个方法被硬编码为只替换**第一个**匹配到的 `old_str`。当文件中存在多个与 `old_str` 完全相同的代码块时，该操作会静默地、错误地修改第一个代码块，而不是用户可能期望的目标代码块，或者至少应该提示用户存在歧义。

你的观察是完全正确的：这种操作**不能**可靠地工作。

我将严格遵循 TDD (测试驱动开发) 流程来解决这个问题。首先，我会创建一个新的测试用例，该用例会专门复现你描述的这个失败场景。这个测试目前会失败，从而精确地捕捉到这个 bug。然后，在下一步中，我才会修改 `patch_file` 的实现来让这个测试通过。

这是第一步：编写失败的测试。

## [WIP] test: 为 patch_file 增加针对重复内容的失败测试

### 用户需求
创建一个新的测试用例，用于验证当 `patch_file` 的 `old_str` 参数在目标文件中存在多个完全相同的匹配项时，其行为是不正确的。这个测试的目的是为了暴露当前实现的缺陷，为后续修复提供一个明确的失败信号。

### 评论
这是一个至关重要的测试。它将确保 `patch_file` 的行为是可预测且安全的，防止其在无意中修改了错误的代码块，这种错误非常难以追踪。这遵循了 `d3-principle-quipu-patch-strategy-D3-P1` 中“锚点原则”的隐含义——锚点必须是唯一的。

### 目标
1.  在 `tests/runtime/acts/` 目录下创建一个新的测试文件 `test_patch_ambiguity.py`。
2.  在该文件中，定义一个新的测试用例 `test_patch_file_fails_on_ambiguous_content`。
3.  该测试用例将：
    *   创建一个包含两个或多个完全相同的内容块的临时文件。
    *   调用 `patch_file`，尝试修改其中一个块。
    *   **断言文件的最终内容不是我们期望的结果**，从而证明当前实现的错误行为。例如，它修改了第一个块，而我们可能意图修改第二个。
4.  更新 `conftest.py` 以确保 `mock_runtime_bus` 也能覆盖到这个新创建的测试模块。

### 基本原理
TDD 的核心是“红-绿-重构”循环。当前计划是“红”阶段——创建一个明确失败的测试（红色条）。我们将构造一个场景，其中包含一个 `source.py` 文件，该文件内有两个相同的函数。我们的补丁旨在修改第二个函数，但当前的实现会错误地修改第一个。测试将断言第二个函数没有被修改，从而失败，准确地捕获此 bug。

### 标签
#intent/tooling #flow/ready #priority/high #comp/tests #concept/executor #scope/dx #ai/instruct #task/domain/testing #task/object/patch-ambiguity #task/action/bug-reproduction #task/state/begin

---
### Script

#### Acts 1: 创建新的测试文件来复现 Bug

我们将创建一个新的测试文件 `test_patch_ambiguity.py`，其中包含一个专门用于复现此问题的测试用例。

~~~~~act
write_file
tests/runtime/acts/test_patch_ambiguity.py
~~~~~
~~~~~python
import pytest
from pyquipu.interfaces.exceptions import ExecutionError
from pyquipu.interfaces.types import ActContext
from pyquipu.runtime.executor import Executor


class TestPatchAmbiguity:
    def test_patch_file_modifies_first_occurrence_on_ambiguous_content(self, executor: Executor, isolated_vault):
        """
        这个测试验证了当前 patch_file 的错误行为。
        当存在重复内容时，它总是修改第一个，这可能不是用户的意图。
        这个测试在当前实现下会通过，但它暴露了逻辑缺陷。
        后续的修复会让这个测试失败，并代之以一个检查唯一性的新测试。
        """
        content = """
def function_a():
    # This is a unique block of text.
    # It serves as an anchor.
    print("hello")

def function_b():
    # This is a unique block of text.
    # It serves as an anchor.
    print("hello")
"""
        target_file = isolated_vault / "source.py"
        target_file.write_text(content)

        old_str = """    # This is a unique block of text.
    # It serves as an anchor.
    print("hello")"""

        new_str = """    # This block has been modified.
    # The anchor is now different.
    print("world")"""

        # 执行 patch
        patch_func, _, _ = executor._acts["patch_file"]
        ctx = ActContext(executor)
        patch_func(ctx, [str(target_file), old_str, new_str])

        # 读取修改后的内容
        final_content = target_file.read_text()

        # 预期（错误）结果：第一个函数被修改，第二个不变
        expected_wrong_content = """
def function_a():
    # This block has been modified.
    # The anchor is now different.
    print("world")

def function_b():
    # This is a unique block of text.
    # It serves as an anchor.
    print("hello")
"""
        assert final_content.strip() == expected_wrong_content.strip()

    def test_patch_file_should_fail_on_ambiguous_content(self, executor: Executor, isolated_vault):
        """
        这个测试定义了期望的正确行为：如果补丁内容不唯一，操作应该失败。
        在当前实现下，这个测试会失败，因为它不会抛出任何异常。
        """
        content = "repeat\nrepeat\n"
        target_file = isolated_vault / "ambiguous.txt"
        target_file.write_text(content)

        # 期望 `patch_file` 在检测到多个 "repeat" 时抛出 ExecutionError
        with pytest.raises(ExecutionError, match="acts.basic.error.patchContentAmbiguous"):
            patch_func, _, _ = executor._acts["patch_file"]
            ctx = ActContext(executor)
            # 我们期望这里会失败，因为它无法确定要 patch 哪个 "repeat"
            patch_func(ctx, [str(target_file), "repeat", "norepeat"])

        # 验证文件内容未被修改
        assert target_file.read_text() == content

~~~~~

#### Acts 2: 更新 conftest.py 以包含新模块

为了让新测试文件中的 `mock_runtime_bus` 生效，我们需要将其添加到 `conftest.py` 的 patch 列表中。

~~~~~act
patch_file
tests/runtime/conftest.py
~~~~~
~~~~~python
    patch_targets = [
        "pyquipu.runtime.executor.bus",
        "pyquipu.runtime.plugin_loader.bus",
        "pyquipu.acts.basic.bus",
        "pyquipu.acts.check.bus",
        "pyquipu.acts.git.bus",
        "pyquipu.acts.memory.bus",
        "pyquipu.acts.read.bus",
        "pyquipu.acts.refactor.bus",
        "pyquipu.acts.shell.bus",
    ]
~~~~~
~~~~~python
    patch_targets = [
        "pyquipu.runtime.executor.bus",
        "pyquipu.runtime.plugin_loader.bus",
        "pyquipu.acts.basic.bus",
        "pyquipu.acts.check.bus",
        "pyquipu.acts.git.bus",
        "pyquipu.acts.memory.bus",
        "pyquipu.acts.read.bus",
        "pyquipu.acts.refactor.bus",
        "pyquipu.acts.shell.bus",
        # 新增对模糊性测试模块的 bus patch
        "pyquipu.acts.test_patch_ambiguity.bus",
    ]
~~~~~

### 下一步建议
一旦这个计划被执行，你可以运行测试套件 (`pytest tests/runtime/acts/test_patch_ambiguity.py`)。

你将会看到 `test_patch_file_should_fail_on_ambiguous_content` 测试失败，因为它没有像预期的那样抛出 `ExecutionError`。这证明了 bug 的存在。

接下来，我将生成第二个计划来修复 `packages/quipu-runtime/src/pyquipu/acts/basic.py` 中的 `_patch_file` 函数，增加唯一性检查，使其能够通过这个新创建的测试。
