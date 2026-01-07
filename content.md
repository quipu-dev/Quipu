好的，测试通过证明了重构后的“测试基础设施层”是稳健且正确的。通过将 Fixture 集中到 `test-utils`，我们成功地为 Monorepo 建立了一个标准化的测试契约。

我将生成一个 `[COMMIT]` 计划，将这些变更持久化到版本库中。

## [COMMIT] refactor(tests): 将通用 Fixture 集致化到 test-utils

### 用户需求
整理测试套件，消除 `conftest.py` 之间的逻辑冗余和潜在冲突，提高测试套件的可维护性。

### 评论
这是一次关键的工程质量提升。它不仅解决了当前的维护痛点，还为未来将测试用例物理移动到各个 package 内部铺平了道路，因为基础设施现在已经是跨包共享的了。

### 目标
1.  提交新创建的 `pyquipu.test_utils.fixtures` 模块。
2.  提交所有重构后的 `conftest.py` 文件。
3.  标记“测试套件优化”宏观任务的完成。

### 基本原理
遵循 **SSoT (唯一真理来源)** 原则。通过将共享的夹具逻辑（如 Engine 初始化、Bus Mocking、工作区搭建）移入专门的工具包，我们确保了所有测试环境的一致性。这种架构使得单个包的测试可以独立运行，同时也支持在根目录下进行全局集成测试。

### 标签
#intent/refine #intent/tooling #flow/ready #priority/medium 
#comp/tests #comp/build #concept/ui #scope/dx 
#ai/instruct 
#task/domain/testing #task/object/test-infrastructure #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有涉及测试基础设施重构的文件添加到暂存区并提交。

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(tests): centralize common fixtures into test-utils

Migrated shared fixtures (engine_instance, git_workspace, mocks, sync_env, etc.) from distributed conftest.py files to a centralized module in pyquipu-test-utils.

This refactoring:
1. Eliminates logic duplication across the test suite.
2. Resolves potential fixture shadowing and loading order conflicts.
3. Decouples test environmental setup from the tests themselves.
4. Prepares the architecture for moving test cases into individual package directories.

Each conftest.py now acts as a clean consumer of the standardized testing infrastructure provided by the internal test-utils package.
~~~~~

### 下一步建议

- **物理迁移**: 既然基础设施已经就绪，下一步可以考虑正式执行最初的设想：将 `tests/<pkg_name>/` 目录下的测试用例物理移动到 `packages/<pkg_name>/tests/` 下。
- **并行化测试**: 随着测试套件的解耦，可以考虑配置 `pytest-xdist` 来并行运行测试，进一步提升开发效率。
