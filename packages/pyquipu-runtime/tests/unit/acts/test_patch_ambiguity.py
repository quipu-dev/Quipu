import pytest
from quipu.runtime.executor import Executor
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext


class TestPatchAmbiguity:
    def test_patch_file_fails_on_ambiguous_multiline_content(self, executor: Executor, isolated_vault):
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

        new_str = """    # This block has been modified."""

        with pytest.raises(ExecutionError, match="找到 2 个匹配项"):
            patch_func, _, _ = executor._acts["patch_file"]
            ctx = ActContext(executor)
            patch_func(ctx, [str(target_file), old_str, new_str])

        # 验证文件未被修改
        assert target_file.read_text() == content

    def test_patch_file_should_fail_on_ambiguous_content(self, executor: Executor, isolated_vault):
        content = "repeat\nrepeat\n"
        target_file = isolated_vault / "ambiguous.txt"
        target_file.write_text(content)

        with pytest.raises(ExecutionError, match="找到 2 个匹配项"):
            patch_func, _, _ = executor._acts["patch_file"]
            ctx = ActContext(executor)
            patch_func(ctx, [str(target_file), "repeat", "norepeat"])

        # 验证文件内容未被修改
        assert target_file.read_text() == content
