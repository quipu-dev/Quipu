好的，所有的代码修改和硬编码清理已经完成。现在我们执行最后的提交，将“统一与收敛”以及“常量迁移”这两个阶段的成果固化到仓库中。

## [COMMIT] refactor(spec): unify protocols and centralize global constants

### 用户需求
提交架构重构路线图“阶段四：统一与收敛”和“阶段五：清理与验证”的所有代码变更。

### 评论
这次提交标志着整个“从 Interfaces 到 Spec”重构任务的圆满完成。我们不仅消除了一切硬编码的魔术哈希，还成功地将全系统的核心契约（渲染器、解析器、引擎）集中到了 `pyquipu-spec` 包中，确立了系统的“宪法”层。这极大地增强了 Quipu 架构的严密性和未来的可扩展性。

### 目标
1.  将受影响的所有协议定义文件、核心逻辑文件以及更新后的测试文件添加到 Git 暂存区。
2.  创建一个详尽的提交记录，说明本次重构对全系统一致性的贡献。

### 基本原理
通过将变更作为单一逻辑单元提交，我们确保了仓库历史的清晰性，并宣告了新重构架构的正式启用。

### 标签
#intent/refine #flow/ready #priority/medium #comp/spec #comp/bus #comp/cli #comp/runtime #comp/engine #comp/application #task/domain/architecture #task/object/unification #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交统一协议与常量的变更

我们将汇总所有修改过的文件并执行提交。

~~~~~act
git_add
packages/pyquipu-spec/src/quipu/spec/protocols/messaging.py
packages/pyquipu-spec/src/quipu/spec/protocols/parser.py
packages/pyquipu-spec/src/quipu/spec/protocols/engine.py
packages/pyquipu-bus/src/quipu/bus/bus.py
packages/pyquipu-cli/src/quipu/cli/rendering.py
packages/pyquipu-cli/src/quipu/cli/commands/workspace.py
packages/pyquipu-runtime/src/quipu/runtime/parser.py
packages/pyquipu-application/src/quipu/application/controller.py
packages/pyquipu-engine/src/quipu/engine/state_machine.py
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
packages/pyquipu-test-utils/src/quipu/test_utils/helpers.py
packages/pyquipu-engine/tests/integration/test_branching.py
packages/pyquipu-engine/tests/integration/test_git_writer.py
packages/pyquipu-engine/tests/integration/test_git_reader.py
packages/pyquipu-engine/tests/integration/test_engine.py
packages/pyquipu-engine/tests/integration/sqlite/test_reader.py
packages/pyquipu-engine/tests/integration/sqlite/test_writer.py
packages/pyquipu-engine/tests/integration/sqlite/test_writer_idempotency.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(spec): unify protocols and centralize global constants

This commit completes the 'Interfaces to Spec' architectural roadmap (Phases 4 & 5):

1. Protocols Unification:
   - Centralized 'Renderer' protocol in 'quipu.spec.protocols.messaging', used by bus and cli.
   - Centralized 'PlanParser' protocol in 'quipu.spec.protocols.parser', updated runtime implementation.
   - Introduced 'QuipuEngine' protocol in 'quipu.spec.protocols.engine' to fully decouple application and cli layers from implementation details.

2. Constants Centralization:
   - Migrated all 'EMPTY_TREE_HASH' literal occurrences to 'quipu.spec.constants'.
   - Cleaned up all hardcoded git tree hashes across core logic and the entire integration test suite.

3. Code Health:
   - Fixed type annotations in 'parser.py' and 'controller.py'.
   - Simplified local constant definitions in storage backends.

The 'pyquipu-spec' package is now the Single Source of Truth (SSoT) for all core definitions in the Quipu ecosystem.
~~~~~

### 下一步建议
恭喜！我们已经完成了这一宏大的重构任务。

目前的系统底座已经非常稳固。对于未来的开发，我建议：
- **强化开发者文档**: 基于 `spec` 包编写新的开发者指南，说明如何实现新的 `Act` 插件或新的存储后端。
- **性能评估**: 既然存储后端已经解耦，我们可以开始探索针对超大规模仓库的索引优化策略，而无需担心破坏上层逻辑。
