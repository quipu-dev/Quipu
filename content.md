[简单回答：Fhrsk 将执行 Stage 7 的重构计划，包括 `remote`, `export`, `ui` 命令的 MessageBus 迁移及相关测试更新。]

## [WIP] feat: 重构 remote, export, ui 命令以适配 MessageBus

### 错误分析
当前 `quipu remote` (sync), `quipu export`, `quipu ui` 命令直接使用 `typer.secho` 和 `typer.echo` 进行信息输出，并且包含了硬编码的文本、图标和颜色。这违反了新的 `MessageBus` 统一输出规范，导致无法支持国际化，且测试脆弱。此外，`MessageBus` 尚缺乏获取格式化消息字符串的方法 (`get`)，导致需要作为参数传递给 `prompt_for_confirmation` 的提示语无法被统一管理。

### 用户需求
1.  在 `quipu-common` 的 `MessageBus` 中添加 `get(msg_id, **kwargs)` 方法，以便获取格式化后的字符串（用于 Prompt 等场景）。
2.  将 `remote.py`, `export.py`, `ui.py` 中的所有用户输出迁移到 `bus` 调用。
3.  在 `locales/zh/cli.json` 中补充 `sync`, `export`, `ui` 相关的消息模板。
4.  更新 `tests/cli/test_export_command.py`，使用 Mock 的 `bus` 对象进行断言，替代字符串匹配。

### 评论
这是 MessageBus 重构计划的第七阶段（独立功能命令），完成后绝大部分 CLI 命令都将遵循新规范，系统的一致性和可维护性将大幅提升。

### 目标
1.  增强 `MessageBus` API。
2.  完成 `remote.py`, `export.py`, `ui.py` 的重构。
3.  更新本地化资源文件。
4.  确保相关测试通过。

### 基本原理
通过 `MessageBus` 接管所有输出，实现业务逻辑与展示层的解耦。对于需要传递字符串给其他函数（如 `prompt_for_confirmation`）的场景，使用 `bus.get()` 获取翻译后的文本。测试中使用 `unittest.mock` 验证语义调用。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #comp/common #concept/ui #scope/ux #scope/dx #ai/instruct #task/domain/cli #task/object/standalone-commands #task/action/refactor #task/state/continue #task/status/active

---

### Script

#### Acts 1: 增强 `MessageBus` 以支持获取消息字符串

我们需要先给 `MessageBus` 添加 `get` 方法，以便 `export.py` 等命令可以获取本地化后的 Prompt 字符串。

~~~~~act
patch_file
packages/quipu-common/src/quipu/common/messaging/bus.py
~~~~~
~~~~~python
    def error(self, msg_id: str, **kwargs: Any) -> None:
        self._render("error", msg_id, **kwargs)

    def data(self, data_string: str) -> None:
        self._renderer.data(data_string)
~~~~~
~~~~~python
    def error(self, msg_id: str, **kwargs: Any) -> None:
        self._render("error", msg_id, **kwargs)

    def get(self, msg_id: str, **kwargs: Any) -> str:
        """Retrieves and formats a message string without rendering it."""
        template = self._store.get(msg_id)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Formatting error for '{msg_id}': missing key {e}")
            return template

    def data(self, data_string: str) -> None:
        self._renderer.data(data_string)
~~~~~

#### Acts 2: 更新 `cli.json` 资源文件

补充 `sync`, `ui`, `export` 相关的消息模板。

