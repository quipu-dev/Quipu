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