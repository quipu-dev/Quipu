好的，现在我们将创建一个 Git 提交来保存 `quipu axon` 子命令的实现。

## [COMMIT] feat: 实现无状态的 `quipu axon` 子命令

### 用户需求
将 `axon` 子命令的实现持久化到版本历史中。

### 评论
这个提交标志着 `axon` 功能的正式完成，使其成为项目的一部分，并将 `quipu-runtime` 的通用价值释放出来。

### 目标
执行 `git add` 和 `git commit` 操作，将新创建的 `axon.py` 和修改后的 `main.py` 文件提交到仓库。

### 基本原理
遵循“工作-提交”分离的原则，在确认功能实现方案后，通过一个独立的、原子化的提交来保存工作成果。

### 标签
#intent/tooling #flow/ready #priority/high #comp/cli #concept/executor #scope/api #ai/instruct #task/domain/cli #task/object/subcommand-axon #task/action/implementation #task/state/end

---

### Script

#### Acts 1: 将变更添加到暂存区

~~~~~act
git_add
~~~~~
~~~~~
packages/quipu-cli/src/quipu/cli/commands/axon.py
packages/quipu-cli/src/quipu/cli/main.py
~~~~~

#### Acts 2: 创建 Git 提交

~~~~~act
git_commit
~~~~~
~~~~~
feat: 实现无状态的 quipu axon 子命令

该命令作为一个独立的、轻量级的 Markdown 任务执行器，实现了 `quipu-runtime` 与 `quipu-engine` 的解耦。

- **无状态**: `axon` 命令不初始化 `Engine`，不依赖 `.git` 或 `.quipu` 目录，确保其在任何环境下都能运行。
- **功能对齐**: 复用了 `run` 命令的文件/STDIN 读取逻辑，并支持 `--yolo`, `--list-acts` 等参数。
- **应用扩展**: 为 Quipu 在 CI/CD、项目脚手架和自动化脚本等非版本控制场景下的应用提供了入口。
~~~~~
