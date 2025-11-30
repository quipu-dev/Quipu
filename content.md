分析正确。我之前的修改只解决了**增量**问题，即新创建的节点会自动修剪其父节点的引用。但这并未处理已经存在的 294 个冗余引用。

你需要一个一次性的清理工具来处理这些历史遗留的引用。

我将为你创建一个新的 CLI 命令：`quipu cache prune-refs`。这个命令会安全地分析整个历史图谱，并移除所有指向非叶子节点（即有子节点的节点）的冗余 `head` 引用。

## [WIP] feat: 添加 cache prune-refs 命令以清理冗余历史引用

### 用户需求
`refs/quipu/local/heads/` 目录中存在大量历史遗留的、指向非叶子节点的冗余引用，需要一个工具来安全地清理它们，以减少磁盘空间占用。

### 评论
这是一个必要的维护工具，它与增量修剪功能互补。通过提供一个明确的清理命令，我们可以处理任何历史时期产生的冗余引用，确保仓库元数据的健康。

### 目标
1.  在 `quipu cache` 子命令下创建一个新的 `prune-refs` 命令。
2.  该命令将加载完整的历史图谱。
3.  识别出所有非叶子节点（有子节点的节点）。
4.  查找所有指向这些非叶子节点的 `refs/quipu/local/heads/*` 引用。
5.  在用户确认后，删除这些冗余引用。

### 基本原理
该命令是“引用修剪”逻辑的批量应用版本。它首先在内存中构建完整的依赖关系图，然后将所有 `head` 引用分为两类：指向叶子节点的（必要的）和指向非叶子节点的（冗余的）。通过仅删除后者，我们可以在不破坏历史可达性的前提下，将引用数量最小化。为防止误操作，此破坏性操作前会要求用户确认。

### 标签
#intent/build #intent/refine #flow/ready #priority/high 
#comp/cli #comp/engine #concept/history 
#scope/dx #ai/instruct
#task/domain/storage #task/object/ref-management #task/action/cleanup #task/state/continue

---

### Script

#### Acts 1: 在 `cache.py` 中实现 `prune-refs` 命令

我们将更新 `commands/cache.py` 文件，加入新的 `prune-refs` 命令。为确保完整性，我将重写整个文件，包含已有的 `sync`、`rebuild` 和新增的 `prune-refs`。

~~~~~act
write_file
packages/quipu-cli/src/pyquipu/cli/commands/cache.py
~~~~~
~~~~~python
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

cache_app = typer.Typer(name="cache", help="管理本地 SQLite 缓存及 Git 元数据。")


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


@cache_app.command("prune-refs")
def cache_prune_refs(
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
    清理冗余的 Quipu head 引用，仅保留叶子节点引用。
    """
    setup_logging()
    bus.info("cache.prune.info.starting")

    with engine_context(work_dir) as engine:
        graph = engine.history_graph
        if not graph:
            bus.info("query.info.emptyHistory")
            ctx.exit(0)

        # 1. 识别所有非叶子节点的 commit hash
        non_leaf_commits = {node.commit_hash for node in graph.values() if node.children}
        bus.info("cache.prune.info.nonLeafFound", count=len(non_leaf_commits))

        # 2. 查找所有指向非叶子节点的本地 head 引用
        all_refs = engine.git_db.list_refs("refs/quipu/local/heads")
        refs_to_prune = []
        for ref_name, commit_hash in all_refs.items():
            if commit_hash in non_leaf_commits:
                refs_to_prune.append(ref_name)

        if not refs_to_prune:
            bus.success("cache.prune.success.noAction")
            ctx.exit(0)

        bus.warning("cache.prune.warning.aboutToDelete", count=len(refs_to_prune))
        # 打印部分待删除的 ref 作为示例
        for ref_to_show in refs_to_prune[:10]:
            bus.data(f"  - {ref_to_show}")
        if len(refs_to_prune) > 10:
            bus.data(f"  ... and {len(refs_to_prune) - 10} more.")

        # 3. 请求用户确认
        if not force:
            prompt = bus.get("cache.prune.prompt.confirm")
            if not prompt_for_confirmation(prompt, default=False):
                bus.warning("common.prompt.cancel")
                raise typer.Abort()

        # 4. 执行删除
        deleted_count = 0
        with typer.progressbar(refs_to_prune, label="正在修剪引用") as progress:
            for ref_name in progress:
                try:
                    engine.git_db.delete_ref(ref_name)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete ref {ref_name}", exc_info=True)
                    bus.error("cache.prune.error.deleteFailed", ref=ref_name, error=str(e))

        bus.success("cache.prune.success.complete", count=deleted_count)
~~~~~
#### Acts 2: 更新 `git_db` 以支持列出引用

`prune-refs` 命令需要一个方法来获取所有的 `head` 引用。我们将这个底层方法添加到 `GitDB` 类中。

~~~~~act
patch_file
packages/quipu-engine/src/pyquipu/engine/git_db.py
~~~~~
~~~~~python
    def batch_cat_file(self, object_hashes: List[str]) -> Dict[str, bytes]:
~~~~~
~~~~~python
    def list_refs(self, prefix: str) -> Dict[str, str]:
        """
        列出指定前缀下的所有引用。
        返回一个 {ref_name: commit_hash} 的字典。
        """
        # format=%(refname) %(objectname)
        res = self._run(["for-each-ref", "--format=%(refname) %(objectname)", prefix], check=False)
        if res.returncode != 0 or not res.stdout.strip():
            return {}

        results = {}
        for line in res.stdout.strip().splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                results[parts] = parts
        return results

    def batch_cat_file(self, object_hashes: List[str]) -> Dict[str, bytes]:
~~~~~

### 下一步建议

现在你可以运行 `qd cache prune-refs` 来清理历史引用。执行后，再次检查 `wc -l` 的结果，它应该会显著减少。