~~~~~act
patch_file
locales/zh/cli.json
~~~~~
~~~~~json
  "workspace.discard.ui.diffHeader": "\n以下是即将被丢弃的变更:"
}
~~~~~
~~~~~json
  "workspace.discard.ui.diffHeader": "\n以下是即将被丢弃的变更:",

  "sync.setup.firstUse": "🤝 首次使用 sync 功能，正在自动配置用户身份...",
  "sync.setup.success": "✅ 已根据你的 Git 邮箱 '{email}' 生成并保存用户 ID: {user_id}",
  "sync.setup.error.noEmail": "❌ 错误：无法获取你的 Git 用户邮箱。",
  "sync.setup.info.emailHint": "💡 请先运行以下命令进行设置:\n  git config --global user.email \"you@example.com\"",
  "sync.run.info.mode": "⚙️  模式: {mode}",
  "sync.run.info.pulling": "⬇️  正在拉取...",
  "sync.run.info.pullingPrune": "⬇️  正在拉取 (带修剪)...",
  "sync.run.info.reconciling": "🤝 正在调和...",
  "sync.run.info.pushing": "⬆️  正在推送...",
  "sync.run.info.pushingForce": "⬆️  正在强制推送...",
  "sync.run.info.pruning": "🗑️  正在修剪本地...",
  "sync.run.success.bidirectional": "\n✅ Quipu 双向同步完成。",
  "sync.run.success.pullOnly": "\n✅ Quipu 拉取同步完成。",
  "sync.run.success.pullPrune": "\n✅ Quipu 拉取同步 (带修剪) 完成。",
  "sync.run.success.pushOnly": "\n✅ Quipu 推送同步完成。",
  "sync.run.success.pushForce": "\n✅ Quipu 强制推送完成。",
  "sync.run.info.cacheHint": "\n💡 提示: 运行 `quipu cache sync` 来更新本地数据库和 UI 视图。",
  "sync.run.error.generic": "\n❌ 同步操作失败: {error}",

  "ui.error.depMissing": "❌ TUI 依赖 'textual' 未安装。",
  "ui.info.depHint": "💡 请运行: pip install 'textual>=0.58.0'",
  "ui.info.emptyHistory": "📜 历史记录为空，无需启动 UI。",
  "ui.info.checkoutRequest": "\n> TUI 请求检出到: {short_hash}",

  "export.info.emptyHistory": "📜 历史记录为空，无需导出。",
  "export.error.badParam": "❌ 参数错误: {error}",
  "export.info.noMatchingNodes": "🤷 未找到符合条件的节点。",
  "export.prompt.overwrite": "⚠️ 目录 '{path}' 非空，是否清空并继续?",
  "export.info.starting": "🚀 正在导出 {count} 个节点到 '{path}'...",
  "export.info.zipping": "📦 正在压缩导出文件...",
  "export.success.zip": "\n✅ 导出成功，已保存为压缩包: {path}",
  "export.success.dir": "\n✅ 导出成功完成。"
}
~~~~~

#### Acts 3: 重构 `remote.py`

替换硬编码输出为 `bus` 调用。

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/commands/remote.py
~~~~~
~~~~~python
import subprocess
from pathlib import Path
from typing import Annotated, Optional
from enum import Enum

import typer
from quipu.common.identity import get_user_id_from_email
from quipu.engine.config import ConfigManager
from quipu.engine.git_db import GitDB

from ..config import DEFAULT_WORK_DIR
from ..logger_config import setup_logging
from ..utils import find_git_repository_root
from quipu.common.messaging import bus


class SyncMode(str, Enum):
    BIDIRECTIONAL = "bidirectional"
    PUSH_FORCE = "push-force"
    PUSH_ONLY = "push-only"
    PULL_PRUNE = "pull-prune"
    PULL_ONLY = "pull-only"


