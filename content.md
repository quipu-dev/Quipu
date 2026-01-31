[简要回答]
好的，这是一个重要的工程化重构。引入 `L` 指针将消除“魔术字符串”，为 IDE 的自动补全和重构功能铺平道路，同时通过类型系统保证 ID 的有效性。

我将生成一个计划，通过编写并执行一个一次性的 Python 脚本，自动扫描 `packages/` 目录下的源代码，将所有符合模式的 `bus.xxx("string.id")` 调用替换为 `bus.xxx(L.string.id)`，并自动注入所需的导入语句。

## [WIP] refactor: 将 bus 消息 ID 迁移至 L 指针

### 用户需求
将 Quipu 代码库中所有使用字符串字面量表示的消息 ID（如 `bus.info("my.id")`）重构为使用 `needle.pointer.L` 对象（如 `bus.info(L.my.id)`），以提高代码的可维护性和类型安全性。

### 评论
这是一个典型的“大规模机械性重构”。使用脚本执行是最安全且高效的方法，可以避免人工操作的遗漏和错误。由于 `SemanticPointer` 已经实现了 `__eq__` 与字符串的兼容，这一改动不会破坏现有的基于字符串断言的测试用例。

### 目标
1.  创建一个重构脚本 `refactor_bus_ids.py`。
2.  执行脚本，批量修改 `packages/` 下的 Python 文件：
    *   将 `bus.method("dot.separated.id")` 替换为 `bus.method(L.dot.separated.id)`。
    *   在相关文件中添加 `from needle.pointer import L`。
3.  验证修改并在完成后删除脚本。

### 基本原理
*   **正则替换**: 目标模式非常清晰（`bus.<method>("id")`），且 ID 格式规范（无空格，点分隔），适合使用正则表达式进行精确匹配和替换。我们排除了 `bus.data`，因为它通常传输内容而非 ID。
*   **自动导入**: 脚本会检测文件是否发生了替换，并智能地在 `from quipu.common.bus import bus` 附近插入 `L` 的导入语句，保持代码风格整洁。
*   **兼容性**: 利用 `SemanticPointer` 与 `str` 的相等性兼容，确保重构平滑过渡，不强制要求同步修改所有测试断言。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #comp/runtime #task/domain/tech-debt #task/object/l-pointer #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 创建重构脚本
编写一个专门的 Python 脚本来执行查找和替换操作。

~~~~~act
write_file
refactor_bus_ids.py
~~~~~
~~~~~python
import os
import re

TARGET_DIR = "packages"

# 匹配模式：
# 1. 方法名: info, error, warning, success, fail, render_to_string
# 2. 引号: 单引号或双引号
# 3. ID: 必须包含至少一个点，且只包含字母、数字、下划线。这避免了匹配普通句子。
ID_PATTERN = re.compile(r'(bus\.(?:info|error|warning|success|fail|render_to_string))\s*\(\s*(["\'])([a-zA-Z0-9_]+\.[a-zA-Z0-9_\.]+)\2')

def process_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return # Skip binary or non-utf8 files

    new_content = content
    has_replacement = False

    def replace_match(match):
        nonlocal has_replacement
        has_replacement = True
        method = match.group(1)
        # quote = match.group(2) # unused
        id_str = match.group(3)
        return f"{method}(L.{id_str}"

    new_content = ID_PATTERN.sub(replace_match, content)

    if has_replacement:
        # Check if already imported
        if "from needle.pointer import L" not in new_content:
            # Strategy: Try to insert before 'from quipu.common.bus import bus'
            # This is the most common pattern in our codebase.
            if "from quipu.common.bus import bus" in new_content:
                new_content = new_content.replace(
                    "from quipu.common.bus import bus",
                    "from needle.pointer import L\nfrom quipu.common.bus import bus"
                )
            else:
                # Fallback: Insert after the last 'from ... import ...' block or at the top
                # Finding the first import to prepend is safer than appending to random location
                first_import = re.search(r'^(import|from)\s', new_content, re.MULTILINE)
                if first_import:
                    insert_pos = first_import.start()
                    new_content = new_content[:insert_pos] + "from needle.pointer import L\n" + new_content[insert_pos:]
                else:
                    # No imports? Prepend to file (unlikely for a file using bus)
                    new_content = "from needle.pointer import L\n" + new_content
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Refactored: {filepath}")

def main():
    print("Starting L-pointer refactoring...")
    for root, dirs, files in os.walk(TARGET_DIR):
        # Exclude common noise dirs
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "build", "dist", ".quipu"}]
        
        for name in files:
            if name.endswith(".py"):
                process_file(os.path.join(root, name))
    print("Refactoring complete.")

if __name__ == "__main__":
    main()
~~~~~

#### Acts 2: 执行重构
运行脚本应用变更。

~~~~~act
run_command
~~~~~
~~~~~
python3 refactor_bus_ids.py
~~~~~

#### Acts 3: 验证结果
随机检查一个核心文件，确认替换是否生效且格式正确。

~~~~~act
read_file
packages/pyquipu-runtime/src/quipu/acts/basic.py
~~~~~

#### Acts 4: 清理脚本
任务完成后删除一次性脚本。

~~~~~act
delete_file
refactor_bus_ids.py
~~~~~

### 下一步建议
如果重构脚本执行成功且代码通过验证，我们可以运行全套测试以确保没有引入语法错误或逻辑破坏。之后，我们将提交这些更改。
