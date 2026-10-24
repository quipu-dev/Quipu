import logging
from pathlib import Path
from typing import Annotated

import typer

from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from .helpers import _execute_visit, _find_current_node, engine_context

logger = logging.getLogger(__name__)


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

            matches = [
                node
                for node in graph.values()
                if node.commit_hash.startswith(hash_prefix) or node.output_tree.startswith(hash_prefix)
            ]
            if not matches:
                typer.secho(
                    f"❌ 错误: 未找到 output_tree 哈希前缀为 '{hash_prefix}' 的历史节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)

            unique_output_trees = {node.output_tree for node in matches}
            if len(unique_output_trees) > 1:
                typer.secho(
                    f"❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {len(matches)} 个节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)

            if len(matches) > 1:
                matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)

            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree

            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_output_tree_hash:
                typer.secho(
                    f"✅ 工作区已处于目标状态 ({target_node.short_hash})，无需操作。",
                    fg=typer.colors.GREEN,
                    err=True,
                )
                ctx.exit(0)

            is_dirty = engine.current_node is None or engine.current_node.output_tree != current_hash
            if is_dirty:
                typer.secho(
                    "⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                engine.capture_drift(current_hash)
                typer.secho("✅ 变更已捕获。", fg=typer.colors.GREEN, err=True)
                current_hash = engine.git_db.get_tree_hash()

            diff_stat_str = engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)

            if not force:
                prompt = (
                    f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n"
                    f"此操作会覆盖未提交的更改。是否继续？"
                )
                if not prompt_for_confirmation(prompt, diff_lines=diff_stat_str.splitlines(), default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()

            _execute_visit(
                ctx,
                engine,
                target_output_tree_hash,
                f"🚀 正在导航到节点: {target_node.short_hash}",
            )

    @app.command(name="set-head", help="手动将 HEAD（基准节点）重定位到指定状态，不修改工作区文件。")
    def set_head(
        ctx: typer.Context,
        hash_prefix: Annotated[str, typer.Argument(help="目标历史节点的 commit_hash 或 output_tree 的哈希前缀。")],
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

            matches = [
                node
                for node in graph.values()
                if node.commit_hash.startswith(hash_prefix) or node.output_tree.startswith(hash_prefix)
            ]
            if not matches:
                typer.secho(
                    f"❌ 错误: 未找到哈希前缀为 '{hash_prefix}' 的历史节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)

            unique_output_trees = {node.output_tree for node in matches}
            if len(unique_output_trees) > 1:
                typer.secho(
                    f"❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {len(matches)} 个节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)

            if len(matches) > 1:
                matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)

            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree

            current_head = engine._read_head()
            if current_head == target_output_tree_hash:
                typer.secho(
                    f"✅ 当前 HEAD 已指向目标节点 ({target_node.short_hash})，无需操作。",
                    fg=typer.colors.GREEN,
                    err=True,
                )
                ctx.exit(0)

            current_tree = engine.git_db.get_tree_hash()
            diff_stat_str = engine.git_db.get_diff_stat(target_output_tree_hash, current_tree)

            if not force:
                prompt = (
                    f"🚨 即将把基准历史节点 (HEAD) 重定位到 {target_node.short_hash} ({target_node.timestamp})。\n"
                    f"工作区现有文件内容将保持不变。是否继续？"
                )
                if not prompt_for_confirmation(
                    prompt, diff_lines=diff_stat_str.splitlines() if diff_stat_str else None, default=True
                ):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()

            try:
                engine.set_head(hash_prefix)
                typer.secho(
                    f"📌 HEAD 基准已成功重定位至 {target_node.short_hash} ({target_node.summary or '无描述'})。",
                    fg=typer.colors.GREEN,
                    err=True,
                )
            except Exception as e:
                logger.exception("重定位 HEAD 失败")
                typer.secho(f"❌ 导航操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)

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
                        typer.secho(f"✅ 已到达历史根节点 (移动了 {i} 步)。", fg=typer.colors.GREEN, err=True)
                    else:
                        typer.secho("✅ 已在历史根节点。", fg=typer.colors.GREEN, err=True)
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.parent

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                f"🚀 正在导航到节点: {target_node.short_hash}",
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
                        typer.secho(f"✅ 已到达分支末端 (移动了 {i} 步)。", fg=typer.colors.GREEN, err=True)
                    else:
                        typer.secho("✅ 已在分支末端。", fg=typer.colors.GREEN, err=True)
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.children[-1]
                if len(current_node.children) > 1:
                    typer.secho(
                        f"💡 当前节点有多个分支，已自动选择最新分支 -> {target_node.short_hash}",
                        fg=typer.colors.BLUE,
                        err=True,
                    )

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                f"🚀 正在导航到节点: {target_node.short_hash}",
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
                typer.secho("✅ 当前节点没有兄弟分支。", fg=typer.colors.GREEN, err=True)
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == 0:
                    typer.secho("✅ 已在最旧的兄弟分支。", fg=typer.colors.GREEN, err=True)
                    ctx.exit(0)
                target_node = siblings[idx - 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    f"🚀 正在导航到节点: {target_node.short_hash}",
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
                typer.secho("✅ 当前节点没有兄弟分支。", fg=typer.colors.GREEN, err=True)
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == len(siblings) - 1:
                    typer.secho("✅ 已在最新的兄弟分支。", fg=typer.colors.GREEN, err=True)
                    ctx.exit(0)
                target_node = siblings[idx + 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    f"🚀 正在导航到节点: {target_node.short_hash}",
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
                    typer.secho(f"✅ 已后退到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
                else:
                    typer.secho("⚠️  已到达访问历史的起点。", fg=typer.colors.YELLOW, err=True)
            except Exception as e:
                logger.exception("后退操作失败")
                typer.secho(f"❌ 后退操作失败: {e}", fg=typer.colors.RED, err=True)
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
                    typer.secho(f"✅ 已前进到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
                else:
                    typer.secho("⚠️  已到达访问历史的终点。", fg=typer.colors.YELLOW, err=True)
            except Exception as e:
                logger.exception("前进操作失败")
                typer.secho(f"❌ 前进操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
