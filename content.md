好的，所有的 `pyproject.toml` 文件已经成功更新，依赖项和版本号现在已处于一致状态。我们现在将这些变更作为一个完整的逻辑单元提交。

[COMMIT] 计划将把所有被修改的配置文件添加到 Git 暂存区并创建提交。

## [COMMIT] chore: 升级版本至 0.3.0 并添加 pyneedle-pointer 依赖

### 用户需求
正式提交对 monorepo 依赖关系和版本号的更新，以完成 L 指针重构的配套工程化变更。

### 评论
版本号的统一跃迁（从 0.2.x 到 0.3.0）标志着 Quipu 架构进入了一个新的成熟阶段。通过明确声明 `pyneedle-pointer` 依赖，我们确保了分发包的完整性和开发者环境的自愈能力。

### 目标
1.  将 monorepo 内所有被修改的 `pyproject.toml` 文件添加到 Git 暂存区。
2.  创建一个包含详细说明的 Git 提交。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules`，将 Git 提交与之前的文件修改操作分离开来。这不仅符合 Quipu 的工作流规范，也确保了提交记录的纯净，即一个提交只负责“记录”一个已经验证通过的逻辑状态。

### 标签
#intent/tooling #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/dependency-management #task/object/versions #task/action/update #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交版本与依赖变更
将所有配置文件加入暂存区并创建提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
chore: bump versions to 0.3.0 and add pyneedle-pointer dependency

This commit finalizes the L-pointer refactoring by updating the dependency
manifests across the monorepo.

Changes:
- Added 'pyneedle-pointer ~= 0.2.1' to pyquipu-common and pyquipu-test-utils.
- Bumped pyquipu-common version to 0.2.0.
- Bumped all other packages (cli, engine, runtime, application, meta) to 0.3.0.
- Synchronized inter-package dependencies to reflect the new versioning.
- Updated root pyproject.toml dev dependencies.
~~~~~

### 下一步建议
- **同步文档**: 建议检查 `README.md` 或其他开发文档，确保其中提及的版本号和安装指令与当前的 `0.3.0` 版本一致。
- **发布准备**: 既然版本号已经提升，可以考虑进行一次全量构建测试，验证各包之间的依赖约束在安装时是否能被正确解析。
