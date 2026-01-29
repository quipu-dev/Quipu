好的，代码修改已经完成并经过了初步核对。现在我们按照 Quipu 协议的要求，将这些重构变更作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] refactor(spec): protocolize storage and runtime interfaces

### 用户需求
提交架构重构路线图中“阶段三：协议化改革”的所有代码变更。

### 评论
这次重构通过引入 `typing.Protocol` 实现了结构化类型，显著降低了 `spec`、`engine` 和 `runtime` 包之间的耦合度。它确立了清晰的行为契约，消除了循环依赖的隐患，并为后续的自动化测试和多后端扩展奠定了坚实的基础。

### 目标
1.  将阶段三涉及的所有修改过的文件添加到 Git 暂存区。
2.  创建一个符合 Conventional Commits 规范的提交记录，详细说明本次重构的内容。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules` 约束，将文件修改与 Git 提交操作在不同的计划中执行，确保变更在被永久记录前有被审查和验证的机会。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/spec #comp/engine #comp/runtime #task/domain/architecture #task/object/type-system #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 提交协议化重构的变更

我们将把受影响的 spec、engine 和 runtime 文件添加到暂存区，并创建一个详细的提交。

~~~~~act
git_add
packages/pyquipu-spec/src/quipu/spec/protocols/storage.py
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
packages/pyquipu-spec/src/quipu/spec/protocols/runtime.py
packages/pyquipu-spec/src/quipu/spec/models/execution.py
packages/pyquipu-runtime/src/quipu/runtime/executor.py
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(spec): protocolize storage and runtime interfaces

In accordance with Phase 3 of the Architecture Refactoring Roadmap:

1. Converted 'HistoryReader' and 'HistoryWriter' from ABCs to Protocols in 'quipu.spec.protocols.storage'.
2. Removed explicit inheritance from storage implementation classes in 'pyquipu-engine', embracing structural typing.
3. Introduced 'ExecutorProtocol' in 'quipu.spec.protocols.runtime' to decouple 'ActContext' from the concrete 'Executor' implementation.
4. Consolidated runtime type definitions by moving the 'Statement' TypedDict to the runtime protocols module.
5. Updated imports across 'spec', 'engine', and 'runtime' to align with the new structural architecture.

This change eliminates conceptual circular dependencies between the runtime and interfaces, and provides a more flexible foundation for testing and future extensions.
~~~~~

### 下一步建议
- **运行测试**: 在继续之前，强烈建议在本地环境中运行 `pytest` 以确保所有组件在新的协议体系下协作正常。
- **阶段四启动**: 确认提交后，我们可以开始执行“阶段四：统一与收敛”，提取 `Renderer` 和 `PlanParser` 协议至 `spec` 包。
