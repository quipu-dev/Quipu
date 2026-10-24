import logging
from pathlib import Path
from typing import Annotated

import typer

from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
from .helpers import engine_context

logger = logging.getLogger(__name__)

cache_app = typer.Typer(name="cache", help="管理本地 SQLite 缓存。")


@cache_app.command("sync", help="执行增量数据补水，将 Git 历史索引同步到本地 SQLite。")
def cache_sync(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = DEFAULT_WORK_DIR,
):
    """将 Git 历史增量同步到 SQLite 缓存。"""
    typer.secho("💧 正在执行增量数据补水...", fg=typer.colors.BLUE, err=True)
    try:
        with engine_context(work_dir):
            pass
        typer.secho("✅ 数据同步完成。", fg=typer.colors.GREEN, err=True)
    except Exception as e:
        logger.exception("数据同步失败")
        typer.secho(f"❌ 数据同步失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)


@cache_app.command("rebuild", help="重建本地 SQLite 缓存数据库。")
def cache_rebuild(
    ctx: typer.Context,
    force: Annotated[bool, typer.Option("--force", "-f", help="强制执行，跳过确认提示。")] = False,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = DEFAULT_WORK_DIR,
):
    """强制全量重建 SQLite 缓存。"""
    setup_logging()
    db_path = work_dir.resolve() / ".quipu" / "history.sqlite"
    if not db_path.exists():
        typer.secho("🤷 数据库文件不存在，将直接创建。无需重建。", fg=typer.colors.YELLOW, err=True)
        cache_sync(ctx, work_dir)


@cache_app.command("prune-refs", help="清理冗余的本地分支引用 (heads)。")
def cache_prune_refs(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = DEFAULT_WORK_DIR,
):
    """
    清理 refs/quipu/local/heads/ 下的冗余引用。
    只保留分支末端 (Leaves)，删除中间节点的引用。
    """
    setup_logging()

    with engine_context(work_dir) as engine:
        typer.secho("🔍 正在扫描冗余引用...", fg=typer.colors.BLUE, err=True)

        # 1. 获取所有本地 heads
        local_heads = engine.git_db.get_all_ref_heads("refs/quipu/local/heads/")
        if not local_heads:
            typer.secho("✅ 未发现冗余引用。", fg=typer.colors.GREEN, err=True)
            return

        head_commits = {h[0] for h in local_heads}

        # 2. 批量获取这些 commit 的内容以解析 parent
        commits_content = engine.git_db.batch_cat_file(list(head_commits))

        parents_of_heads = set()
        for c_hash, content in commits_content.items():
            text = content.decode("utf-8", errors="ignore")
            for line in text.splitlines():
                if line.startswith("parent "):
                    p_hash = line.split()[1]
                    parents_of_heads.add(p_hash)
                elif line == "":
                    break

        # 3. 计算交集：既是 Head 又是某个 Head 的 Parent -> 冗余
        redundant_commits = head_commits.intersection(parents_of_heads)

        if not redundant_commits:
            typer.secho("✅ 未发现冗余引用。", fg=typer.colors.GREEN, err=True)
            return

        # 4. 找出对应的 ref names 并删除
        refs_to_delete = []
        for c_hash, ref_name in local_heads:
            if c_hash in redundant_commits:
                refs_to_delete.append(ref_name)

        typer.secho(
            f"🗑️  发现 {len(refs_to_delete)} 个冗余引用 (总计 {len(local_heads)} 个 heads)。",
            fg=typer.colors.BLUE,
            err=True,
        )

        deleted_count = 0
        for ref in refs_to_delete:
            engine.git_db.delete_ref(ref)
            deleted_count += 1

        typer.secho(f"✅ 清理完成，已删除 {deleted_count} 个引用。", fg=typer.colors.GREEN, err=True)
        return
