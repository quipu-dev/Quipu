## 生成 `git add` 和 `git commit` 指令来保存这次重构

这是一个重要的改进，因为它不仅简化了代码，还通过确保 `engine.close()` 的调用修复了一个潜在的资源泄漏问题。

### Script

#### Acts 1: 提交变更

~~~~~act
git_add
packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~
refactor(cli): 提取 Engine 设置逻辑到上下文管理器

此前，在 `quipu.cli.main` 中的每个命令都包含了用于日志记录设置和 `Engine`
实例创建的样板代码。这导致了代码重复，并且更严重的是，由于 `engine.close()`
没有被一致地调用，存在资源泄漏的风险。

本提交引入了 `engine_context` 上下文管理器，它封装了 `Engine`
实例的整个生命周期：
1.  设置日志记录
2.  通过 `create_engine` 创建实例 (包含 align)
3.  在 `finally` 块中调用 `engine.close()` 以确保资源释放

所有相关的命令都已重构为使用此上下文管理器，从而使代码更清晰、更安全、更易于维护。这也解决了潜在的数据库连接泄漏问题。
~~~~~
