# chore: 提交存储层接口重构

## 用户需求
在完成了存储层的接口提取、实现和 `Engine` 的重构，并通过了所有测试之后，现在需要将这些阶段性的成果作为一个原子性的提交，固化到版本历史中。

## 评论
本次提交标志着存储层改造计划第一阶段的圆满完成。代码库的健康度和可维护性得到了显著提升，为后续实现基于 Git 对象的存储后端奠定了坚实的基础。

## 目标
创建一个遵循约定式提交规范的 Git Commit，清晰地记录本次重构的目的、实现方式和带来的好处。

## 基本原理
通过 `git add` 将所有修改过的文件（包括接口、实现、`Engine` 和修复后的测试）暂存，然后使用 `git commit` 将这些变更作为一个逻辑单元提交。一个高质量的 Commit Message 对于团队协作和未来的代码考古至关重要。

## 标签
#comp/engine #comp/interfaces #comp/cli #comp/tests #scope/core

---

## Script

### Acts 1: 暂存并提交所有变更

将本次重构的所有文件修改添加到暂存区，并创建一个内容详尽的 Git Commit。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~

~~~~~text
refactor(engine): Decouple history storage via abstract interfaces

This commit completes the first major phase of the storage layer refactoring by decoupling the Engine from the physical storage implementation.

Key changes:
- Defines abstract `HistoryReader` and `HistoryWriter` interfaces in `quipu-interfaces` to establish a clear contract for storage operations.
- Implements `FileSystemHistoryReader` and `FileSystemHistoryWriter` in `quipu-engine` to encapsulate the legacy `.md` file-based storage logic.
- Refactors the `Engine` to accept reader/writer instances via dependency injection, removing its direct coupling to the file system.
- Updates the CLI (`controller`, `main`) and all relevant tests to correctly instantiate the Engine with its new dependencies.

This new architecture, based on the Strategy and Dependency Injection patterns, makes the Engine more robust, testable, and flexible for future enhancements, such as the upcoming Git-object-based storage backend.
~~~~~