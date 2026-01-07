好的，第一阶段的代码修改已经准备就绪。现在我们将这些变更作为一个完整的逻辑单元进行提交。

这包括了新包 `pyquipu-test-utils` 的初始化、`helpers.py` 的迁移、根配置的更新以及所有测试文件中导入路径的修复。

## [COMMIT] chore(test): initialize pyquipu-test-utils and migrate helpers

### 用户需求
将之前的架构变更（创建测试工具包并迁移辅助函数）提交到 Git 仓库。

### 评论
将这些基础性的变更单独提交是一个良好的实践。它在执行大规模的测试目录重构之前，先确立了一个稳定的、具有一致导入路径的基准状态。

### 目标
1.  将所有新创建的文件和修改后的文件添加到 Git 暂存区。
2.  创建一个详尽的提交消息，记录本次重构的意图和影响。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules` 协议，我们将 Git 提交操作独立于文件系统修改操作。通过 `git_add` 包含新包目录、根 `pyproject.toml` 以及受 `sed` 影响的 `tests/` 目录，确保提交的完整性。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/tests #comp/build #scope/dx #ai/instruct #task/domain/testing #task/object/test-suite-structure #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 提交测试架构基础变更

我们将新包、修改后的根配置文件以及所有修复了导入路径的测试文件添加到暂存区并提交。

~~~~~act
git_add
packages/quipu-test-utils
pyproject.toml
tests
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
chore(test): initialize pyquipu-test-utils and migrate helpers

This commit establishes the foundation for the test suite reorganization by:
1. Creating a new internal package 'pyquipu-test-utils' to house common testing infrastructure.
2. Migrating 'tests/helpers.py' to 'pyquipu-test-utils' to elevate it to a first-class, shareable component.
3. Integrating 'pyquipu-test-utils' into the workspace and dev dependencies in the root 'pyproject.toml'.
4. Bulk-updating all import paths in the 'tests/' directory using sed, transitioning from relative/internal imports to the new package-based import: 'from pyquipu.test_utils.helpers'.

This move decouples test logic from utility scripts and prepares the codebase for distributing tests into their respective packages.
~~~~~

### 下一步建议
基础工具包已经就绪且已提交。下一步我们将执行宏大的重构计划：
1.  **编写重构脚本**: 创建一个 Python 脚本，自动化地将 `tests/` 中的文件根据其模块归属移动到 `packages/*/tests/{unit,integration}/` 目录下。
2.  **执行重构**: 运行脚本并验证结果。
3.  **提交重构结果**: 在确认测试依然通过后，完成最终的目录调整提交。

如果你准备好了，我将为你编写那个自动化重构脚本。
