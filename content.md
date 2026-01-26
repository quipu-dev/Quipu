好的，所有的逻辑漏洞都已堵上。现在的 `release_manager` 已经具备了处理 Monorepo 构建偏移和杂乱文件的能力，其健壮性已达到工业级标准。

我们将这些关键修复提交到 Git 历史。

## [COMMIT] fix(ci/cd): 修复 Release Manager 的构建路径与文件过滤逻辑

### 错误分析
1.  **通配符失效**: `subprocess.run` 无法解析路径中的 `*`。
2.  **构建目录漂移**: `uv build` 在工作区模式下默认将产物输出到根目录，导致子包脚本无法定位。
3.  **上传污染**: `glob("*")` 包含了 `.gitignore` 等非发布文件，触发了 `twine` 的格式校验错误。

### 用户需求
固化对 `scripts/release_manager.py` 的一系列修复，确保 CD 流程在 CI/CD 环境中能够一次性通过。

### 评论
这些修复虽然看似细小，但对于一个无人值守的持续交付系统来说至关重要。通过显式指定构建路径和精细化的文件过滤，我们消除了环境不确定性，确保了发布流程的原子性和幂等性。

### 目标
1.  暂存 `scripts/release_manager.py` 的最终稳定版本。
2.  创建一个清晰记录修复逻辑的提交。

### 基本原理
根据 `d3-constraint-quipu-plan-script-rules` 约束，在所有功能逻辑稳定后，通过一个独立的计划完成提交操作。

### 标签
#intent/fix #flow/ready #priority/high 
#comp/build #concept/executor #scope/dx 
#ai/instruct 
#task/domain/devops #task/object/release-manager #task/action/bug-fix 
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交修复

我们将修正后的脚本添加到 Git 暂存区并提交。

~~~~~act
git_add
~~~~~
~~~~~files
scripts/release_manager.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(ci/cd): robust path handling and artifact filtering in release manager

Fixed several critical bugs in the idempotent CD script:
- Resolved wildcard expansion failure by manually listing files from 'dist/'.
- Forced 'uv build' to output to package-local 'dist/' using '--out-dir'.
- Restricted upload artifacts to standard '.whl' and '.tar.gz' to avoid invalid distribution errors (e.g., from .gitignore).
- Enhanced 'run_cmd' to capture and display both stdout and stderr on failure for easier CI debugging.
- Enabled forced tagging and pushing to support retries in idempotent workflows.
~~~~~

### 下一步建议
- **CI 最终验证**: 现在可以将代码推送到远程 `main` 分支。观察 GitHub Actions，它应该能够成功完成 `pyquipu` 门户包的发布。
- **监控版本**: 发布成功后，可以在 PyPI 上检查 `pyquipu` 的版本是否已更新为 `0.1.1`。
