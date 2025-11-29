Excellent. With the tests passing, we can now confidently commit this major architectural refactoring. The file tree confirms that the directories have been correctly renamed and the new structure is in place.

I will now generate the final `[COMMIT]` plan to persist these changes into the version history.

## [COMMIT] refactor(core): split core namespace into engine, runtime, and interfaces

### 用户需求
将 `quipu.core` 命名空间重构的成功结果（包括目录重命名和 `import` 语句更新）作为一个原子性的、有良好文档记录的变更提交到 Git 仓库。

### 评论
这是一个里程碑式的重构。它消除了 `quipu.core` 这一模糊的命名空间，使得项目的物理代码结构与逻辑架构（Engine/Runtime/Interfaces）完全对齐。这将极大地提升代码库的可读性、可维护性，并为未来的功能开发奠定更坚实的基础。

### 目标
1.  将所有因重构而产生的变更（文件修改和目录移动）添加到 Git 暂存区。
2.  创建一个清晰、详尽的 Git Commit，永久记录此次架构演进。

### 基本原理
通过创建一个单一、完整的提交，我们确保了 Git 历史的干净和可追溯性。任何开发者在未来 `git blame` 或 `git log` 时，都能立刻理解这个大规模变更的意图和范围，而不是看到一系列零散的、无上下文的修改。

### 标签
#intent/refactor #flow/ready #priority/high #comp/engine #comp/runtime #comp/interfaces #comp/tests #scope/core #ai/instruct #task/domain/storage #task/object/namespace #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交命名空间重构

我们将暂存所有变更，并使用一条遵循 Conventional Commits 规范的提交信息来创建提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(core): split core namespace into engine, runtime, and interfaces

This major refactoring aligns the physical code structure with the project's logical architecture by splitting the ambiguous `quipu.core` namespace.

Previously, modules from different logical layers (engine, runtime, interfaces) shared the same `quipu.core` namespace, obscuring their boundaries and responsibilities.

This change introduces three distinct and semantically meaningful namespaces:
- `quipu.engine`: For state management, history, and Git plumbing.
- `quipu.runtime`: For stateless parsing and execution of plans.
- `quipu.interfaces`: for shared data models, exceptions, and abstract base classes.

The refactoring was performed atomically via an automated script, which:
1. Renamed the `core` directory within `quipu-engine`, `quipu-runtime`, and `quipu-interfaces` packages to `engine`, `runtime`, and `interfaces` respectively.
2. Updated all `from quipu.core...` import statements across the entire codebase (`packages/` and `tests/`) to point to their new locations.

This greatly improves code clarity, maintainability, and enforces stronger module separation.
~~~~~

### 下一步建议
本次核心架构重构已经完成并提交。现在，我们可以：
1.  继续开发新的功能，享受更清晰的架构带来的便利。
2.  审视 `pyproject.toml` 中的依赖关系，看是否有可以进一步解耦和优化的空间。
