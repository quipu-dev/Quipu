import logging
from pathlib import Path
from typing import Annotated

import typer
from pyquipu.common.messaging import bus

from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
from ..ui_utils import prompt_for_confirmation
from .helpers import engine_context

logger = logging.getLogger(__name__)

cache_app = typer.Typer(name="cache", help="管理本地 SQLite 缓存。")


@cache_app.command("sync")
def cache_sync(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
        ),
    ] = DEFAULT_WORK_DIR,
):
    """
    将 Git 历史增量同步到 SQLite 缓存。
    """
    bus.info("cache.sync.info.hydrating")
    try:
        with engine_context(work_dir):
            pass
        bus.success("cache.sync.success")
    except Exception as e:
        logger.error("数据同步失败", exc_info=True)
        bus.error("cache.sync.error", error=str(e))
        ctx.exit(1)


@cache_app.command("rebuild")
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
    """
    强制全量重建 SQLite 缓存。
    """
    setup_logging()
    db_path = work_dir.resolve() / ".quipu" / "history.sqlite"
    if not db_path.exists():
        bus.warning("cache.rebuild.info.dbNotFound")
        cache_sync(ctx, work_dir)


@cache_app.command("prune-refs")
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
        bus.info("cache.prune.info.scanning")
        
        # 1. 获取所有本地 heads
        local_heads = engine.git_db.get_all_ref_heads("refs/quipu/local/heads/")
        if not local_heads:
            bus.success("cache.prune.info.noRedundant")
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
            bus.success("cache.prune.info.noRedundant")
            return

        # 4. 找出对应的 ref names 并删除
        refs_to_delete = []
        for c_hash, ref_name in local_heads:
            if c_hash in redundant_commits:
                refs_to_delete.append(ref_name)
        
        bus.info("cache.prune.info.found", count=len(refs_to_delete), total=len(local_heads))
        
        deleted_count = 0
        for ref in refs_to_delete:
            engine.git_db.delete_ref(ref)
            deleted_count += 1
            
        bus.success("cache.prune.success", count=deleted_count)
        return

    if not force:
        prompt = f"🚨 即将删除并重建数据库 {db_path}。\n此操作不可逆。是否继续？"
        if not prompt_for_confirmation(prompt, default=False):
            bus.warning("common.prompt.cancel")
            raise typer.Abort()

    try:
        db_path.unlink()
        bus.info("cache.rebuild.info.deleting")
    except (OSError, PermissionError) as e:
        logger.error(f"删除旧数据库文件 '{db_path}' 失败", exc_info=True)
        bus.error("cache.rebuild.error.deleteFailed", error=str(e))
        ctx.exit(1)

    cache_sync(ctx, work_dir)