def register(app: typer.Typer):
    @app.command()
    def sync(
        ctx: typer.Context,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        remote_option: Annotated[
            Optional[str], typer.Option("--remote", "-r", help="Git 远程仓库的名称 (覆盖配置文件)。")
        ] = None,
        mode: Annotated[
            SyncMode,
            typer.Option(
                "--mode",
                "-m",
                help="同步模式: 'bidirectional' (默认), 'push-force', 'push-only', 'pull-prune', 'pull-only'",
                case_sensitive=False,
            ),
        ] = SyncMode.BIDIRECTIONAL,
    ):
        """
        与远程仓库同步 Quipu 历史图谱。
        """
        setup_logging()
        sync_dir = find_git_repository_root(work_dir) or work_dir
        config = ConfigManager(sync_dir)
        remote = remote_option or config.get("sync.remote_name", "origin")

        final_user_id = config.get("sync.user_id")
        if not final_user_id:
            bus.info("sync.setup.firstUse")
            try:
                result = subprocess.run(
                    ["git", "config", "user.email"], cwd=sync_dir, capture_output=True, text=True, check=True
                )
                email = result.stdout.strip()
                if not email:
                    raise ValueError("Git user.email is empty.")

                final_user_id = get_user_id_from_email(email)
                config.set("sync.user_id", final_user_id)
                config.save()
                bus.success("sync.setup.success", email=email, user_id=final_user_id)

            except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
                bus.error("sync.setup.error.noEmail")
                bus.warning("sync.setup.info.emailHint")
                ctx.exit(1)

        try:
            git_db = GitDB(sync_dir)
            subscriptions = config.get("sync.subscriptions", [])
            target_ids_to_fetch = set(subscriptions)
            target_ids_to_fetch.add(final_user_id)

            bus.info("sync.run.info.mode", mode=mode.value)

            # --- Operation Dispatch based on Mode ---
            match mode:
                case SyncMode.BIDIRECTIONAL:
                    bus.info("sync.run.info.pulling")
                    for target_id in sorted(list(target_ids_to_fetch)):
                        git_db.fetch_quipu_refs(remote, target_id)
                    bus.info("sync.run.info.reconciling")
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    bus.info("sync.run.info.pushing")
                    git_db.push_quipu_refs(remote, final_user_id)
                    bus.success("sync.run.success.bidirectional")

                case SyncMode.PULL_ONLY:
                    bus.info("sync.run.info.pulling")
                    for target_id in sorted(list(target_ids_to_fetch)):
                        git_db.fetch_quipu_refs(remote, target_id)
                    bus.info("sync.run.info.reconciling")
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    bus.success("sync.run.success.pullOnly")

                case SyncMode.PULL_PRUNE:
                    bus.info("sync.run.info.pullingPrune")
                    for target_id in sorted(list(target_ids_to_fetch)):
                        git_db.fetch_quipu_refs(remote, target_id)
                    bus.info("sync.run.info.reconciling")
                    git_db.reconcile_local_with_remote(remote, final_user_id)
                    bus.info("sync.run.info.pruning")
                    git_db.prune_local_from_remote(remote, final_user_id)
                    bus.success("sync.run.success.pullPrune")

                case SyncMode.PUSH_ONLY:
                    bus.info("sync.run.info.pushing")
                    git_db.push_quipu_refs(remote, final_user_id, force=False)
                    bus.success("sync.run.success.pushOnly")

                case SyncMode.PUSH_FORCE:
                    bus.info("sync.run.info.pushingForce")
                    git_db.push_quipu_refs(remote, final_user_id, force=True)
                    bus.success("sync.run.success.pushForce")

            bus.info("sync.run.info.cacheHint")

        except RuntimeError as e:
            bus.error("sync.run.error.generic", error=str(e))
            ctx.exit(1)
~~~~~

#### Acts 4: 重构 `export.py`

替换输出，并使用 `bus.get()` 处理 Prompt。

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Set

import typer
import yaml

from .helpers import engine_context
from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from quipu.common.messaging import bus
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine

logger = logging.getLogger(__name__)


def _sanitize_summary(summary: str) -> str:
    """净化摘要以用作安全的文件名部分。"""
    if not summary:
        return "no-summary"
    sanitized = re.sub(r"[\\/:#\[\]|]", "_", summary)
    sanitized = re.sub(r"[\s_]+", "_", sanitized)
    return sanitized[:60]


def _generate_filename(node: QuipuNode) -> str:
    """根据规范生成文件名。"""
    ts = node.timestamp.strftime("%y%m%d-%H%M")
    short_hash = node.commit_hash[:7]
    sanitized_summary = _sanitize_summary(node.summary)
    return f"{ts}-{short_hash}-{sanitized_summary}.md"


