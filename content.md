好的，所有的架构调整和文档修正都已完成。现在，我们将这些变更作为一个完整的逻辑单元提交到 Git 仓库，正式确立 Quipu 的 CD v2.0 架构。

## [COMMIT] feat(ci/cd): 实现基于主分支的幂等性 CD 架构 v2.0

### 用户需求
将之前完成的所有关于 CD 架构重构、根项目重命名、门户包创建以及文档链接修正的变更固化到 Git 历史中。

### 评论
这次提交标志着 Quipu 项目从传统的“手动/Tag 驱动发布”转向了“版本势能驱动”的自动化持续交付模型。这不仅提升了工程质量，也为未来的多包协同开发奠定了坚实的基础。

### 目标
1.  暂存所有新增、修改及移动的文件。
2.  创建一个具有详尽说明的 Commit，记录 CD v2.0 的核心逻辑。

### 基本原理
根据 `d3-constraint-quipu-plan-script-rules` 约束，在完成所有文件系统操作并验证通过后，通过一个独立的 `[COMMIT]` 计划来完成 Git 固化。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/build #comp/docs #comp/cli #scope/dx
#ai/instruct
#task/domain/devops #task/object/cd-pipeline #task/action/implementation
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

我们将所有变更（包括门户包的创建、根项目的重命名、CD 脚本和工作流的部署）添加到 Git 暂存区，并执行提交。

~~~~~act
git_add
~~~~~
~~~~~files
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(ci/cd): implement idempotent main-branch CD architecture v2.0

This commit introduces a high-fidelity continuous delivery system where releases are driven by version changes in `pyproject.toml` rather than manual Git tags.

Key changes:
- Refactored project identity: Renamed root package to `pyquipu-monorepo` to distinguish the repository (factory) from its products.
- Created `packages/pyquipu` facade: A meta-package serving as the primary distribution entry point on PyPI.
- Implemented `scripts/release_manager.py`: A dynamic workspace scanner that performs idempotent releases by comparing local versions against PyPI metadata.
- Automated Workflow: Added `.github/workflows/cd.yml` which triggers on every push to the main branch, ensuring "version is truth".
- Doc Migration: Moved user-facing documentation to the facade package and updated links to absolute GitHub URLs to prevent PyPI rendering issues.

This architecture ensures architectural incorruptibility and eliminates release-related human error.
~~~~~

### 下一步建议
- **合并分支**: 如果你当前在特性分支上，现在可以将其合并到 `main`。一旦合并，GitHub Actions 将首次运行 `release_manager.py`。
- **验证发布**: 合并后观察 GitHub Actions 的输出，确保 `release_manager` 正确识别了所有的子包。
- **分支清理**: 在确认 CD 管道正常工作后，可以清理旧的发布分支或不再需要的临时脚本。
