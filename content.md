# diagnose-import 诊断导入路径问题

## 目标
运行一个独立的 Python 脚本，打印 `quipu` 包的路径列表 (`__path__`) 和 `sys.path`，以确定为什么 Python 无法找到 `quipu.acts`。这将揭示是命名空间合并失败，还是路径指向错误。

## 基本原理
Python 的命名空间包机制允许 `quipu` 映射到多个物理目录。通过打印 `quipu.__path__`，我们可以看到 Python 到底加载了哪些目录。如果列表中缺少 `.../packages/quipu-runtime/src/quipu`，则说明该包未正确安装或被屏蔽。

## 标签
#debug #import #namespace

---

## Script

### Act 1: 创建并运行诊断脚本

写入一个临时脚本并执行，输出关键的调试信息。

~~~~~act
write_file
~~~~~

~~~~~path
debug_quipu.py
~~~~~

~~~~~python
import sys
import os
from pathlib import Path

print("=== Debugging Quipu Import ===")

# 1. Check physical directory
runtime_acts = Path("packages/quipu-runtime/src/quipu/acts")
print(f"\n[Filesystem Check]")
if runtime_acts.exists():
    print(f"  Found: {runtime_acts}")
    print(f"  Is Dir: {runtime_acts.is_dir()}")
    init_file = runtime_acts / "__init__.py"
    print(f"  Has __init__: {init_file.exists()}")
else:
    print(f"  MISSING: {runtime_acts}")

# 2. Check sys.path (first 5 entries are usually enough)
print(f"\n[Sys.path Top 5]")
for p in sys.path[:5]:
    print(f"  {p}")

# 3. Attempt Import
print(f"\n[Import Check]")
try:
    import quipu
    print(f"  Successfully imported 'quipu'")
    print(f"  quipu.__path__: {list(quipu.__path__)}")
    
    try:
        import quipu.acts
        print(f"  Successfully imported 'quipu.acts'")
        print(f"  quipu.acts.__file__: {quipu.acts.__file__}")
    except ImportError as e:
        print(f"  FAILED to import 'quipu.acts': {e}")
        # Check if runtime path is in quipu.__path__
        cwd = os.getcwd()
        expected_part = "packages/quipu-runtime/src/quipu"
        found = False
        for p in quipu.__path__:
            if expected_part in p or (cwd in p and "quipu-runtime" in p):
                found = True
                print(f"  -> Found runtime path in namespace: {p}")
        if not found:
            print(f"  -> CRITICAL: Runtime path NOT found in quipu namespace paths!")

except ImportError as e:
    print(f"  FAILED to import 'quipu': {e}")

print("==============================")
~~~~~

### Act 2: 运行诊断脚本

~~~~~act
run_command
~~~~~

~~~~~bash
python3 debug_quipu.py
~~~~~