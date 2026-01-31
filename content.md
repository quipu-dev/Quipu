好的，保持一致性对测试代码的健壮性至关重要。将测试中的断言也同步到 `L` 指针，可以确保当我们在生产代码中利用 IDE 重构（如重命名某个消息 ID 路径）时，测试用例能自动同步，从而真正发挥重构的威力。

我将生成一个计划，通过脚本自动扫描测试目录并执行这一转换。

## [WIP] refactor: 迁移测试断言中的消息 ID 至 L 指针

### 用户需求
将测试目录中所有 `mock_bus` 的断言调用（如 `assert_called_with("string.id")`）重构为使用 `L` 指针（如 `assert_called_with(L.string.id)`）。

### 评论
在集成测试中，我们大量使用了 `mock_bus` 来验证业务意图。通过将这些断言也迁移到 `L` 指针，我们实现了生产代码与测试代码在语义标识符上的“强耦合”，这是一种健康的耦合，因为它确保了变更的原子性。

### 目标
1.  创建一个重构脚本 `refactor_test_assertions.py`。
2.  执行脚本，扫描 `packages/**/tests/` 和根目录 `tests/` 下的所有 Python 文件：
    *   将 `mock_bus.<method>.<assertion>("id")` 替换为 `mock_bus.<method>.<assertion>(L.id)`。
    *   在测试文件中注入 `from needle.pointer import L`。
3.  验证并删除脚本。

### 基本原理
*   **多级正则匹配**: 脚本会识别 `assert_called_with`、`assert_called_once_with` 和 `assert_any_call` 等常见的 Mock 断言方法。
*   **智能导入注入**: 脚本会尝试在 `import pytest` 或文件开头的导入块中插入 `L` 指针的导入语句。

### 标签
#intent/refine #intent/tooling #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/l-pointer #task/action/refactor-assertions #task/state/begin

---

### Script

#### Acts 1: 创建测试重构脚本

~~~~~act
write_file
refactor_test_assertions.py
~~~~~
~~~~~python
import os
import re

# 扫描 packages 下的测试和根目录下的测试
SCAN_PATHS = ["packages", "tests"]

# 匹配模式：
# 1. 基础部分: mock_bus.<method>
# 2. 断言方法: assert_called_with, assert_called_once_with, assert_any_call, called_with
# 3. ID 字符串
TEST_ASSERT_PATTERN = re.compile(
    r'(mock_bus\.[a-z_]+\.(?:assert_called_with|assert_called_once_with|assert_any_call|called_with))\s*\(\s*(["\'])([a-zA-Z0-9_]+\.[a-zA-Z0-9_\.]+)\2'
)

def process_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return

    new_content = content
    has_replacement = False

    def replace_match(match):
        nonlocal has_replacement
        has_replacement = True
        prefix = match.group(1)
        id_str = match.group(3)
        return f"{prefix}(L.{id_str}"

    new_content = TEST_ASSERT_PATTERN.sub(replace_match, content)

    if has_replacement:
        # 注入导入语句
        if "from needle.pointer import L" not in new_content:
            # 优先插入在 pytest 导入之后，或者在文件开头的 import 块
            if "import pytest" in new_content:
                new_content = new_content.replace(
                    "import pytest",
                    "import pytest\nfrom needle.pointer import L"
                )
            else:
                first_import = re.search(r'^(import|from)\s', new_content, re.MULTILINE)
                if first_import:
                    insert_pos = first_import.start()
                    new_content = new_content[:insert_pos] + "from needle.pointer import L\n" + new_content[insert_pos:]
                else:
                    new_content = "from needle.pointer import L\n" + new_content
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Refactored test: {filepath}")

def main():
    print("Starting L-pointer refactoring for tests...")
    for start_path in SCAN_PATHS:
        for root, dirs, files in os.walk(start_path):
            # 仅处理 Python 文件
            for name in files:
                if name.endswith(".py") and ("test_" in name or "conftest" in name):
                    process_file(os.path.join(root, name))
    print("Test refactoring complete.")

if __name__ == "__main__":
    main()
~~~~~

#### Acts 2: 执行测试重构

~~~~~act
run_command
~~~~~
~~~~~
python3 refactor_test_assertions.py
~~~~~

#### Acts 3: 验证结果
检查一个典型的集成测试文件，确认断言是否已更新。

~~~~~act
read_file
packages/pyquipu-cli/tests/integration/test_cache_commands.py
~~~~~

#### Acts 4: 清理脚本

~~~~~act
delete_file
refactor_test_assertions.py
~~~~~

### 下一步建议
一旦测试用例也完成了 `L` 指针的迁移，我建议运行 `pytest` 来验证全系统的一致性。如果一切正常，我们可以进行最终的 `[COMMIT]`。
