太好了。既然测试已经全部通过，这意味着我们已经成功越过了重构过程中最危险的“断连期”，系统已在新的 `spec` 架构基础上恢复了功能一致性。

我将生成一个 `[COMMIT]` 计划，将这次重大的架构演进作为一个完整的逻辑单元提交到 Git 历史中。

## [COMMIT] refactor: 将核心接口与协议迁移至新的 pyquipu-spec 包

### 用户需求
将目前完成的所有架构重构工作（创建 `spec` 包、迁移依赖、修正导入路径及修复模型缺陷）提交到 Git 仓库。

### 评论
这是 Quipu 项目的一个重要里程碑。通过这次重构，我们不仅优化了物理包结构，更在逻辑上确立了以 `Protocol` 为核心的契约驱动设计。这将极大地提升系统未来的可测试性和模块替换的灵活性。

### 目标
1.  将所有变更添加到 Git 暂存区。
2.  创建一个内容详尽的提交记录，说明重构的动机、范围和结果。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules-D3-P2` 约束，本计划仅包含 Git 操作，不包含任何文件内容的修改。我们将把新创建的 `pyquipu-spec` 目录、修改后的各包配置文件以及所有修正了导入路径的源码文件一并提交。

### 标签
#intent/architect #flow/ready #priority/high 
#comp/interfaces #comp/build #scope/core 
#ai/instruct 
#task/domain/architecture #task/object/spec-package #task/action/dependency-migration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交架构重构成果

我们将变更加入暂存区并创建提交。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: migrate core interfaces to pyquipu-spec and embrace Protocols

Major architectural shift from a loose 'interfaces' collection to a formal 'spec' package acting as the system's constitution.

Key Changes:
- Created 'pyquipu-spec' package with a structured layout (models, protocols, exceptions).
- Replaced 'abc.ABC' with 'typing.Protocol' for all core interfaces (HistoryReader, HistoryWriter, etc.), enabling structural typing and decoupling.
- Introduced 'ExecutorProtocol' in the spec to break the circular conceptual dependency between runtime and interfaces.
- Migrated all internal packages to depend on 'pyquipu-spec' instead of 'pyquipu-interfaces'.
- Performed a codebase-wide refactoring of import paths.
- Restored the missing 'content' field in 'QuipuNode' model to fix regression in memory-backend tests.
- Deleted the obsolete 'pyquipu-interfaces' package.

This transition establishes a Single Source of Truth for system contracts and significantly improves mockability and architectural integrity.
~~~~~

### 下一步建议
1.  **收拢分布式的 Protocol**: 建议下一步将 `pyquipu-bus` 中的 `Renderer` 和 `pyquipu-runtime` 中的 `PlanParser` 协议也提取到 `quipu.spec.protocols` 中，彻底确立 `spec` 的中心地位。
2.  **清理遗留的 ABC 导入**: 检查并移除各实现类（如 `GitObjectHistoryReader`）中已不再需要的 `ABC` 继承声明。
3.  **完善规范文档**: 可以在 `pyquipu-spec` 中增加更详细的 docstring 和架构文档。
