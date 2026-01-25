好的，基础设施已经搭建完毕。现在我们将这些变更作为一个完整的逻辑单元提交到版本库中。

这个提交标志着 Quipu 从一个纯开发态的 Monorepo 演进到了具备工业级分发能力的系统。

## [COMMIT] feat(build): 实现基于 Scoped Tags 的多包独立发布基础设施

### 用户需求
完成 Quipu Monorepo 的发布配置，使其支持通过 GitHub Actions 进行子包的按需发布。

### 评论
通过引入 Scoped Tags 模式，我们解决了 Monorepo 中最棘手的发布耦合问题。这不仅提升了开发者的灵活性，也为最终用户提供了更精确的依赖管理。

### 目标
1.  将所有 8 个子包及根元包的构建配置添加到暂存区。
2.  将新的 GitHub Action 工作流添加到暂存区。
3.  执行提交并记录详细的变更说明。

### 基本原理
按照 `[COMMIT]` 协议的要求，此计划仅包含 Git 状态变更操作，不涉及任何文件内容的修改，确保了提交原子性的纯净。

### 标签
#intent/tooling #flow/ready #comp/build #scope/dx #ai/instruct #task/domain/tooling #task/object/pypi-infrastructure #task/action/setup #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交发布基础设施变更

我们将添加所有受影响的 `pyproject.toml` 文件以及新创建的 GitHub Action 工作流。

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
.github/workflows/python-publish.yml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(build): implement scoped-tag publishing infrastructure

Established a robust CI/CD pipeline and standardized metadata for independent package distribution on PyPI.

Key changes:
- Standardized 'pyproject.toml' across all 8 sub-packages with consistent authorship, license (Apache-2.0), and classifiers.
- Converted internal dependencies to use semantic versioning (~= 0.1.0) instead of local workspace paths, ensuring PyPI compatibility.
- Implemented '.github/workflows/python-publish.yml' with a scoped-tag parser.
- Enabled granular releases via the '{pkg_name}@v{version}' tag pattern (e.g., pyquipu-engine@v0.1.0).
- Removed problematic root README references in sub-packages to comply with hatchling build constraints.

This setup allows each component of the Quipu ecosystem to be released and versioned independently while maintaining a cohesive development experience within the monorepo.
~~~~~

### 下一步建议
- **初次预发布**: 建议先尝试给最基础的包 `pyquipu-interfaces` 打一个 `test` 标签（如果你已经配置好了 `PYPI_API_TOKEN`），观察 Action 的执行情况。
- **发布脚本**: 随着包数量增多，手动打标可能会出错。我们可以考虑编写一个简单的 Python 脚本，用于自动检查依赖关系并按顺序触发特定包的发布标签。
