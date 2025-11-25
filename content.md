# feat 实现 Quipu 的历史数据迁移工具。

在这份计划中，我将实现 Quipu 的历史数据迁移工具。

这是 `Quipu` 演进路线图中的关键一步，它负责将旧的、基于文件系统 (`.md` 文件) 的历史记录，无损地转换并升级为符合 `QDPS v1.0` 规范的 Git 对象存储结构。

主要工作包括：
1.  在 `quipu-engine` 中实现核心迁移逻辑 `HistoryMigrator`，它负责读取旧节点、构建新的元数据（包含迁移标记和环境遥测）并写入 Git 数据库。
2.  在 `quipu-cli` 中注册新的 `history migrate` 命令。
3.  添加针对迁移逻辑的单元测试，覆盖线性历史和断链历史等场景。

## 用户需求
用户需要一个自动化的工具，以便将现有的 Quipu 项目从旧版存储架构平滑迁移到新版 Git 对象存储架构，同时保留所有历史信息。

## 评论
这是一个必须的基础设施功能。如果没有迁移路径，老用户将被迫丢失历史或停留在旧版本。迁移工具的实现标志着新存储架构的正式就绪。

## 目标
*   实现 `quipu history migrate` 命令。
*   确保迁移后的数据符合 `QDPS v1.0` 规范，特别是元数据中的 `migration_info` 和 `generator` 字段。
*   能够正确处理父子关系，重建历史链条。

## 基本原理
*   **读取**: 复用现有的 `FileSystemHistoryReader` 加载旧数据。
*   **转换**: 在内存中构建新的 `metadata.json`，利用“知情猜测”填充缺失的环境信息，并打上 `migrated` 标记。
*   **写入**: 直接使用 `GitDB` 的底层接口 (`hash-object`, `mktree`, `commit-tree`) 构建新的 Git 对象，这比复用 `GitObjectHistoryWriter` 更灵活，因为它允许我们注入特定的时间戳和迁移元数据。
*   **链接**: 使用一个 `tree_map` 字典来维护 `output_tree -> commit_hash` 的映射，从而在转换过程中正确地将旧的 Tree 链接转换为新的 Commit 链接。

## 标签
#comp/engine #comp/cli #feat #concept/history #scope/core

---

## Script

### Acts 1: 实现迁移器核心逻辑

在 `quipu-engine` 中创建一个新的模块 `migration.py`，负责将旧的文件系统节点转换为 Git 对象节点。

~~~~~act
write_file packages/quipu-engine/src/quipu/core/migration.py
~~~~~

~~~~~python
import json
import logging
import os
import platform
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import importlib.metadata

from quipu.core.models import QuipuNode
from quipu.core.git_db import GitDB
from quipu.core.file_system_storage import FileSystemHistoryReader

logger = logging.getLogger(__name__)

