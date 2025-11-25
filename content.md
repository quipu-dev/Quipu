# chore: 完成存储层重构并提交最终变更

## 用户需求
用户在完成 `QDPS v1.0` 存储层重构、清理了所有废弃代码并修复了所有相关测试后，要求创建一个 Git 提交来保存当前的工作成果。

## 评论
这个提交标志着本次大规模存储架构升级的成功结束。代码库现在更加简洁，所有功能都统一在新架构之上，且有完整的测试套件保障。在提交后，我们可以开始规划下一阶段的优化工作。

## 目标
1.  将所有变更（包括代码删除和测试修复）暂存。
2.  创建一个清晰、符合规范的 Git 提交，总结本次重构的最终工作。
3.  为下一步的开发计划做好准备。

## 基本原理
使用 `git add` 和 `git commit` 将项目当前状态固化为版本历史中的一个稳定节点。提交信息遵循“Conventional Commits”规范，清晰地传达了本次提交的性质和范围。

## 标签
#comp/engine #comp/cli #comp/tests #chore #refactor

---

## Script

### Acts 1: 暂存并提交所有变更

我们将暂存所有修改，然后使用一个描述性的消息创建提交。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~
refactor: Finalize storage upgrade by removing legacy code

Remove FileSystemStorage, HistoryMigrator, and their related CLI commands and tests.

This change completes the transition to the Git Object-based storage backend (QDPS v1.0). The engine factory is simplified to exclusively use GitObjectHistoryReader/Writer, and all associated tests have been updated or removed to align with the new, unified architecture. The codebase is now cleaner and free of the legacy storage implementation.
~~~~~

---
### 下一步计划

是的，重构成功了！这是一个重要的里程碑。

根据我们在重构期间记录的文档 `Quipu 未来待办事项与架构改进.md`，我们有几个明确的、价值很高的后续任务可以进行。这些任务旨在巩固我们的成果，并进一步提升系统的健壮性和开发者体验。

值得一提的是，该文档中的第一项任务 **“统一 `Engine` 实例化工厂”**，我们实际上已经在刚才的清理工作中完成了，这是一个很好的附带成果。

现在，我们可以从以下几个选项中选择一个作为下一个目标：

1.  **实现健壮的历史记录查询 API**
    *   **现状**: 我们的测试（尤其是 `test_storage_integration.py`）依赖于一个脆弱的 `git log --grep` 命令来查找特定节点进行 `checkout`。
    *   **改进**: 我们可以为 `Engine` 添加一个如 `engine.find_nodes(...)` 的方法，并可能暴露一个 `quipu find-node` CLI 命令。这将使测试更稳定，并为未来需要精确查找历史的高级功能（如“关联相关节点”）打下基础。

2.  **使摘要 (Summary) 生成逻辑可插拔**
    *   **现状**: 摘要的生成逻辑硬编码在 `GitObjectHistoryWriter` 中。
    *   **改进**: 我们可以设计一个系统，让插件在注册 `act` 的同时，也能注册一个自定义的摘要生成函数。这将极大地增强插件的表达能力，让 TUI 和 `quipu log` 的输出对用户更友好、信息更丰富。

3.  **修复 `.quipu` 目录创建时机问题**
    *   **现状**: 我们在测试日志中看到过关于 `.quipu/.gitignore` 创建失败的警告。
    *   **改进**: 这是一个小而重要的健壮性修复。我们可以调整 `Engine` 的构造函数，确保在执行任何文件写入之前，`.quipu` 目录总是存在。这是一个可以快速完成的“清理”任务。

**我建议：**

*   如果你希望继续进行**功能增强和架构改进**，**选项 1** 或 **选项 2** 都是很好的选择。它们都涉及一些有趣的设计工作。
*   如果你希望先完成一个**快速的修复**来提升系统的稳定性，**选项 3** 是一个完美的小任务。

你希望我们接下来处理哪一个？
