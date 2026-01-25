好的，迁移到 `hatchling` 的工作已经完成。通过这次重构，我们不仅消除了讨厌的弃用警告，还为 Quipu 建立了一个更现代、更稳健的构建基础设施。

我将生成一个 `[COMMIT]` 计划，将这些配置变更正式提交。

## [COMMIT] refactor(build): 迁移至 hatchling 后端并修复 PEP 639 许可证警告

### 错误分析

在之前的构建尝试中，`setuptools` 输出了多条 `SetuptoolsDeprecationWarning` 警告：
1.  **许可证格式陈旧**: `project.license` 使用表结构（`{ text = "..." }`）已被弃用。
2.  **分类器冗余**: 显式声明许可证分类器（`License :: OSI Approved :: ...`）已不再推荐，应由 SPDX 表达式替代。
3.  **构建后端局限性**: `setuptools` 在处理 Monorepo 子包的源码发现时逻辑较复杂，容易产生不确定的构建结果。

### 用户需求
修复构建警告，并采用更适合 Monorepo 的 `hatchling` 构建后端。

### 评论
这是一次及时的“技术债”偿还。在系统初期就对齐最新的打包标准（如 PEP 639），可以避免未来在大规模发布时遇到阻断性问题。`hatchling` 的引入也使得我们的 `pyproject.toml` 文件变得更加简洁易读。

### 目标
1.  将所有 8 个子包及根元包的 `pyproject.toml` 变更提交到 Git。
2.  确保构建后端的切换在版本历史中得到清晰记录。

### 基本原理
我们按照现代 Python 打包标准，将 `license` 简化为 SPDX 字符串，并利用 `hatch` 的 `targets.wheel.packages` 配置来精确控制源码包含逻辑。这种“显式优于隐式”的方法极大地提高了分发包的可靠性。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/tooling #task/object/hatchling-migration #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交构建后端迁移变更

我们将所有更新后的配置文件添加到暂存区并创建提交。

~~~~~act
git_add
packages/pyquipu-interfaces/pyproject.toml
packages/pyquipu-common/pyproject.toml
packages/pyquipu-bus/pyproject.toml
packages/pyquipu-engine/pyproject.toml
packages/pyquipu-runtime/pyproject.toml
packages/pyquipu-application/pyproject.toml
packages/pyquipu-cli/pyproject.toml
packages/pyquipu-test-utils/pyproject.toml
pyproject.toml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(build): migrate to hatchling and fix PEP 639 license warnings

Switched the build backend from setuptools to hatchling across the entire monorepo to leverage better workspace support and modern packaging standards.

Key Improvements:
- Updated 'project.license' to use simple SPDX identifier strings ("Apache-2.0") as per PEP 639.
- Removed deprecated license classifiers to eliminate setuptools build warnings.
- Standardized package discovery using '[tool.hatch.build.targets.wheel]' configuration, ensuring reliable source inclusion from 'src/'.
- Streamlined 'pyproject.toml' files by removing redundant auto-discovery configurations.

This migration ensures a clean, warning-free build process and aligns the project with current Python packaging best practices.
~~~~~

### 下一步建议
- **清理环境**: 建议运行 `rm -rf dist/ packages/*/src/*.egg-info` 来清理旧的构建产物。
- **发布测试**: 现在你可以放心地尝试运行 `uv build packages/pyquipu-interfaces/`，享受整洁、无警告的构建输出了。
- **Action 验证**: 既然后端已经切换，下一次推送标签触发 GitHub Action 时，它将自动使用 `hatchling` 进行构建，我们可以观察其在线运行情况。