def _format_frontmatter(node: QuipuNode) -> str:
    """生成 YAML Frontmatter 字符串。"""
    data = {
        "commit_hash": node.commit_hash,
        "output_tree": node.output_tree,
        "input_tree": node.input_tree,
        "timestamp": node.timestamp.isoformat(),
        "node_type": node.node_type,
    }
    if node.owner_id:
        data["owner_id"] = node.owner_id
    yaml_str = yaml.dump(data, Dumper=yaml.SafeDumper, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---"


def _filter_nodes(
    nodes: List[QuipuNode], limit: Optional[int], since: Optional[str], until: Optional[str]
) -> List[QuipuNode]:
    """根据时间戳和数量过滤节点列表。"""
    filtered = nodes
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace(" ", "T"))
            filtered = [n for n in filtered if n.timestamp >= since_dt]
        except ValueError:
            raise typer.BadParameter("无效的 'since' 时间戳格式。请使用 'YYYY-MM-DD HH:MM'。")
    if until:
        try:
            until_dt = datetime.fromisoformat(until.replace(" ", "T"))
            filtered = [n for n in filtered if n.timestamp <= until_dt]
        except ValueError:
            raise typer.BadParameter("无效的 'until' 时间戳格式。请使用 'YYYY-MM-DD HH:MM'。")
    if limit is not None and limit > 0:
        filtered = filtered[:limit]
    return list(reversed(filtered))


def _generate_navbar(
    current_node: QuipuNode,
    exported_hashes_set: Set[str],
    filename_map: Dict[str, str],
    hidden_link_types: Set[str],
) -> str:
    """生成导航栏 Markdown 字符串。"""
    nav_links = []

    # 1. 总结节点 (↑)
    if "summary" not in hidden_link_types:
        ancestor = current_node.parent
        while ancestor:
            if ancestor.input_tree == ancestor.output_tree and ancestor.commit_hash in exported_hashes_set:
                nav_links.append(f"> ↑ [总结节点]({filename_map[ancestor.commit_hash]})")
                break
            ancestor = ancestor.parent

    # 2. 上一分支点 (↓)
    if "branch" not in hidden_link_types:
        ancestor = current_node.parent
        found_branch_point = None
        while ancestor:
            if len(ancestor.children) > 1 and ancestor.commit_hash in exported_hashes_set:
                found_branch_point = ancestor
                break
            ancestor = ancestor.parent
        if (
            found_branch_point
            and current_node.parent
            and found_branch_point.commit_hash != current_node.parent.commit_hash
        ):
            nav_links.append(f"> ↓ [上一分支点]({filename_map[found_branch_point.commit_hash]})")

    # 3. 父节点 (←)
    if "parent" not in hidden_link_types:
        if current_node.parent and current_node.parent.commit_hash in exported_hashes_set:
            nav_links.append(f"> ← [父节点]({filename_map[current_node.parent.commit_hash]})")

    # 4. 子节点 (→)
    if "child" not in hidden_link_types:
        for child in current_node.children:
            if child.commit_hash in exported_hashes_set:
                nav_links.append(f"> → [子节点]({filename_map[child.commit_hash]})")

    if not nav_links:
        return ""

    return "\n\n" + "> [!nav] 节点导航\n" + "\n".join(nav_links)


def _generate_file_content(
    node: QuipuNode,
    engine: Engine,
    no_frontmatter: bool,
    no_nav: bool,
    exported_hashes_set: Set[str],
    filename_map: Dict[str, str],
    hidden_link_types: Set[str],
) -> str:
    """构建单个 Markdown 文件的完整内容。"""
    parts = []
    if not no_frontmatter:
        parts.append(_format_frontmatter(node))

    public_content = engine.reader.get_node_content(node) or ""
    parts.append("# content.md")
    parts.append(public_content.strip())

    private_content = engine.reader.get_private_data(node.commit_hash)
    if private_content:
        parts.append("# 开发者意图")
        parts.append(private_content.strip())

    content_str = "\n\n".join(parts)

    if not no_nav:
        navbar_str = _generate_navbar(node, exported_hashes_set, filename_map, hidden_link_types)
        content_str += navbar_str

    return content_str


