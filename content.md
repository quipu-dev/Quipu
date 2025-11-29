好的，第一阶段的重构已经完成。现在我将创建一个 `[COMMIT]` 计划，将这些架构改进作为一个逻辑单元提交到版本控制中。

## [COMMIT] refactor(cli, common): 解耦 MessageBus 与 Typer Renderer

### 用户需求
将 `MessageBus` 的渲染逻辑与其核心功能解耦。具体来说，将 `TyperRenderer` 从 `quipu-common` 移动到 `quipu-cli`，并修改 `MessageBus` 以通过依赖注入的方式接收一个渲染器实例。

### 评论
这是一个关键的架构重构，它遵循了依赖倒置原则，使得 `quipu-common` 成为一个与 UI 无关的、可移植的通用库。这不仅提升了代码的模块化程度，还极大地简化了未来对 `MessageBus` 进行测试的复杂度。

### 目标
1.  将 `TyperRenderer` 实现移动到 `quipu-cli` 中。
2.  修改 `MessageBus` 以接受外部注入的 `Renderer`。
3.  从 `quipu-common` 中移除 `typer` 依赖。
4.  在 `quipu-cli` 的应用入口处完成渲染器的注入。
5.  创建一个 Git 提交来固化这次重构。

### 基本原理
通过将 `TyperRenderer` (实现细节) 从 `quipu-common` (通用库) 移动到 `quipu-cli` (应用程序)，我们切断了底层库对上层 UI 框架的依赖。`MessageBus` 的全局实例现在在 `quipu-cli` 启动时才被“激活”，注入一个具体的渲染器。这使得系统的不同部分各司其职，架构更加清晰和健壮。

### 标签
#intent/refine #flow/ready #priority/critical #comp/cli #comp/common #concept/ui #scope/core #scope/dx #ai/instruct #task/domain/cli #task/object/message-bus #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交第一阶段重构的全部变更

我们将把本次重构涉及的所有文件添加到 Git 暂存区，并创建一个符合规范的提交。

```````act
git_add
packages/quipu-cli/src/quipu/cli/rendering.py
packages/quipu-common/src/quipu/common/messaging/bus.py
packages/quipu-common/pyproject.toml
packages/quipu-cli/src/quipu/cli/main.py
```````

```````act
git_commit
```````
```````text
refactor(cli, common): decouple MessageBus from Typer Renderer

Implements the first phase of the MessageBus refactoring plan. This change decouples the core message bus logic in `quipu-common` from the specific UI rendering implementation (`Typer`).

Key changes:
- The `TyperRenderer` class and `Renderer` protocol have been moved from `quipu-common` to a new `rendering.py` module within `quipu-cli`.
- The `MessageBus` in `quipu-common` no longer initializes a default renderer. Instead, it exposes a `set_renderer()` method for dependency injection.
- The `typer` dependency has been removed from `quipu-common`, making it a UI-agnostic package.
- The `TyperRenderer` is now instantiated and injected into the global `bus` instance at the `quipu-cli` application entry point (`main.py`).

This change adheres to the Dependency Inversion Principle, making `quipu-common` more reusable and significantly improving the testability of components that rely on the `MessageBus`.
```````

### 下一步建议
我们已经成功地为后续的 `MessageBus` 迁移工作奠定了坚实的架构基础。

现在，我们可以安全地进入 **Phase 2: 迁移 `quipu-runtime`**。这个阶段将首次大规模地应用 `MessageBus`，替换 `acts` 和 `executor` 中的 `logging` 调用，真正开始收获这次架构重构带来的好处。
