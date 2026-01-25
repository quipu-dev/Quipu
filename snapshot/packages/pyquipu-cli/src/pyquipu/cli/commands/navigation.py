import logging
from pathlib import Path
from typing import Annotated

import typer
from pyquipu.bus import bus

from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from .helpers import _execute_visit, _find_current_node, engine_context

logger = logging.getLogger(__name__)


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
    def undo(
        ctx: typer.Context,
        count: Annotated[int, typer.Option("--count", "-n", help="向上移动的步数。")] = 1,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            graph = engine.history_graph
            current_node = _find_current_node(engine, graph)
            if not current_node:
                ctx.exit(1)
            target_node = current_node
            for i in range(count):
                if not target_node.parent:
                    if i > 0:
                        bus.success("navigation.undo.reachedRoot", steps=i)
                    else:
                        bus.success("navigation.undo.atRoot")
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.parent

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )

    @app.command(help="沿当前分支向下导航（进入最新子节点）。")
    def redo(
        ctx: typer.Context,
        count: Annotated[int, typer.Option("--count", "-n", help="向下移动的步数。")] = 1,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            graph = engine.history_graph
            current_node = _find_current_node(engine, graph)
            if not current_node:
                ctx.exit(1)
            target_node = current_node
            for i in range(count):
                if not target_node.children:
                    if i > 0:
                        bus.success("navigation.redo.reachedEnd", steps=i)
                    else:
                        bus.success("navigation.redo.atEnd")
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.children[-1]
                if len(current_node.children) > 1:
                    bus.info("navigation.redo.info.multiBranch", short_hash=target_node.short_hash)

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )

    @app.command(help="导航到时间上更早的兄弟分支节点。")
    def prev(
        ctx: typer.Context,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            graph = engine.history_graph
            current_node = _find_current_node(engine, graph)
            if not current_node:
                ctx.exit(1)
            siblings = current_node.siblings
            if len(siblings) <= 1:
                bus.success("navigation.prev.noSiblings")
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == 0:
                    bus.success("navigation.prev.atOldest")
                    ctx.exit(0)
                target_node = siblings[idx - 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    "navigation.info.navigating",
                    short_hash=target_node.short_hash,
                )
            except ValueError:
                pass

    @app.command(help="导航到时间上更新的兄弟分支节点。")
    def next(
        ctx: typer.Context,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            graph = engine.history_graph
            current_node = _find_current_node(engine, graph)
            if not current_node:
                ctx.exit(1)
            siblings = current_node.siblings
            if len(siblings) <= 1:
                bus.success("navigation.next.noSiblings")
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == len(siblings) - 1:
                    bus.success("navigation.next.atNewest")
                    ctx.exit(0)
                target_node = siblings[idx + 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    "navigation.info.navigating",
                    short_hash=target_node.short_hash,
                )
            except ValueError:
                pass

    @app.command(help="在访问历史中后退一步。")
    def back(
        ctx: typer.Context,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.back()
                if result_hash:
                    bus.success("navigation.back.success", short_hash=result_hash[:7])
                else:
                    bus.warning("navigation.back.atStart")
            except Exception as e:
                logger.error("后退操作失败", exc_info=True)
                bus.error("navigation.back.error", error=str(e))
                ctx.exit(1)

    @app.command(help="在访问历史中前进一步。")
    def forward(
        ctx: typer.Context,
        work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.forward()
                if result_hash:
                    bus.success("navigation.forward.success", short_hash=result_hash[:7])
                else:
                    bus.warning("navigation.forward.atEnd")
            except Exception as e:
                logger.error("前进操作失败", exc_info=True)
                bus.error("navigation.forward.error", error=str(e))
                ctx.exit(1)
