# commit-env-refactor 提交环境标准化与重构

## 目标
将所有关于环境标准化（移除根包定义、添加 `dev-requirements.txt`）以及之前的物理拆分重构（`quipu` 命名空间化）的变更提交到版本控制。

## 基本原理
这将固化目前的稳定状态，作为后续功能开发的安全基线。

## 标签
#chore #git

---

## Script

### Act 1: 添加所有变更

~~~~~act
git_add
~~~~~

~~~~~bash
.
~~~~~

### Act 2: 提交变更

~~~~~act
git_commit
~~~~~

~~~~~text
chore: standardize dev env and complete monorepo refactor

1. Standardized development environment:
   - Removed [project] definition from root pyproject.toml to prevent package conflicts.
   - Added dev-requirements.txt for reproducible editable installs.
   - Cleaned up build artifacts (*.egg-info).

2. Completed physical separation (Phase 2):
   - Moved all code into packages/ (interfaces, engine, runtime, cli).
   - Configured namespace packages for `quipu`.
   - Fixed import paths and dependencies.

3. Fixed testing infrastructure:
   - Removed pytest pythonpath injection to rely on installed environment.
   - Verified all tests passing with editable installs.
~~~~~