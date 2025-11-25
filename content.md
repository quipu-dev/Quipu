# chore: 为接口层解耦创建 Git 提交

## 目标
将已完成的“阶段 1.1：建立接口层隔离”的重构工作固化为一个 Git 提交。

## 基本原理
本次重构成功地将核心接口文件 (`types`, `models`, `exceptions`, `result`) 从业务逻辑中分离出来，并通过 `intf_` 前缀进行了标识。所有相关引用也已更新，并且测试套件已全部通过。现在需要创建一个清晰的 Git 提交来记录这一里程碑，以便于后续的代码审查和历史追溯。

## 标签
 #git #chore

---

## Script

### Act 1: 暂存所有变更

将所有修改过的文件和重命名的文件添加到 Git 暂存区。

~~~~~act
git_add .
~~~~~

### Act 2: 提交变更

创建一条符合规范的 Git 提交信息，总结本次重构的内容。

~~~~~act
git_commit
~~~~~

~~~~~
refactor(core): Isolate interface layer as `intf_*`

This commit completes Phase 1.1 of the Quipu refactoring plan.

- Renames shared data structure and definition files within the `core/` directory to have an `intf_` prefix (`intf_types`, `intf_models`, etc.).
- Updates all import statements across the entire codebase to reflect these changes.
- Fixes a related import error in `tests/test_plugins.py` that was discovered during testing.

This logical separation is a prerequisite for the physical separation of the `quipu-interfaces` package in Phase 2. The codebase is now prepared for the next stage of decoupling.
~~~~~