def register(app: typer.Typer):
    @app.command(name="export")
    def export_command(
        ctx: typer.Context,
        work_dir: Annotated[
            Path, typer.Option("--work-dir", "-w", help="工作区根目录", resolve_path=True)
        ] = DEFAULT_WORK_DIR,
        output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="导出目录", resolve_path=True)] = Path(
            "./.quipu/export"
        ),
        limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="限制最新节点数量")] = None,
        since: Annotated[Optional[str], typer.Option("--since", help="起始时间戳 (YYYY-MM-DD HH:MM)")] = None,
        until: Annotated[Optional[str], typer.Option("--until", help="截止时间戳 (YYYY-MM-DD HH:MM)")] = None,
        zip_output: Annotated[bool, typer.Option("--zip", help="压缩导出目录")] = False,
        no_nav: Annotated[bool, typer.Option("--no-nav", help="禁用导航栏")] = False,
        no_frontmatter: Annotated[bool, typer.Option("--no-frontmatter", help="禁用 Frontmatter")] = False,
        hide_link_type: Annotated[
            Optional[List[str]],
            typer.Option(
                "--hide-link-type", help="禁用特定类型的导航链接 (可多次使用: summary, branch, parent, child)"
            ),
        ] = None,
    ):
        """将 Quipu 历史记录导出为一组人类可读的 Markdown 文件。"""
        hidden_types = set(hide_link_type) if hide_link_type else set()

        with engine_context(work_dir) as engine:
            if not engine.history_graph:
                bus.info("export.info.emptyHistory")
                ctx.exit(0)

            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                nodes_to_export = _filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                bus.error("export.error.badParam", error=str(e))
                ctx.exit(1)

            if not nodes_to_export:
                bus.info("export.info.noMatchingNodes")
                ctx.exit(0)

            if output_dir.exists() and any(output_dir.iterdir()):
                prompt = bus.get("export.prompt.overwrite", path=output_dir)
                if not prompt_for_confirmation(prompt, default=False):
                    bus.warning("common.prompt.cancel")
                    raise typer.Abort()
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            bus.info("export.info.starting", count=len(nodes_to_export), path=output_dir)

            # 预计算文件名和节点集合以供导航栏使用
            filename_map = {node.commit_hash: _generate_filename(node) for node in nodes_to_export}
            exported_hashes_set = {node.commit_hash for node in nodes_to_export}

            with typer.progressbar(nodes_to_export, label="导出进度") as progress:
                for node in progress:
                    filename = filename_map[node.commit_hash]
                    content = _generate_file_content(
                        node, engine, no_frontmatter, no_nav, exported_hashes_set, filename_map, hidden_types
                    )
                    (output_dir / filename).write_text(content, encoding="utf-8")

            if zip_output:
                bus.info("export.info.zipping")
                zip_path = shutil.make_archive(str(output_dir), "zip", output_dir)
                shutil.rmtree(output_dir)
                bus.success("export.success.zip", path=zip_path)
            else:
                bus.success("export.success.dir")
~~~~~

#### Acts 5: 重构 `ui.py`

替换硬编码输出。

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/commands/ui.py
~~~~~
~~~~~python
import logging
from pathlib import Path
from typing import Annotated

import typer

from .helpers import engine_context, _execute_visit
from ..config import DEFAULT_WORK_DIR, LOG_LEVEL
from ..factory import create_engine
from ..logger_config import configure_file_logging, setup_logging
from quipu.common.messaging import bus

logger = logging.getLogger(__name__)


