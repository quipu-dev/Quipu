# refactor(cli): Extract engine factory to unify initialization logic

## 用户需求
创建提交

## 评论
在完成了对 `Engine` 实例化逻辑的重构并修复了相关的测试后，现在将这些变更提交到版本控制中。

## 目标
将本次重构（包括创建 `factory.py` 模块、修改 `controller.py` 和 `main.py`、更新测试用例以及修复创世状态检测逻辑）作为一个原子提交进行记录。

## 标签
#comp/cli #refactor #scope/dx

---

## Script

### Acts 1: 暂存并提交变更

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~

~~~~~
refactor(cli): Extract engine factory to unify initialization logic

This commit centralizes the creation of the Engine instance by introducing a `factory.py` module.

Previously, both `main.py` and `controller.py` contained duplicate logic for detecting the storage format (Git Object vs. File System) and initializing the Engine. This violated the DRY principle and created a maintenance burden.

This refactoring:
- Creates `quipu.cli.factory.create_engine` as the single source of truth for Engine instantiation.
- Removes redundant code from `main.py` and `controller.py`.
- Ensures all CLI commands (`run`, `log`, `checkout`, etc.) share the exact same logic for storage detection and engine setup.
- Updates all relevant tests to use the new factory, simplifying test setup.

Additionally, this commit includes a fix for a boundary condition where the "genesis state" (empty repo, no history) was incorrectly identified as a "dirty" state, which was discovered during testing of this refactoring.
~~~~~