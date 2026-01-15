好的，我们已经完成了 `pyquipu-bus` 的提取和全系统的依赖同步。现在我将生成一个 `[COMMIT]` 计划，将这些结构性的变更作为一个完整的逻辑单元提交。

## [COMMIT] refactor: 提取消息总线至独立的 pyquipu-bus 包

### 用户需求
提交所有关于 `pyquipu-bus` 提取的变更，包括新包的创建、代码迁移、依赖更新以及全局导入路径的替换。

### 评论
这次重构成功地将“通信机制”与“通用工具/资源”分离，不仅提高了架构的清晰度，也为未来在不引入 `common` 所有工具函数的情况下单独使用总线提供了可能。这是系统走向高内聚、低耦合的重要一步。

### 目标
1. 将所有受影响的文件添加到 Git 暂存区。
2. 创建一个符合 Conventional Commits 规范的、具有详细说明的提交。

### 基本原理
通过一次性提交这些相互关联的变更（结构、依赖、代码引用），可以保证 Git 历史的原子性。如果未来需要回滚，这个提交可以作为一个整体被操作，而不会导致系统处于不一致的状态。

### 标签
#intent/refine #flow/ready #comp/build #concept/parser #scope/api #ai/instruct #task/domain/testing #task/object/pyquipu-bus #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交变更

我们将暂存新创建的包、修改后的子包配置以及全局代码引用的变更。

~~~~~act
git_add
packages/pyquipu-bus
packages/pyquipu-common/pyproject.toml
packages/pyquipu-application/pyproject.toml
packages/pyquipu-cli/pyproject.toml
packages/pyquipu-engine/pyproject.toml
packages/pyquipu-runtime/pyproject.toml
packages/pyquipu-test-utils/pyproject.toml
pyproject.toml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: extract messaging bus into independent pyquipu-bus package

Extracted the message bus logic from 'pyquipu-common' into a dedicated 'pyquipu-bus' package. This refactoring achieves better decoupling between communication infrastructure and shared utilities/assets.

Key changes:
- Created 'packages/pyquipu-bus' with its own build configuration.
- Migrated 'MessageBus', 'MessageStore', and 'Renderer' protocols to 'pyquipu.bus'.
- Updated resource discovery in 'pyquipu.bus' to locate 'locales' within 'pyquipu-common' using package-level inspection.
- Updated 'pyproject.toml' across all monorepo packages to reflect the new dependency on 'pyquipu-bus'.
- Performed a global update of import paths from 'pyquipu.common.messaging' to 'pyquipu.bus'.
- Removed the deprecated 'messaging' module from 'pyquipu-common'.

This move centralizes the ecosystem's event orchestration and paves the way for a more streamlined 'common' package focused on static assets and pure utilities.
~~~~~

### 下一步建议
- **CI/CD 验证**：如果有持续集成流水线，请推送代码以验证新包在干净环境下的安装和运行情况。
- **文档更新**：建议在项目的 `README.md` 或架构文档中更新组件图谱，反映 `pyquipu-bus` 的新角色。
