Excellent point. This is a crucial architectural clarification. Your directive to distinguish between `commit_hash` and `tree_hash` goes to the heart of the **HFEA Ontological Correctness** principle. An operation should be explicit about the entity it acts upon.

-   A **commit** is an *event* in history.
-   A **tree** is a *state* of the workspace.

When a user says `checkout`, their intent is to restore the workspace to a specific *state*, therefore the operation should fundamentally be on a **tree hash**. By making the application layer's API explicit about this, we eliminate ambiguity and build a more robust and self-documenting system.

I will proceed by refactoring the `checkout` command first, as it's a perfect example of this stateful migration.

## [WIP] refactor: Migrate checkout logic to QuipuApplication

### 用户需求

1.  将 `quipu checkout` 命令的业务逻辑从 CLI 层迁移到 `QuipuApplication` 类的一个新方法中。
2.  根据用户指令，新的应用层 API 必须明确其操作的是 `tree_hash`, 而不是模糊的 `hash`。

### 评论

这是实现我们架构目标的最后、也是最关键的一步。将有状态的 `engine` 操作封装在 `application` 层的方法中，可以使我们的核心业务逻辑（如导航、保存、查询）变得完全独立于 UI，从而可以被单元测试，也可以在未来被其他接口（如 Web API）复用。明确 `tree_hash` 的使用，是对系统语义的一次重要提纯。

### 目标

1.  在 `QuipuApplication` 类中创建一个新的公共方法 `checkout_by_tree_hash_prefix(self, tree_hash_prefix: str, force: bool)`。
2.  将 `navigation.py` 中 `checkout` 命令的所有业务逻辑——包括查找节点、处理歧义、检查工作区是否已是目标状态、检查工作区是否“脏”、捕获漂移、获取 diff、请求用户确认，以及最终执行 `visit`——全部迁移到这个新方法中。
3.  确保新方法在其所有执行路径中都返回一个标准的 `QuipuResult` 对象，作为与 CLI 层的稳定契约。
4.  彻底简化 `checkout` 命令，使其仅负责：
    *   创建一个 `QuipuApplication` 实例。
    *   调用 `app.checkout_by_tree_hash_prefix(...)`。
    *   使用 `bus` 渲染返回的 `QuipuResult`。

### 基本原理

我们正在将 `QuipuApplication` 固化为一个**应用服务 Facade**。`checkout_by_tree_hash_prefix` 方法封装了一个完整的业务用例。CLI 层调用它时，不需要知道 `engine` 的存在，也不需要关心确认流程的细节（这些通过注入的 `confirmation_handler` 处理）。这种彻底的解耦是 HFEA **严格分层与边界**原则的终极体现。通过在方法命名中包含 `_by_tree_hash_prefix`，我们让 API 的意图变得不言自明，消除了任何猜测。

### 标签

#intent/refine #flow/ready #priority/high #comp/cli #comp/application #concept/navigation #concept/state #scope/core #scope/api #scope/dx #ai/brainstorm #task/domain/cli #task/object/stateful-commands #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 在 `QuipuApplication` 中创建 `checkout` 服务方法

我们将把 `navigation.py` 中的 `checkout` 逻辑移植到 `controller.py` 的 `QuipuApplication` 类中，并将其改造为一个健壮的、返回 `QuipuResult` 的方法。

~~~~~act
patch_file
packages/pyquipu-application/src/pyquipu/application/controller.py
~~~~~
~~~~~python.old
    def run(self, content: str, parser_name: str) -> QuipuResult:
        # --- Phase 1 & 2: Perception & Decision (Lazy Capture) ---
        input_tree_hash = self._prepare_workspace()
~~~~~
~~~~~python.new
    def checkout_by_tree_hash_prefix(self, tree_hash_prefix: str, force: bool = False) -> QuipuResult:
        graph = self.engine.history_graph
        matches = [node for node in graph.values() if node.output_tree.startswith(tree_hash_prefix)]

        if not matches:
            return QuipuResult(
                success=False,
                exit_code=1,
                message="navigation.checkout.error.notFound",
                msg_kwargs={"hash_prefix": tree_hash_prefix},
            )
        if len(matches) > 1:
            return QuipuResult(
                success=False,
                exit_code=1,
                message="navigation.checkout.error.notUnique",
                msg_kwargs={"hash_prefix": tree_hash_prefix, "count": len(matches)},
            )

        target_node = matches[0]
        target_output_tree_hash = target_node.output_tree
        current_hash = self.engine.git_db.get_tree_hash()

        if current_hash == target_output_tree_hash:
            return QuipuResult(
                success=True,
                exit_code=0,
                message="navigation.checkout.info.noAction",
                msg_kwargs={"short_hash": target_node.short_hash},
            )

        is_dirty = self.engine.current_node is None or self.engine.current_node.output_tree != current_hash
        if is_dirty:
            # Here we need a message bus to inform the user.
            # For now, we rely on the CLI to have a bus configured.
            # A better solution would involve passing the bus into the app.
            # bus.warning("navigation.checkout.info.capturingDrift")
            self.engine.capture_drift(current_hash)
            # bus.success("navigation.checkout.success.driftCaptured")
            current_hash = self.engine.git_db.get_tree_hash()

        diff_stat_str = self.engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)

        if not self.yolo and not force:
            # Re-create prompt here as we don't have access to the bus directly yet.
            # This highlights a future improvement area.
            prompt = (
                f"将工作区检出到快照 {target_node.short_hash} ({target_node.timestamp}) "
                f"会覆盖当前未保存的变更。"
            )
            try:
                self.confirmation_handler(diff_stat_str.splitlines(), prompt)
            except OperationCancelledError:
                raise  # Re-raise to be caught by the top-level handler

        self.engine.visit(target_output_tree_hash)
        return QuipuResult(
            success=True,
            exit_code=0,
            message="navigation.success.visit",
            msg_kwargs={"short_hash": target_output_tree_hash[:7]},
        )

    def run(self, content: str, parser_name: str) -> QuipuResult:
        # --- Phase 1 & 2: Perception & Decision (Lazy Capture) ---
        input_tree_hash = self._prepare_workspace()
