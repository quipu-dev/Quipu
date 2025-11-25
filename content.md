# Quipu - 未来待办事项与架构改进

本文档记录了在存储层重构过程中发现的一些待改进点、技术债以及未来可能实现的功能。这些任务在当前阶段被认为是非阻塞的，但对提升系统的健壮性、可维护性和开发者体验至关重要。

---

### 1. 统一 `Engine` 实例化工厂

-   **问题**: 当前，用于检测存储格式并创建 `Engine` 实例的逻辑在两个地方重复存在：
    1.  `packages/quipu-cli/src/quipu/cli/main.py` (`_setup_engine` 函数)，用于 `save`, `log`, `checkout` 等命令。
    2.  `packages/quipu-cli/src/quipu/cli/controller.py` (`run_quipu` 函数)，用于 `run` 命令。
    这违反了 DRY (Don't Repeat Yourself) 原则，增加了未来维护的成本。

-   **展望**: 将此逻辑提取到一个独立的、可共享的工厂函数中 (例如，在 `controller.py` 中实现，并由 `main.py` 导入)。这个工厂函数将是系统中唯一负责根据工作区状态决定并实例化 `Engine` 及其存储策略的地方。

-   **暴露的文件**:
    -   `packages/quipu-cli/src/quipu/cli/main.py`
    -   `packages/quipu-cli/src/quipu/cli/controller.py`

### 2. 实现健壮的历史记录查询 API

-   **问题**: 在集成测试 (`test_storage_integration.py`) 中，为了找到特定节点的哈希以进行 `checkout`，我们被迫使用了一个脆弱的方法：`git log --grep="<summary_string>"`。这种方法依赖于摘要的唯一性，并可能因摘要生成逻辑的改变而失效。

-   **展望**: 开发一个专门用于查询历史的内部 API 或新的 CLI 命令。这将为自动化脚本和测试提供一个稳定、可靠的方式来定位历史节点。
    -   **CLI 示例**: `quipu find-node --summary "..." --type plan`
    -   **API 示例**: `engine.find_nodes(summary_pattern="...", node_type="plan") -> List[QuipuNode]`

-   **暴露的文件**:
    -   `packages/quipu-engine/src/quipu/core/state_machine.py` (Engine API)
    -   `packages/quipu-cli/src/quipu/cli/main.py` (CLI 命令)
    -   `tests/test_storage_integration.py` (测试用例)

### 3. 使摘要 (Summary) 生成逻辑可插拔

-   **问题**: `plan` 和 `capture` 节点的摘要生成逻辑目前硬编码在 `GitObjectHistoryWriter` 和 `history.py` 中。如果用户通过插件系统添加了新的自定义 `act`，他们没有办法为这些 `act` 提供一个更智能、更具描述性的摘要生成方式。

-   **展望**: 设计一个机制，允许插件在注册 `act` 的同时，可以注册一个可选的摘要生成函数。当 `HistoryWriter` 创建一个 `plan` 节点时，它会检查执行的第一个 `act` 是否有关联的摘要函数，如果有则使用它，否则回退到默认的提取逻辑。

-   **暴露的文件**:
    -   `packages/quipu-engine/src/quipu/core/git_object_storage.py`
    -   `packages/quipu-runtime/src/quipu/core/executor.py`
    -   `packages/quipu-interfaces/src/quipu/core/types.py`

### 4. 修复 `.quipu` 目录创建时机问题

-   **问题**: 在测试日志中观察到警告 `無法創建隔離文件 ... .quipu/.gitignore: [Errno 2] No such file or directory`。这是因为 `Engine` 的构造函数试图写入 `.gitignore` 文件时，`.quipu` 目录可能尚未被创建。

-   **展望**: 调整 `Engine` 的 `__init__` 方法，确保在尝试写入任何内部文件（如 `.gitignore` 或 `HEAD`）之前，首先检查并创建 `.quipu` 目录本身。这可以确保 `Engine` 实例化的原子性和健壮性。

-   **暴露的文件**:
    -   `packages/quipu-engine/src/quipu/core/state_machine.py`

```act
end
```