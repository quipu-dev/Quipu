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