~~~~~

#### Acts 2: 简化 `checkout` CLI 命令

现在，`checkout` 命令的实现变得极其简单。它只负责收集用户输入，调用应用服务，然后渲染结果。

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/navigation.py
~~~~~
~~~~~python.old
def register(app: typer.Typer):
    @app.command(help="检出指定状态的快照到工作区。")
    def checkout(
        ctx: typer.Context,
        hash_prefix: Annotated[str, typer.Argument(help="目标状态节点 output_tree 的哈希前缀。")],
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        force: Annotated[bool, typer.Option("--force", "-f", help="强制执行，跳过确认提示。")] = False,
    ):
        with engine_context(work_dir) as engine:
            graph = engine.history_graph

            matches = [node for node in graph.values() if node.output_tree.startswith(hash_prefix)]
            if not matches:
                bus.error("navigation.checkout.error.notFound", hash_prefix=hash_prefix)
                ctx.exit(1)
            if len(matches) > 1:
                bus.error("navigation.checkout.error.notUnique", hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)
            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree

            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_output_tree_hash:
                bus.success("navigation.checkout.info.noAction", short_hash=target_node.short_hash)
                ctx.exit(0)

            is_dirty = engine.current_node is None or engine.current_node.output_tree != current_hash
            if is_dirty:
                bus.warning("navigation.checkout.info.capturingDrift")
                engine.capture_drift(current_hash)
                bus.success("navigation.checkout.success.driftCaptured")
                current_hash = engine.git_db.get_tree_hash()

            diff_stat_str = engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)

            if not force:
                prompt = bus.get(
                    "navigation.checkout.prompt.confirm",
                    short_hash=target_node.short_hash,
                    timestamp=target_node.timestamp,
                )
                if not prompt_for_confirmation(prompt, diff_lines=diff_stat_str.splitlines(), default=False):
                    bus.warning("common.prompt.cancel")
                    raise typer.Abort()

            _execute_visit(
                ctx,
                engine,
                target_output_tree_hash,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )

    @app.command(help="沿当前分支向上导航（回到父节点）。")
~~~~~
~~~~~python.new
from ..ui_utils import confirmation_handler_for_executor


def register(app: typer.Typer):
    @app.command(help="检出指定状态的快照到工作区。")
    def checkout(
        ctx: typer.Context,
        tree_hash_prefix: Annotated[str, typer.Argument(help="目标状态快照 (tree) 的哈希前缀。")],
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        force: Annotated[bool, typer.Option("--force", "-f", help="强制执行，跳过确认提示。")] = False,
    ):
        from pyquipu.application.controller import QuipuApplication
        from pyquipu.interfaces.exceptions import OperationCancelledError

        app_instance = None
        try:
            # The application instance manages the engine's lifecycle
            app_instance = QuipuApplication(work_dir=work_dir, confirmation_handler=confirmation_handler_for_executor)
            app_instance.engine.align()  # Ensure history is loaded

            result = app_instance.checkout_by_tree_hash_prefix(tree_hash_prefix=tree_hash_prefix, force=force)

            if result.message:
                kwargs = result.msg_kwargs or {}
                if not result.success:
                    bus.error(result.message, **kwargs)
                else:
                    bus.success(result.message, **kwargs)

            ctx.exit(result.exit_code)

        except OperationCancelledError:
            bus.warning("common.prompt.cancel")
            ctx.exit(2)
        except Exception as e:
            bus.error("common.error.generic", error=str(e))
            ctx.exit(1)
        finally:
            if app_instance and app_instance.engine:
                app_instance.engine.close()

    @app.command(help="沿当前分支向上导航（回到父节点）。")
~~~~~

### 下一步建议

我们已经为有状态命令的迁移建立了一个清晰、可重复的模式。

我建议我们按照这个模式，继续迁移剩余的有状态命令。下一个合适的候选者是 `workspace.py` 中的 `save` 和 `discard` 命令，因为它们是 `checkout` 的逻辑对应操作。完成后，我们将拥有一个几乎完全由应用层驱动的、干净的 CLI。
