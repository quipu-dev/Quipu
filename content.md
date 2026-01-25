好的，既然代码已经修改完成且符合预期，我们现在将这些变更作为一个完整的逻辑单元提交到 Git 仓库。

我将生成一个 `[COMMIT]` 计划，执行 `git add` 和 `git commit` 操作。

## [COMMIT] refactor(cli): 将无状态逻辑和 Acts 发现机制迁移至 application 层

### 用户需求

将之前在 `axon` 和 `run` 命令中实现的无状态执行逻辑以及 `acts` 发现逻辑提交到版本控制系统。

### 评论

这是一次关键的架构优化。通过将业务逻辑从 CLI 命令中剥离，我们不仅解决了代码重复（DRY）问题，还显著增强了系统在非 CLI 环境下的重用能力。这标志着 `application` 层正逐渐成熟为整个 Quipu 系统的核心指挥中心。

### 目标

1.  将修改后的 `controller.py`（增加应用服务函数）添加到暂存区。
2.  将重构后的 `run.py` 和 `axon.py`（转变为瘦客户端）添加到暂存区。
3.  创建一个描述详尽的 Git 提交，记录这次分层架构的改进。

### 基本原理

根据 **Monorepo 测试架构规范** 和 **HFEA 协议**，我们将变更固化。通过 `[COMMIT]` 计划，我们将这些逻辑上关联的修改原子化地存入历史记录，确保后续开发可以基于一个干净、分层明确的基座进行。

### 标签

#intent/refine #flow/ready #priority/high #comp/cli #comp/application #scope/core #scope/dx #ai/instruct #task/domain/cli #task/object/refactor #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 提交变更

我们将所有涉及到的文件添加到 Git 暂存区，并创建一个记录此次架构重构的提交。

~~~~~act
git_add
packages/pyquipu-application/src/pyquipu/application/controller.py
packages/pyquipu-cli/src/pyquipu/cli/commands/run.py
packages/pyquipu-cli/src/pyquipu/cli/commands/axon.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(cli): move stateless logic and acts discovery to application layer

This commit performs a significant architectural cleanup by extracting business logic from the CLI layer into the application layer:

1.  Created `get_available_acts(work_dir)` in `application.controller` to centralize act discovery, eliminating duplicated logic in `run` and `axon` commands (DRY).
2.  Created `run_stateless_plan(...)` in `application.controller` to encapsulate the entire execution flow for the `axon` command.
3.  Refactored `quipu run` and `quipu axon` to act as thin clients, delegating core operations to the newly created application services.

These changes clarify the boundary between the presentation layer (CLI) and the orchestration layer (Application), enabling easier testing and potential future reuse of Quipu's core logic in different interfaces.
~~~~~

### 下一步建议

-   **继续有状态命令的迁移**: 接下来，我们可以采用同样的模式，将 `checkout`, `log`, `save`, `discard` 等依赖 `Engine` 的有状态命令逻辑也迁移到 `QuipuApplication` 类的方法中。
-   **增加集成测试**: 既然逻辑已经移到了 `application` 层，我们可以为 `run_stateless_plan` 和 `get_available_acts` 编写纯 Python 的集成测试，而无需再依赖复杂的 `Typer.CliRunner` 模拟。
