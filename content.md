好的，测试通过意味着我们已经成功完成了 **pyquipu** 测试架构的重大迁徙。现在，测试用例与其验证的代码在物理结构上达成了一致，同时通过根目录的 `conftest.py` 确保了全局基础设施的共享。

我将生成一个 `[COMMIT]` 计划，清理临时脚本并提交这一阶段性的重构成果。

## [COMMIT] refactor(tests): 完成测试套件向 package 内部的迁移

### 用户需求
完成将所有特定包的测试从根目录 `tests/` 移动到 `packages/*/tests/` 的任务，并解决由此引发的命名空间冲突和 Fixture 作用域问题。

### 评论
这次重构极大地提升了 Monorepo 的模块化水平。现在，每个包都是一个自包含的单元，拥有自己的源码和多层级测试（单元/集成）。根目录的 `conftest.py` 作为一个桥梁，为整个项目提供标准化的测试环境，完美平衡了灵活性与统一性。

### 目标
1.  删除不再需要的迁移辅助脚本 `migrate_tests.py`。
2.  提交所有重构后的测试目录结构。
3.  提交已提升至根目录的全局 `conftest.py`。
4.  提交更新后的 `pyproject.toml` 配置。

### 基本原理
我们通过以下三个核心动作完成了迁移：
- **物理迁移**: 使用脚本精确地将文件归位到 `unit` 或 `integration` 目录。
- **消除冲突**: 移除子包测试目录下的 `__init__.py`，使 Pytest 能够生成唯一的测试模块名，避免了 Monorepo 中常见的导入路径冲突。
- **作用域恢复**: 将全局 `conftest.py` 提升至项目根目录，利用 Pytest 的递归查找机制，为所有处于子目录深处的测试重新赋予了访问全局 Fixture（如 `runner`, `engine_instance`）的能力。

### 标签
#intent/refine #intent/tooling #flow/ready #priority/medium 
#comp/tests #comp/build #concept/executor #scope/dx 
#ai/instruct 
#task/domain/testing #task/object/test-layout #task/action/migration #task/state/end #task/status/completed

---

### Script

#### Acts 1: 清理并提交

删除临时工具脚本，并将所有变更提交到版本库。

~~~~~act
delete_file
migrate_tests.py
~~~~~

~~~~~act
git_add
conftest.py
pyproject.toml
packages/quipu-application/tests/
packages/quipu-cli/tests/
packages/quipu-engine/tests/
packages/quipu-runtime/tests/
tests/
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(tests): complete migration of tests to package directories

This commit finalizes the reorganization of the test suite:
1. Relocated all package-specific tests from root 'tests/' to 'packages/*/tests/{unit,integration}/'.
2. Removed '__init__.py' files from sub-package test directories to resolve Python namespace conflicts and ImportPathMismatchErrors.
3. Elevated 'tests/conftest.py' to the project root './conftest.py' to ensure global fixture availability for all distributed tests.
4. Updated 'pyproject.toml' to scan both root and package test paths and include all source directories in pythonpath.
5. Cleaned up the old 'tests/' sub-structure, retaining only cross-package integration tests.

This layout improves code locality and supports independent package verification while maintaining shared testing infrastructure.
~~~~~

### 下一步建议

- **覆盖率审查**: 运行 `uv run pytest --cov` 检查是否有任何测试在迁移过程中被意外遗漏（虽然概率较低，但作为重构后的最后一道门禁是必要的）。
- **并行化配置**: 由于现在测试已经分布在不同的包中，可以考虑在 CI 流程中针对不同的包并行运行测试，以显著缩短反馈周期。