class HistoryMigrator:
    """
    负责将旧的文件系统历史记录迁移到 Git 对象存储格式。
    遵循 QDPS v1.0 规范中的迁移策略。
    """

    def __init__(self, root_dir: Path, git_db: GitDB):
        self.root_dir = root_dir
        self.git_db = git_db
        self.fs_reader = FileSystemHistoryReader(root_dir / ".quipu" / "history")

    def _get_migrator_version(self) -> str:
        try:
            return importlib.metadata.version("quipu-engine")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"

    def _build_metadata(self, node: QuipuNode, assumed_env: List[str]) -> Dict[str, Any]:
        """根据 QDPS v1.0 迁移规范构建 metadata.json"""
        
        # 提取时间戳
        # 旧文件名格式: {input}_{output}_{YYYYMMDDHHMMSS}.md
        # 已经在 node.timestamp 中解析好了
        start_time = node.timestamp.timestamp()

        metadata = {
            "meta_version": "1.0-migrated",
            "type": node.node_type,
            "summary": node.summary,
            "generator": {
                "id": "manual-migrated",
                "tool": "quipu-cli-legacy"
            },
            "env": {
                "quipu": "unknown",
                # 知情猜测
                "python": platform.python_version(),
                "os": platform.system().lower()
            },
            "exec": {
                "start": start_time,
                "duration_ms": -1
            },
            "migration_info": {
                "migrated_at": time.time(),
                "migrator_version": self._get_migrator_version(),
                "assumed_env": assumed_env
            }
        }
        return metadata

    def migrate(self, dry_run: bool = False) -> int:
        """
        执行迁移过程。
        
        Returns:
            int: 迁移成功的节点数量
        """
        if not (self.root_dir / ".quipu" / "history").exists():
            logger.warning("未找到旧版历史目录 (.quipu/history)，无需迁移。")
            return 0

        # 1. 加载所有旧节点
        # load_all_nodes 会处理排序和父子关系
        nodes = self.fs_reader.load_all_nodes()
        if not nodes:
            logger.info("旧版历史目录为空。")
            return 0

        logger.info(f"找到 {len(nodes)} 个旧历史节点，准备迁移...")

        # 2. 准备状态映射表: output_tree_hash -> new_commit_hash
        # 用于将基于 Tree 的链接转换为基于 Commit 的链接
        tree_to_commit: Dict[str, str] = {}
        
        # 创世哈希 (Empty Tree)
        GENESIS_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
        migrated_count = 0
        assumed_env = ["python", "os"]

        # 按照时间顺序处理
        # 确保父节点先被处理并进入映射表
        sorted_nodes = sorted(nodes, key=lambda n: n.timestamp)

        for node in sorted_nodes:
            # 查找父 Commit
            parent_commit: Optional[str] = None
            
            if node.input_tree == GENESIS_HASH:
                # 根节点，无父 Commit
                parent_commit = None
            elif node.input_tree in tree_to_commit:
                parent_commit = tree_to_commit[node.input_tree]
            else:
                # 这是一个断链的节点（input_tree 指向了一个未知的状态，或者之前的节点尚未迁移）
                # 在旧的线性历史中，这可能意味着它是另一个分支的开始，或者历史不完整
                # 策略：视为新的根节点
                logger.warning(f"节点 {node.filename.name} 的输入状态 {node.input_tree[:7]} 未在已迁移历史中找到。将其作为新的根节点处理。")
                parent_commit = None

            if dry_run:
                logger.info(f"[Dry Run] Would migrate node: {node.summary} ({node.timestamp})")
                migrated_count += 1
                # 模拟更新映射，以便后续节点能找到父节点
                tree_to_commit[node.output_tree] = f"mock_commit_for_{node.output_tree}"
                continue

            # --- Git 底层操作 ---
            
            # 1. 准备 Metadata
            meta_data = self._build_metadata(node, assumed_env)
            meta_bytes = json.dumps(meta_data, sort_keys=False, ensure_ascii=False).encode('utf-8')
            
            # 2. 准备 Content
            # 移除可能存在的 Frontmatter (虽然 fs_reader 已经解析了，但 content 属性可能还保留着纯文本)
            # QuipuNode.content 是 body_content，已经去除了 Frontmatter
            content_bytes = node.content.encode('utf-8')

            # 3. Hash Objects
            meta_blob = self.git_db.hash_object(meta_bytes)
            content_blob = self.git_db.hash_object(content_bytes)

            # 4. Make Tree
            # 必须使用 tab 分隔
            tree_desc = (
                f"100444 blob {meta_blob}\tmetadata.json\n"
                f"100444 blob {content_blob}\tcontent.md"
            )
            tree_hash = self.git_db.mktree(tree_desc)

            # 5. Commit Tree
            parents = [parent_commit] if parent_commit else []
            # Subject
            message = f"{node.summary}\n\nX-Quipu-Output-Tree: {node.output_tree}"
            
            commit_hash = self.git_db.commit_tree(tree_hash, parents, message)
            
            # 6. 更新映射
            tree_to_commit[node.output_tree] = commit_hash
            
            # 7. 更新 Ref (每次都更新，确保 HEAD 指向最新的)
            # 注意：对于分叉的情况，这会导致 HEAD 在不同分支间跳动，最终指向时间戳最新的那个
            # 这对于单线历史是可以的。对于复杂图谱，我们可能需要更复杂的 ref 管理
            # 但 QDPS v1.0 暂定使用单一 refs/quipu/history
            self.git_db.update_ref("refs/quipu/history", commit_hash)
            
            migrated_count += 1
            logger.debug(f"已迁移节点: {node.summary} -> {commit_hash[:7]}")

        logger.info(f"迁移完成。共迁移 {migrated_count} 个节点。")
        return migrated_count
