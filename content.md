好的，我们已经成功地重构了消息管理系统，使其更加模块化和健壮。现在，我们将这个重要的架构改进作为一个完整的逻辑单元进行提交。

## [COMMIT] refactor(common, locales): 实现分层消息域并分离 runtime 消息

### 用户需求
将 `quipu-runtime` 模块的消息从 `cli.json` 文件中分离出来，存放到一个独立的 `runtime.json` 文件中。为了支持这一点，需要更新 `quipu-common` 中的 `MessageStore` 以从一个语言目录加载并合并所有 `.json` 消息文件，从而实现按功能域管理消息资源。

### 评论
这是一个关键的架构重构，它纠正了消息管理的语义混淆问题，实现了真正的模块化和解耦。通过让每个核心包“拥有”自己的消息资源文件，我们为系统的长期可维护性和未来向其他模块（如 `quipu-engine`）的扩展奠定了坚实的基础。

### 目标
1.  已修改 `quipu.common.messaging.bus.MessageStore`，使其能够加载并合并一个目录下所有的 `.json` 文件。
2.  已创建新的 `locales/zh/runtime.json` 文件。
3.  已将之前添加到 `locales/zh/cli.json` 中的所有 `runtime.*` 和 `acts.*` 相关的消息，移动到了新的 `runtime.json` 中。
4.  创建一个 Git 提交，将此项架构改进持久化。

### 基本原理
我们修改了 `MessageStore._load_messages` 方法，使其遍历给定语言环境目录下的所有 `*.json` 文件，并将其内容合并到内部的 `_messages` 字典中。这一改动对上层的 `MessageBus` 是透明的，它仍然访问一个统一的消息命名空间。这使得我们可以将消息资源文件按照其所属的包或领域进行物理分离，而无需改变任何调用点的代码，从而实现了高内聚、低耦合的设计。

### 标签
#intent/refine #flow/ready #priority/high #comp/common #comp/runtime #concept/ui #scope/core #ai/instruct #task/domain/ui #task/object/message-bus #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更

现在，我们将所有相关的修改添加到 Git 暂存区，并创建一个内容详尽的提交。

~~~~~act
git_add
packages/quipu-common/src/quipu/common/messaging/bus.py
locales/zh/cli.json
locales/zh/runtime.json
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(common, locales): implement layered message domains

Separates message resource files by their logical domain, improving
modularity and maintainability.

Previously, all messages, including those from the `quipu-runtime`
package, were stored in a single `cli.json`. This created semantic
coupling and made the file difficult to manage.

This commit introduces the concept of layered message domains by:
1.  Updating `MessageStore` to load and merge all `*.json` files from
    a locale directory (e.g., `locales/zh/`).
2.  Creating a new `locales/zh/runtime.json` file.
3.  Moving all `runtime.*` and `acts.*` messages from `cli.json` to
    `runtime.json`.

This change decouples core libraries from specific frontends and
establishes a scalable pattern for managing messages as new modules
are added.
~~~~~

### 下一步建议
我们已经成功完成了 `MessageBus` 的架构重构和 `quipu-runtime` 的迁移。现在的消息系统既健壮又可扩展。

下一步的逻辑重点是 **Phase 3: 迁移 `quipu-engine`**。

这个阶段需要更加谨慎，因为 `engine` 中的日志更多是面向开发者的调试信息。我们需要仔细甄别哪些 `logging` 调用应该保留（用于调试），哪些是真正需要暴露给用户的警告或错误信息，应该被迁移到 `engine.json` 中。

如果你同意，我们可以开始分析 `quipu-engine` 的代码，并制定迁移计划。
