# fix-namespace 修复命名空间包冲突

## 目标
删除所有子包顶层 `quipu` 目录下的 `__init__.py` 文件。

## 基本原理
Quipu 采用 Monorepo 结构，`quipu` 是一个命名空间包 (Namespace Package)。如果有任何一个子包在 `src/quipu/` 目录下包含了 `__init__.py`，Python 就会将其视为普通包，从而导致其他子包（如 `quipu.acts` 所在的 `quipu-runtime`）无法被正确发现和导入。这通常是 `ModuleNotFoundError: No module named 'quipu.acts'` 的根源。

## 标签
#fix #python #packaging

---

## Script

### Act 1: 移除 Interface 包的顶层 init

~~~~~act
delete_file packages/quipu-interfaces/src/quipu/__init__.py
~~~~~

### Act 2: 移除 Engine 包的顶层 init

~~~~~act
delete_file packages/quipu-engine/src/quipu/__init__.py
~~~~~

### Act 3: 移除 Runtime 包的顶层 init

~~~~~act
delete_file packages/quipu-runtime/src/quipu/__init__.py
~~~~~

### Act 4: 移除 CLI 包的顶层 init

~~~~~act
delete_file packages/quipu-cli/src/quipu/__init__.py
~~~~~

### Act 5: 确保 Acts 包有 init

虽然我们要删除顶层的 init，但 `acts` 是一个具体的子模块，它必须拥有 `__init__.py` 才能被导入。这里重新写入它以防万一（或确认其内容正确）。

~~~~~act
write_file
~~~~~

~~~~~path
packages/quipu-runtime/src/quipu/acts/__init__.py
~~~~~

~~~~~python
from . import basic, check, git, memory, read, refactor, shell

def register_core_acts(executor):
    """注册所有核心 Acts"""
    basic.register(executor)
    check.register(executor)
    git.register(executor)
    memory.register(executor)
    read.register(executor)
    refactor.register(executor)
    shell.register(executor)
~~~~~