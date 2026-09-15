好的，我们已经完成了依赖关系的修复、检查脚本的创建与 CI 集成，以及 `pyquipu-runtime` 的补丁版本提升。现在我将生成 `[COMMIT]` 计划，将这些更改作为一个完整的工作单元提交到 Git 仓库。

## [COMMIT] fix(deps): 修复 monorepo 依赖一致性、升级 runtime 至 0.3.1 并集成 CI 检查脚本

### 用户需求
完成所有依赖修复、CI 检查集成和版本提升的最终变更，并提交到 Git。

### 评论
通过这次提交，我们建立了 Monorepo 依赖规范守门机制（通过 `scripts/check_monorepo_deps.py`），消除了所有裸依赖和内部版本错位隐患，并将 `pyquipu-runtime` 正确递增至 `0.3.1`，恢复了生态的一致性。

### 目标
1. 将所有修改过的配置文件、脚本以及 CI 工作流文件暂存。
2. 创建包含完整上下文的 Git 提交。

### 基本原理
按照 Conventional Commits 规范及 Quipu 运行时协议，将此工作单元通过 `git_add` 和 `git_commit` 正式收口。

### 标签
#intent/fix #flow/ready #priority/high #comp/build #concept/config #scope/core #ai/instruct #task/domain/tooling #task/object/monorepo-deps #task/action/fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交依赖修复与 CI 集成

~~~~~act
git_add
pyproject.toml
.github/workflows/ci.yml
scripts/check_monorepo_deps.py
packages/pyquipu/pyproject.toml
packages/pyquipu-application/pyproject.toml
packages/pyquipu-cli/pyproject.toml
packages/pyquipu-runtime/pyproject.toml
packages/pyquipu-test-utils/pyproject.toml
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(deps): fix monorepo dependency consistency, bump runtime to 0.3.1, and integrate CI check

- Corrected pyquipu-spec dependency in pyquipu-runtime from ~=0.1.1 to ~=0.2.0
- Bumped pyquipu-runtime to 0.3.1 to patch the release metadata on PyPI
- Updated pyquipu-runtime references across all packages to ~=0.3.1
- Added missing version constraints for typer and dev dependencies in root pyproject.toml
- Added scripts/check_monorepo_deps.py to automate dependency linting
- Integrated dependency consistency check step into CI workflow (.github/workflows/ci.yml)
~~~~~

### 下一步建议

1. **推送代码至远程仓库**：
   ```bash
   git push origin <your-branch>
   ```
2. **构建并发布 `pyquipu-runtime 0.3.1`**：
   ```bash
   uv build packages/pyquipu-runtime --out-dir dist
   twine upload dist/pyquipu_runtime-0.3.1*
   ```
3. **在 PyPI 上 Yank 0.3.0**：
   登录 PyPI 后台将 `pyquipu-runtime 0.3.0` 标记为 Yanked，提示用户升级到 `0.3.1`。
