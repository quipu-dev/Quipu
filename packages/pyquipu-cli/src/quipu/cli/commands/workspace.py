from pathlib import Path
from typing import Annotated

import typer
from quipu.spec.constants import EMPTY_TREE_HASH

from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from .helpers import engine_context


def register(app: typer.Typer):
    @app.command(help="将当前工作区的变更创建为一个新的快照节点。")
    def save(
        ctx: typer.Context,
        message: Annotated[str | None, typer.Argument(help="本次快照的简短描述。")] = None,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
    ):
        with engine_context(work_dir) as engine:
            current_tree_hash = engine.git_db.get_tree_hash()
            is_node_clean = (engine.current_node is not None) and (engine.current_node.output_tree == current_tree_hash)
            is_genesis_clean = (not engine.history_graph) and (current_tree_hash == EMPTY_TREE_HASH)

            if is_node_clean or is_genesis_clean:
                typer.secho("✅ 工作区状态未发生变化，无需创建快照。", fg=typer.colors.GREEN, err=True)
                ctx.exit(0)

            try:
                node = engine.capture_drift(current_tree_hash, message=message)
                msg_suffix = f" ({message})" if message else ""
                typer.secho(f"📸 快照已保存: {node.short_hash}{msg_suffix}", fg=typer.colors.GREEN, err=True)
            except Exception as e:
                typer.secho(f"❌ 创建快照失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)

    @app.command(help="丢弃当前工作区的所有变更，恢复到上一个快照状态。")
    def discard(
        ctx: typer.Context,
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
            if not graph:
                typer.secho("❌ 错误: 找不到任何历史记录，无法确定要恢复到哪个状态。", fg=typer.colors.RED, err=True)
                ctx.exit(1)

            target_tree_hash = engine._read_head()
            latest_node = None
            if target_tree_hash:
                for node in graph.values():
                    if node.output_tree == target_tree_hash:
                        latest_node = node
                        break

            if not latest_node:
                latest_node = max(graph.values(), key=lambda n: n.timestamp)
                target_tree_hash = latest_node.output_tree
                typer.secho(
                    f"⚠️  HEAD 指针丢失或无效，将恢复到最新历史节点: {latest_node.short_hash}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )

            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_tree_hash:
                typer.secho(
                    f"✅ 工作区已经是干净状态 ({latest_node.short_hash})，无需操作。",
                    fg=typer.colors.GREEN,
                    err=True,
                )
                ctx.exit(0)

            assert target_tree_hash is not None
            diff_stat_str = engine.git_db.get_diff_stat(target_tree_hash, current_hash)

            if not force:
                prompt = f"🚨 即将丢弃上述所有变更，并恢复到状态 {latest_node.short_hash}。\n此操作不可逆。是否继续？"
                if not prompt_for_confirmation(prompt, diff_lines=diff_stat_str.splitlines(), default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()

            try:
                engine.visit(target_tree_hash)
                typer.secho(
                    f"✅ 工作区已成功恢复到节点 {latest_node.short_hash}。",
                    fg=typer.colors.GREEN,
                    err=True,
                )
            except Exception as e:
                typer.secho(f"❌ 恢复状态失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