~~~~~

### Acts 2: 注册 CLI 命令

在 `packages/quipu-cli/src/quipu/cli/main.py` 中注册 `history` 命令组和 `migrate` 子命令。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~python
from quipu.core.config import ConfigManager

# 注意：不要在模块级别直接调用 setup_logging()，
~~~~~

~~~~~python
from quipu.core.config import ConfigManager
from quipu.core.migration import HistoryMigrator

# 注意：不要在模块级别直接调用 setup_logging()，
~~~~~

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~python
    if result.data: typer.echo(result.data)
    ctx.exit(result.exit_code)

if __name__ == "__main__":
    app()
~~~~~

~~~~~python
    if result.data: typer.echo(result.data)
    ctx.exit(result.exit_code)

# --- History Management Commands ---
history_app = typer.Typer(help="管理 Axon 历史记录的高级命令。")
app.add_typer(history_app, name="history")

@history_app.command("migrate")
def migrate_history(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option(
            "--work-dir", "-w",
            help="操作执行的根目录（工作区）",
            file_okay=False,
            dir_okay=True,
            resolve_path=True
        )
    ] = DEFAULT_WORK_DIR,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="仅模拟迁移过程，不写入 Git。")
    ] = False,
):
    """
    将旧版文件系统历史记录迁移到 Git 对象存储格式 (QDPS v1.0)。
    """
    setup_logging()
    root = _resolve_root(work_dir)
    
    try:
        git_db = GitDB(root)
        migrator = HistoryMigrator(root, git_db)
        
        count = migrator.migrate(dry_run=dry_run)
        
        if count > 0:
            if dry_run:
                typer.secho(f"\n✅ [Dry Run] 模拟完成，将迁移 {count} 个节点。", fg=typer.colors.GREEN)
            else:
                typer.secho(f"\n✅ 迁移成功！已转换 {count} 个历史节点。", fg=typer.colors.GREEN)
                typer.secho("💡 你现在可以使用 'quipu log' 查看新格式的历史记录。", fg=typer.colors.BLUE)
                typer.secho("⚠️  建议保留 .quipu/history 目录一段时间作为备份，确认无误后再删除。", fg=typer.colors.YELLOW)
        else:
            typer.secho("🤔 未发现需要迁移的节点，或迁移未执行。", fg=typer.colors.YELLOW)
            
    except Exception as e:
        typer.secho(f"❌ 迁移失败: {e}", fg=typer.colors.RED)
        logger.exception(e)
        ctx.exit(1)

if __name__ == "__main__":
    app()
~~~~~

### Acts 3: 单元测试

创建一个测试文件 `tests/test_migration.py`，验证迁移逻辑的正确性。

~~~~~act
write_file tests/test_migration.py
~~~~~

~~~~~python
import pytest
import subprocess
import json
from pathlib import Path
from datetime import datetime
from quipu.core.git_db import GitDB
from quipu.core.migration import HistoryMigrator
from quipu.core.file_system_storage import FileSystemHistoryWriter