def register(app: typer.Typer):
    @app.command()
    def ui(
        ctx: typer.Context,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        raw: Annotated[bool, typer.Option("--raw", help="默认以纯文本模式启动，禁用 Markdown 渲染。")] = False,
    ):
        """
        以交互式 TUI 模式显示 Quipu 历史图谱。
        """
        try:
            from ..tui import QuipuUiApp
        except ImportError:
            bus.error("ui.error.depMissing")
            bus.info("ui.info.depHint")
            ctx.exit(1)

        if LOG_LEVEL == "DEBUG":
            log_file = work_dir / ".quipu" / "tui.debug.log"
            configure_file_logging(log_file)
        else:
            setup_logging()  # Use standard stderr logging for INFO level and above

        logging.info("Starting Quipu UI command...")

        temp_engine = create_engine(work_dir, lazy=True)
        try:
            count = temp_engine.reader.get_node_count()
            if count == 0:
                bus.info("ui.info.emptyHistory")
                ctx.exit(0)
        finally:
            temp_engine.close()

        app_instance = QuipuUiApp(work_dir=work_dir, initial_raw_mode=raw)
        result = app_instance.run()

        if result:
            action, data = result
            if action == "checkout":
                target_hash = data
                with engine_context(work_dir) as action_engine:
                    bus.info("ui.info.checkoutRequest", short_hash=target_hash[:7])
                    _execute_visit(ctx, action_engine, target_hash, "navigation.info.navigating", short_hash=target_hash[:7])

            elif action == "dump":
                print(data)
                ctx.exit(0)
~~~~~

#### Acts 6: 更新测试 `test_export_command.py`

修改测试断言，使用 Mock `bus`。

~~~~~act
write_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
import pytest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, ANY

from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from tests.helpers import EMPTY_TREE_HASH


@pytest.fixture
def populated_history(engine_instance: Engine):
    """
    创建一个包含分支、总结节点的通用历史记录用于测试。
    History:
    - n0 (root) -> n1 -> n2 (branch point) -> n3a (branch A) -> n4 (summary)
                                          \\-> n3b (branch B)
    """
    engine = engine_instance
    ws = engine.root_dir
    (ws / "file.txt").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h0, "plan 0", summary_override="Root Node")
    (ws / "file.txt").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h0, h1, "plan 1", summary_override="Linear Node 1")
    (ws / "file.txt").write_text("v2")
    h2 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2, "plan 2", summary_override="Branch Point")
    engine.visit(h2)
    (ws / "branch_a.txt").touch()
    h3a = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2, h3a, "plan 3a", summary_override="Branch A change")
    engine.visit(h3a)
    engine.create_plan_node(h3a, h3a, "plan 4", summary_override="Summary Node")
    engine.visit(h2)
    (ws / "branch_b.txt").touch()
    h3b = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2, h3b, "plan 3b", summary_override="Branch B change")
    return engine


@pytest.fixture
def history_for_all_links(engine_instance: Engine):
    """
    创建一个复杂的历史记录，确保特定节点拥有所有类型的导航链接。
    Node n3 will have: a parent (n2b), a child (n4), an ancestor branch point (n1),
    and an ancestor summary node (n_summary).
    """
    engine = engine_instance
    ws = engine.root_dir
    engine.create_plan_node(EMPTY_TREE_HASH, EMPTY_TREE_HASH, "plan sum", summary_override="Ancestor_Summary")
    (ws / "f").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h0, "plan 0", summary_override="Root")
    (ws / "f").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h0, h1, "plan 1", summary_override="Branch_Point")
    engine.visit(h1)
    (ws / "a").touch()
    h2a = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2a, "plan 2a", summary_override="Branch_A")
    engine.visit(h1)
    (ws / "b").touch()
    h2b = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2b, "plan 2b", summary_override="Parent_Node")
    engine.visit(h2b)
    (ws / "c").touch()
    h3 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2b, h3, "plan 3", summary_override="Test_Target_Node")
    engine.visit(h3)
    (ws / "d").touch()
    h4 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h3, h4, "plan 4", summary_override="Child_Node")
    return engine


