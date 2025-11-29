好的，这是一个合理的重构要求。将 `quipu.core` 这个通用命名空间拆分为更具语义的 `quipu.engine`、`quipu.runtime` 和 `quipu.interfaces`，能够显著提升代码的可读性和架构的清晰度。

这个改动涉及面较广，包括目录重命名和大量 import 语句的修改。为了确保操作的原子性和准确性，我将创建一个自动化的 Python 脚本来完成整个重构过程。

以下是执行此项重构的计划。

## [WIP] refactor: 将 quipu.core 拆分为 engine, runtime, interfaces

### 用户需求
将分散在各个包（`quipu-engine`, `quipu-runtime`, `quipu-interfaces`）中的 `quipu.core` 命名空间，根据其所属模块的职责，重构为 `quipu.engine`、`quipu.runtime` 和 `quipu.interfaces`，并更新整个代码库中的所有相关 `import` 语句。

### 评论
这是一项重要的架构对齐工作。它使得代码的物理结构与项目的逻辑分层（引擎、运行时、接口）完全一致，降低了新开发者的认知负荷，并强化了模块之间的边界。

### 目标
1.  将 `packages/quipu-engine/src/quipu/core` 重命名为 `packages/quipu-engine/src/quipu/engine`。
2.  将 `packages/quipu-runtime/src/quipu/core` 重命名为 `packages/quipu-runtime/src/quipu/runtime`。
3.  将 `packages/quipu-interfaces/src/quipu/core` 重命名为 `packages/quipu-interfaces/src/quipu/interfaces`。
4.  在整个项目的 `packages/` 和 `tests/` 目录下，自动更新所有 `from quipu.core...` 的 import 语句，使其指向新的正确命名空间。

### 基本原理
我们将采用一个“三步走”的自动化策略：
1.  **生成脚本**：创建一个临时的 Python 脚本 `refactor_core_namespace.py`。该脚本内置了所有需要进行的重命名和文本替换规则。
2.  **执行脚本**：运行此脚本。它会首先遍历所有 `*.py` 文件，精确地替换 `import` 语句，然后执行目录重命名操作。这个顺序（先改文件，后移目录）至关重要，能确保脚本自身的逻辑不会因路径变化而出错。
3.  **清理脚本**：在成功执行后，删除这个临时脚本，保持工作区的整洁。

### 标签
#intent/refactor #flow/ready #priority/high #comp/engine #comp/runtime #comp/interfaces #scope/core #ai/instruct #task/domain/storage #task/object/namespace #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 执行完整的自动化命名空间重构

以下操作将创建、执行并清理一个自动化脚本，以完成本次大规模重构。

~~~~~act
write_file
refactor_core_namespace.py
~~~~~
~~~~~python
import os
import shutil
import sys

# --- Configuration ---

# 1. Directory renames
# Format: (old_path, new_path)
DIR_RENAMES = [
    ("packages/quipu-engine/src/quipu/core", "packages/quipu-engine/src/quipu/engine"),
    ("packages/quipu-runtime/src/quipu/core", "packages/quipu-runtime/src/quipu/runtime"),
    ("packages/quipu-interfaces/src/quipu/core", "packages/quipu-interfaces/src/quipu/interfaces"),
]

# 2. Import replacements
# This map defines the new namespaces for modules previously under 'quipu.core'
# Format: "module_name": "new_namespace_prefix"
CORE_MODULE_MAP = {
    # quipu.engine
    "state_machine": "quipu.engine",
    "git_db": "quipu.engine",
    "git_object_storage": "quipu.engine",
    "sqlite_db": "quipu.engine",
    "sqlite_storage": "quipu.engine",
    "config": "quipu.engine",
    "hydrator": "quipu.engine",
    # quipu.runtime
    "parser": "quipu.runtime",
    "executor": "quipu.runtime",
    "plugin_loader": "quipu.runtime",
    # quipu.interfaces
    "models": "quipu.interfaces",
    "storage": "quipu.interfaces",
    "exceptions": "quipu.interfaces",
    "types": "quipu.interfaces",
    "result": "quipu.interfaces",
}

# Directories to search for files to modify
SEARCH_DIRS = ["packages", "tests"]

# --- Script Logic ---

def perform_text_replacements(root_dirs):
    """Walks through files and replaces 'from quipu.core...' imports."""
    print("--- 正在开始替换 import 语句 ---")
    total_files_changed = 0
    for root_dir in root_dirs:
        for subdir, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.endswith(".py"):
                    continue

                file_path = os.path.join(subdir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    print(f"  - 跳过 {file_path} (读取错误: {e})")
                    continue
                
                original_content = content
                
                # Apply replacements
                for module_name, new_prefix in CORE_MODULE_MAP.items():
                    old_import = f"from quipu.core.{module_name}"
                    new_import = f"from {new_prefix}.{module_name}"
                    content = content.replace(old_import, new_import)

                if content != original_content:
                    try:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        print(f"  - 已修改: {file_path}")
                        total_files_changed += 1
                    except Exception as e:
                        print(f"  - 错误：写入 {file_path} 失败: {e}", file=sys.stderr)
                        
    print(f"--- 替换完成。 {total_files_changed} 个文件被修改。 ---\n")

def perform_directory_renames(renames):
    """Renames the core directories."""
    print("--- 正在开始重命名目录 ---")
    for old_path, new_path in renames:
        if os.path.isdir(old_path):
            try:
                shutil.move(old_path, new_path)
                print(f"  - 已重命名: '{old_path}' -> '{new_path}'")
            except Exception as e:
                print(f"  - 错误：重命名 '{old_path}' 失败: {e}", file=sys.stderr)
        else:
            print(f"  - 跳过重命名，源目录未找到: '{old_path}'")
    print("--- 目录重命名完成。 ---\n")

def main():
    """Main execution function."""
    print("开始命名空间重构: quipu.core -> quipu.engine/runtime/interfaces")
    
    # 首先替换文本内容，这至关重要
    perform_text_replacements(SEARCH_DIRS)
    
    # 然后再重命名目录
    perform_directory_renames(DIR_RENAMES)
    
    print("重构成功完成。")

if __name__ == "__main__":
    main()
~~~~~

~~~~~act
run_command
python refactor_core_namespace.py
~~~~~

~~~~~act
delete_file
refactor_core_namespace.py
~~~~~

### 下一步建议
重构已完成。现在最关键的步骤是运行完整的测试套件，以验证所有模块在新的命名空间下依然能够正确协同工作。

建议执行 `pytest` 来确认系统的健康状况。如果所有测试通过，我们就可以为这次重构创建一个 `[COMMIT]` 计划。