@pytest.fixture
def legacy_env(tmp_path):
    """创建一个包含旧版历史记录的 Git 仓库环境"""
    repo = tmp_path / "legacy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "migrator@quipu.dev"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Migrator Bot"], cwd=repo, check=True)
    
    # 模拟旧版写入器
    fs_writer = FileSystemHistoryWriter(repo / ".quipu" / "history")
    
    return repo, fs_writer

def test_migration_linear_history(legacy_env):
    """测试标准线性历史的迁移"""
    repo, fs_writer = legacy_env
    git_db = GitDB(repo)
    
    # 1. 创建旧版历史
    # Genesis -> A
    h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    ha = "a" * 40
    node_a = fs_writer.create_node("plan", h0, ha, "Plan A")
    
    # A -> B
    hb = "b" * 40
    node_b = fs_writer.create_node("plan", ha, hb, "Plan B")
    
    # 2. 执行迁移
    migrator = HistoryMigrator(repo, git_db)
    count = migrator.migrate()
    
    assert count == 2
    
    # 3. 验证 Git 引用
    ref_head = git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()
    assert len(ref_head) == 40
    
    # 4. 验证节点链 (B -> A)
    # 检查 Head (应该对应 Node B)
    log_entries = git_db.log_ref("refs/quipu/history")
    assert len(log_entries) == 2
    
    head_entry = log_entries[0] # Newest
    assert "Plan B" in head_entry["body"]
    
    parent_entry = log_entries[1]
    assert "Plan A" in parent_entry["body"]
    
    # 5. 验证 Metadata
    # 读取 Head Commit 的 Tree -> metadata.json
    tree_hash = head_entry["tree"]
    tree_content = git_db.cat_file(tree_hash, "tree").decode()
    meta_blob_hash = [l.split()[2] for l in tree_content.splitlines() if "metadata.json" in l][0]
    
    meta_bytes = git_db.cat_file(meta_blob_hash, "blob")
    meta = json.loads(meta_bytes)
    
    assert meta["meta_version"] == "1.0-migrated"
    assert meta["generator"]["id"] == "manual-migrated"
    assert "migration_info" in meta
    assert meta["type"] == "plan"
    assert meta["summary"] == "Plan B"

def test_migration_broken_chain(legacy_env):
    """测试断链节点的处理（应作为新根）"""
    repo, fs_writer = legacy_env
    git_db = GitDB(repo)
    
    h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    ha = "a" * 40
    
    # 节点 A: 正常根
    fs_writer.create_node("plan", h0, ha, "Plan A")
    
    # 节点 C: 断链 (Input 是 Unknown)
    hun = "unknown" * 5 # invalid hash but serves as key
    hc = "c" * 40
    fs_writer.create_node("plan", hun, hc, "Plan C")
    
    migrator = HistoryMigrator(repo, git_db)
    count = migrator.migrate()
    
    assert count == 2
    
    # 验证 C 是一个孤立的根 (无 Parent)
    # 我们需要找到 C 对应的 Commit
    # 由于 update-ref 会指向最新的，如果时间戳 C > A，Head 是 C
    # 假设 fs_writer 是按顺序调用的，C 的时间戳确实较新
    
    head_commit = git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()
    head_info = git_db.log_ref(head_commit)[0]
    
    assert "Plan C" in head_info["body"]
    # 检查 Parent 字段 (git log output: hash\nparent\n...)
    # log_ref 解析后的 parent 字段
    assert head_info["parent"] == "" # 无父节点

def test_migration_dry_run(legacy_env):
    repo, fs_writer = legacy_env
    git_db = GitDB(repo)
    
    fs_writer.create_node("plan", "4b825dc642cb6eb9a060e54bf8d69288fbee4904", "a"*40, "Plan A")
    
    migrator = HistoryMigrator(repo, git_db)
    count = migrator.migrate(dry_run=True)
    
    assert count == 1
    # 验证未创建引用
    assert not git_db.has_quipu_ref()
~~~~~