def test_export_basic(runner, populated_history, monkeypatch):
    """测试基本的导出功能。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])
    
    assert result.exit_code == 0
    mock_bus.success.assert_called_once_with("export.success.dir")
    
    assert output_dir.exists()
    files = list(output_dir.glob("*.md"))
    assert len(files) == 6
    target_file = next((f for f in files if "Branch_A_change" in f.name), None)
    assert target_file is not None
    content = target_file.read_text()
    assert content.startswith("---") and "> [!nav] 节点导航" in content


def test_export_filtering(runner, populated_history, monkeypatch):
    """测试过滤选项。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_filter"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "-n", "2"])
    
    assert result.exit_code == 0
    mock_bus.success.assert_called_once_with("export.success.dir")
    assert len(list(output_dir.glob("*.md"))) == 2


def test_export_edge_cases(runner, quipu_workspace, monkeypatch):
    """测试边界情况。"""
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    # Empty history
    result = runner.invoke(app, ["export", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("export.info.emptyHistory")

    # No matching nodes
    (work_dir / "f").touch()
    engine.capture_drift(engine.git_db.get_tree_hash())
    
    # Reset mock for second call
    mock_bus.reset_mock()
    
    result = runner.invoke(app, ["export", "-w", str(work_dir), "--since", "2099-01-01 00:00"])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("export.info.noMatchingNodes")


def test_export_no_frontmatter(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_fm"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-frontmatter", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert not a_file.read_text().startswith("---")


def test_export_no_nav(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_nav"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-nav", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert "> [!nav] 节点导航" not in a_file.read_text()


def test_export_zip(runner, populated_history, monkeypatch):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_zip"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--zip"])
    
    assert result.exit_code == 0
    mock_bus.info.assert_any_call("export.info.zipping")
    mock_bus.success.assert_called_with("export.success.zip", path=ANY)
    
    zip_path = output_dir.with_suffix(".zip")
    assert not output_dir.exists() and zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert len(zf.namelist()) == 6


@pytest.mark.parametrize(
    "link_type_to_hide, text_not_expected, text_still_expected",
    [
        ("summary", "↑ [总结节点]", "↓ [上一分支点]"),
        ("branch", "↓ [上一分支点]", "← [父节点]"),
        ("parent", "← [父节点]", "→ [子节点]"),
        ("child", "→ [子节点]", "↑ [总结节点]"),
    ],
)
def test_export_hide_link_type(
    runner, history_for_all_links, link_type_to_hide, text_not_expected, text_still_expected, monkeypatch
):
    """验证 --hide-link-type 选项能成功禁用特定类型的导航链接。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_links"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(
        app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--hide-link-type", link_type_to_hide]
    )
    assert result.exit_code == 0
    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()
    assert text_not_expected not in content
    assert text_still_expected in content


def test_export_hide_multiple_link_types(runner, history_for_all_links, monkeypatch):
    """验证可以同时禁用多种链接类型。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_multi"
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.export.bus", mock_bus)

    result = runner.invoke(
        app,
        [
            "export",
            "-w",
            str(engine.root_dir),
            "-o",
            str(output_dir),
            "--hide-link-type",
            "summary",
            "--hide-link-type",
            "child",
        ],
    )
    assert result.exit_code == 0
    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()
    assert "↑ [总结节点]" not in content and "→ [子节点]" not in content
    assert "↓ [上一分支点]" in content and "← [父节点]" in content
~~~~~

### 下一步建议
我们已经完成了绝大多数命令的重构。下一步是“清理与收尾”阶段。建议全局搜索整个 `packages/quipu-cli`，检查是否还有遗漏的 `typer.secho/echo` 调用。特别是可以关注一下 `ui_utils.py` 中的提示逻辑是否也可以进一步使用 `bus.get()` 进行国际化。
