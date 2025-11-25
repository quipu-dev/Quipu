# feat: Implement robust history query API and CLI command

## 用户需求
在自动化测试中，为了获取特定历史节点的哈希以进行 `checkout` 操作，当前实现依赖于一个脆弱的方法：`git log --grep="<summary_string>"`。这种方法严重依赖摘要 (summary) 的具体内容和唯一性，一旦摘要的生成逻辑发生变化，测试就可能失败，这降低了测试的稳定性和可靠性。

## 评论
这是一个关键的开发者体验 (DX) 改进。为系统提供一个稳定、健壮的编程接口来查询历史记录，不仅能解决当前测试的脆弱性问题，还能为未来的自动化脚本和高级功能 (如基于内容的搜索) 奠定基础。

## 目标
1.  在 `quipu-engine` 的 `Engine` 类中实现一个新的 `find_nodes` 方法，提供基于摘要 (正则表达式)、节点类型等条件的查询功能。
2.  在 `quipu-cli` 中新增一个 `quipu find` 命令，将 `Engine` 的查询能力暴露给用户。
3.  重构 `tests/test_storage_integration.py` 测试用例，使用新的 `find_nodes` API 替代不稳定的 `git log --grep` 调用。
4.  为新的 `find` 命令和 `find_nodes` 方法添加专门的测试用例，确保其功能正确。

## 基本原理
本次重构的核心是在 `Engine` 状态机中添加一个查询层。`Engine` 实例在 `align` 之后，内存中持有完整的历史图谱 (`self.history_graph`)。`find_nodes` 方法将直接在此数据结构上进行过滤、排序和限制数量，这是一个高效且与存储后端解耦的实现。

新的 `quipu find` 命令将作为这个查询 API 的前端，负责解析用户参数，调用 `Engine` 方法，并格式化输出结果，为用户和脚本提供一个一致且可靠的交互界面。

## 标签
#comp/engine #comp/cli #comp/tests #scope/api #scope/dx

---

## Script

### Acts 1: 在 Engine 中实现 find_nodes API

首先，我们在 `Engine` 类中添加核心的查询逻辑。这个方法将成为所有历史查询功能的基础。

~~~~~act
write_file packages/quipu-engine/src/quipu/core/state_machine.py
~~~~~

~~~~~python
import logging
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from .git_db import GitDB
from .config import ConfigManager
from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader, HistoryWriter

logger = logging.getLogger(__name__)


class Engine:
    """
    Axon 状态引擎。
    负责协调 Git 物理状态和 Axon 逻辑图谱。
    """

    def _sync_persistent_ignores(self):
        """将 config.yml 中的持久化忽略规则同步到 .git/info/exclude。"""
        try:
            config = ConfigManager(self.root_dir)
            patterns = config.get("sync.persistent_ignores", [])
            if not patterns:
                return

            exclude_file = self.root_dir / ".git" / "info" / "exclude"
            exclude_file.parent.mkdir(exist_ok=True)

            header = "# --- Managed by Quipu ---"
            footer = "# --- End Managed by Quipu ---"

            content = ""
            if exclude_file.exists():
                content = exclude_file.read_text("utf-8")

            managed_block_pattern = re.compile(rf"{re.escape(header)}.*{re.escape(footer)}", re.DOTALL)

            new_block = f"{header}\n" + "\n".join(patterns) + f"\n{footer}"

            new_content, count = managed_block_pattern.subn(new_block, content)
            if count == 0:
                if content and not content.endswith("\n"):
                    content += "\n"
                new_content = content + "\n" + new_block + "\n"

            if new_content != content:
                exclude_file.write_text(new_content, "utf-8")
                logger.debug("✅ .git/info/exclude 已更新。")

        except Exception as e:
            logger.warning(f"⚠️  无法同步持久化忽略规则: {e}")

    def __init__(self, root_dir: Path, reader: HistoryReader, writer: HistoryWriter):
        self.root_dir = root_dir.resolve()
        self.quipu_dir = self.root_dir / ".quipu"
        self.quipu_dir.mkdir(exist_ok=True)  # 确保 .quipu 目录存在
        self.history_dir = self.quipu_dir / "history"
        self.head_file = self.quipu_dir / "HEAD"

        self.nav_log_file = self.quipu_dir / "nav_log"
        self.nav_ptr_file = self.quipu_dir / "nav_ptr"

        quipu_gitignore = self.quipu_dir / ".gitignore"
        if not quipu_gitignore.exists():
            try:
                quipu_gitignore.write_text("*\n", encoding="utf-8")
            except Exception as e:
                logger.warning(f"无法创建隔离文件 {quipu_gitignore}: {e}")

        self.git_db = GitDB(self.root_dir)
        self.reader = reader
        self.writer = writer
        self.history_graph: Dict[str, QuipuNode] = {}
        self.current_node: Optional[QuipuNode] = None

        self._sync_persistent_ignores()

    def _read_head(self) -> Optional[str]:
        if self.head_file.exists():
            return self.head_file.read_text(encoding="utf-8").strip()
        return None

    def _write_head(self, tree_hash: str):
        try:
            self.head_file.write_text(tree_hash, encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️  无法更新 HEAD 指针: {e}")

    def _read_nav(self) -> Tuple[List[str], int]:
        log = []
        ptr = -1
        if self.nav_log_file.exists():
            try:
                content = self.nav_log_file.read_text(encoding="utf-8").strip()
                if content:
                    log = content.splitlines()
            except Exception: pass
        if self.nav_ptr_file.exists():
            try:
                ptr = int(self.nav_ptr_file.read_text(encoding="utf-8").strip())
            except Exception: pass
        if not log:
            ptr = -1
        elif ptr < 0:
            ptr = 0
        elif ptr >= len(log):
            ptr = len(log) - 1
        return log, ptr

    def _write_nav(self, log: List[str], ptr: int):
        try:
            self.nav_log_file.write_text("\n".join(log), encoding="utf-8")
            self.nav_ptr_file.write_text(str(ptr), encoding="utf-8")
        except Exception as e:
            logger.warning(f"⚠️  无法更新导航历史: {e}")

    def _append_nav(self, tree_hash: str):
        log, ptr = self._read_nav()
        if not log:
            current_head = self._read_head()
            if current_head and current_head != tree_hash:
                log.append(current_head)
                ptr = 0
        if ptr < len(log) - 1:
            log = log[:ptr + 1]
        if log and log[-1] == tree_hash:
            ptr = len(log) - 1
            self._write_nav(log, ptr)
            return
        log.append(tree_hash)
        ptr = len(log) - 1
        MAX_LOG_SIZE = 100
        if len(log) > MAX_LOG_SIZE:
            log = log[-MAX_LOG_SIZE:]
            ptr = len(log) - 1
        self._write_nav(log, ptr)

    def visit(self, target_hash: str):
        self.checkout(target_hash)
        self._append_nav(target_hash)

    def back(self) -> Optional[str]:
        log, ptr = self._read_nav()
        if ptr > 0:
            new_ptr = ptr - 1
            target_hash = log[new_ptr]
            logger.info(f"🔙 Back to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def forward(self) -> Optional[str]:
        log, ptr = self._read_nav()
        if ptr < len(log) - 1:
            new_ptr = ptr + 1
            target_hash = log[new_ptr]
            logger.info(f"🔜 Forward to: {target_hash[:7]} (History: {new_ptr + 1}/{len(log)})")
            self.checkout(target_hash)
            self._write_nav(log, new_ptr)
            return target_hash
        return None

    def align(self) -> str:
        all_nodes = self.reader.load_all_nodes()
        final_graph: Dict[str, QuipuNode] = {}
        for node in all_nodes:
            if node.output_tree not in final_graph or \
               node.timestamp > final_graph[node.output_tree].timestamp:
                final_graph[node.output_tree] = node
        self.history_graph = final_graph
        if all_nodes:
            logger.info(f"从存储中加载了 {len(all_nodes)} 个历史事件，形成 {len(final_graph)} 个唯一状态节点。")

        current_hash = self.git_db.get_tree_hash()
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
            self.current_node = None
            return "CLEAN"

        if current_hash in self.history_graph:
            self.current_node = self.history_graph[current_hash]
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            self._write_head(current_hash)
            return "CLEAN"

        logger.warning(f"⚠️  状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        if not self.history_graph:
            return "ORPHAN"
        return "DIRTY"

    def find_nodes(
        self,
        summary_regex: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[QuipuNode]:
        """
        在历史图谱中查找符合条件的节点。

        Args:
            summary_regex: 用于匹配节点摘要的正则表达式。
            node_type: 节点类型 ('plan' 或 'capture')。
            limit: 返回的最大节点数量。

        Returns:
            符合条件的节点列表，按时间戳降序排列。
        """
        candidates = list(self.history_graph.values())
        
        if summary_regex:
            try:
                pattern = re.compile(summary_regex, re.IGNORECASE)
                candidates = [node for node in candidates if pattern.search(node.summary)]
            except re.error as e:
                logger.error(f"无效的正则表达式: {summary_regex} ({e})")
                return []
        
        if node_type:
            candidates = [node for node in candidates if node.node_type == node_type]
            
        # 按时间戳降序排序
        candidates.sort(key=lambda n: n.timestamp, reverse=True)
        
        return candidates[:limit]

    def capture_drift(self, current_hash: str, message: Optional[str] = None) -> QuipuNode:
        log_message = f"📸 正在捕获工作区漂移 (Message: {message})" if message else "📸 正在捕获工作区漂移"
        logger.info(f"{log_message}，新状态 Hash: {current_hash[:7]}")

        genesis_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        input_hash = genesis_hash
        head_hash = self._read_head()
        if head_hash and head_hash in self.history_graph:
            input_hash = head_hash
        elif self.history_graph:
            last_node = max(self.history_graph.values(), key=lambda node: node.timestamp)
            input_hash = last_node.output_tree
            logger.warning(f"⚠️  丢失 HEAD 指针，自动回退到最新历史节点: {input_hash[:7]}")

        diff_summary = self.git_db.get_diff_stat(input_hash, current_hash)
        user_message_section = f"### 💬 备注:\n{message}\n\n" if message else ""
        body = (
            f"# 📸 Snapshot Capture\n\n"
            f"{user_message_section}"
            f"检测到工作区发生变更。\n\n"
            f"### 📝 变更文件摘要:\n```\n{diff_summary}\n```"
        )

        new_node = self.writer.create_node(
            node_type="capture",
            input_tree=input_hash,
            output_tree=current_hash,
            content=body,
            message=message
        )

        self.history_graph[current_hash] = new_node
        self.current_node = new_node
        self._write_head(current_hash)
        self._append_nav(current_hash)

        logger.info(f"✅ 捕获完成，新节点已创建: {new_node.filename.name}")
        return new_node

    def create_plan_node(self, input_tree: str, output_tree: str, plan_content: str) -> QuipuNode:
        if input_tree == output_tree:
            logger.info(f"📝 记录幂等操作节点 (Idempotent Node): {output_tree[:7]}")
        else:
            logger.info(f"📝 正在记录 Plan 节点: {input_tree[:7]} -> {output_tree[:7]}")

        new_node = self.writer.create_node(
            node_type="plan",
            input_tree=input_tree,
            output_tree=output_tree,
            content=plan_content
        )

        self.history_graph[output_tree] = new_node
        self.current_node = new_node
        self._write_head(output_tree)
        self._append_nav(output_tree)

        logger.info(f"✅ Plan 已归档: {new_node.filename.name}")
        return new_node

    def checkout(self, target_hash: str):
        self.git_db.checkout_tree(target_hash)
        self._write_head(target_hash)
        if target_hash in self.history_graph:
            self.current_node = self.history_graph[target_hash]
        logger.info(f"🔄 状态已切换至: {target_hash[:7]}")
~~~~~

### Acts 2: 在 CLI 中添加 find 命令

现在我们将 `Engine` 的查询能力封装成一个新的 `quipu find` 命令，并提供友好的格式化输出。

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~python
import typer
import logging
import sys
import click # 导入 click 库
from pathlib import Path
from typing import Annotated, Optional, Dict

from .logger_config import setup_logging
from .controller import run_quipu
from .config import DEFAULT_WORK_DIR, DEFAULT_ENTRY_FILE, PROJECT_ROOT
from .factory import create_engine, resolve_root, find_project_root # 导入工厂方法
from quipu.core.plugin_loader import load_plugins
from quipu.core.executor import Executor
from quipu.core.state_machine import Engine
from quipu.core.models import QuipuNode
from quipu.core.git_db import GitDB
import inspect
import subprocess
from quipu.core.config import ConfigManager


# 注意：不要在模块级别直接调用 setup_logging()，
# 否则会导致 CliRunner 测试中的 I/O 流过早绑定/关闭问题。
logger = logging.getLogger(__name__)

app = typer.Typer(add_completion=False, name="quipu")

def _prompt_for_confirmation(message: str, default: bool = False) -> bool:
    """
    使用单字符输入请求用户确认，无需回车。
    """
    prompt_suffix = " [Y/n]: " if default else " [y/N]: "
    typer.secho(message + prompt_suffix, nl=False, err=True)
    
    # click.getchar() 不适用于非 TTY 环境 (如 CI/CD 或管道)
    # 在这种情况下，我们回退到 False，强制使用 --force
    if not sys.stdin.isatty():
        typer.echo(" (non-interactive)", err=True)
        return False # 在非交互环境中，安全起见总是拒绝

    char = click.getchar()
    click.echo(char, err=True) # 回显用户输入

    if char.lower() == 'y':
        return True
    if char.lower() == 'n':
        return False
    
    # 对于回车或其他键，返回默认值
    return default

# --- 导航命令辅助函数 ---
def _find_current_node(engine: Engine, graph: Dict[str, QuipuNode]) -> Optional[QuipuNode]:
    """在图中查找与当前工作区状态匹配的节点"""
    current_hash = engine.git_db.get_tree_hash()
    node = graph.get(current_hash)
    if not node:
        typer.secho("⚠️  当前工作区状态未在历史中找到，或存在未保存的变更。", fg=typer.colors.YELLOW, err=True)
        typer.secho("💡  请先运行 'quipu save' 创建一个快照，再进行导航。", fg=typer.colors.YELLOW, err=True)
    return node

def _execute_visit(ctx: typer.Context, engine: Engine, target_hash: str, description: str):
    """辅助函数：执行 engine.visit 并处理结果"""
    typer.secho(f"🚀 {description}", err=True)
    try:
        engine.visit(target_hash)
        typer.secho(f"✅ 已成功切换到状态 {target_hash[:7]}。", fg=typer.colors.GREEN, err=True)
    except Exception as e:
        typer.secho(f"❌ 导航操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)

# --- 核心命令 ---

@app.command()
def ui(
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
):
    """
    以交互式 TUI 模式显示 Axon 历史图谱。
    """
    try:
        from .tui import QuipuUiApp
    except ImportError:
        typer.secho("❌ TUI 依赖 'textual' 未安装。", fg=typer.colors.RED, err=True)
        typer.secho("💡 请运行: pip install 'textual>=0.58.0'", err=True)
        ctx.exit(1)
        
    setup_logging()
    
    engine = create_engine(work_dir)
    all_nodes = engine.reader.load_all_nodes()
    
    if not all_nodes:
        typer.secho("📜 历史记录为空，无需启动 UI。", fg=typer.colors.YELLOW, err=True)
        ctx.exit(0)
        
    graph = engine.history_graph
    current_hash = engine.git_db.get_tree_hash()
    
    app_instance = QuipuUiApp(all_nodes, current_hash=current_hash)
    selected_hash = app_instance.run()

    if selected_hash:
        if selected_hash in graph:
            typer.secho(f"\n> TUI 请求检出到: {selected_hash[:7]}", err=True)
            _execute_visit(ctx, engine, selected_hash, f"正在导航到 TUI 选定节点: {selected_hash[:7]}")
        else:
            typer.secho(f"❌ 错误: 无法在历史图谱中找到目标哈希 {selected_hash[:7]}", fg=typer.colors.RED, err=True)
            ctx.exit(1)


@app.command()
def save(
    ctx: typer.Context,
    message: Annotated[Optional[str], typer.Argument(help="本次快照的简短描述。")] = None,
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
):
    """
    捕获当前工作区的状态，创建一个“微提交”快照。
    """
    setup_logging()
    engine = create_engine(work_dir)
    # create_engine 内部已经调用了 align
    
    # 判断是否 clean
    status = "DIRTY"
    if engine.current_node:
        current_tree_hash = engine.git_db.get_tree_hash()
        if engine.current_node.output_tree == current_tree_hash:
            status = "CLEAN"
            
    if status == "CLEAN":
        typer.secho("✅ 工作区状态未发生变化，无需创建快照。", fg=typer.colors.GREEN, err=True)
        ctx.exit(0)
        
    current_hash = engine.git_db.get_tree_hash()
    try:
        node = engine.capture_drift(current_hash, message=message)
        msg_suffix = f' ({message})' if message else ''
        typer.secho(f"📸 快照已保存: {node.short_hash}{msg_suffix}", fg=typer.colors.GREEN, err=True)
    except Exception as e:
        typer.secho(f"❌ 创建快照失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)

@app.command(name="find")
def find_command(
    ctx: typer.Context,
    summary_regex: Annotated[Optional[str], typer.Option("--summary", "-s", help="用于匹配节点摘要的正则表达式 (不区分大小写)。")] = None,
    node_type: Annotated[Optional[str], typer.Option("--type", "-t", help="节点类型 ('plan' 或 'capture')。")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="返回的最大结果数量。")] = 10,
    work_dir: Annotated[Path, typer.Option("--work-dir", "-w", help="工作区根目录。")] = DEFAULT_WORK_DIR,
):
    """
    根据条件查找历史节点。
    """
    setup_logging()
    engine = create_engine(work_dir)
    
    if not engine.history_graph:
        typer.secho("📜 历史记录为空。", fg=typer.colors.YELLOW, err=True)
        ctx.exit(0)
        
    nodes = engine.find_nodes(summary_regex=summary_regex, node_type=node_type, limit=limit)
    
    if not nodes:
        typer.secho("🤷 未找到符合条件的历史节点。", fg=typer.colors.YELLOW, err=True)
        ctx.exit(0)
        
    typer.secho("--- 查找结果 ---", bold=True, err=True)
    for node in nodes:
        ts = node.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        color = typer.colors.CYAN if node.node_type == "plan" else typer.colors.MAGENTA
        tag = f"[{node.node_type.upper()}]"
        # 直接打印 output_tree hash，因为这是节点的唯一标识符
        typer.secho(f"{ts} {tag:<9} {node.output_tree}", fg=color, nl=False, err=True)
        typer.echo(f" - {node.summary}", err=True)

@app.command()
def sync(
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
    remote: Annotated[Optional[str], typer.Option("--remote", "-r", help="Git 远程仓库的名称 (覆盖配置文件)。")] = None,
):
    """
    与远程仓库同步 Axon 历史图谱。
    """
    setup_logging()
    work_dir = resolve_root(work_dir) # Sync needs root
    config = ConfigManager(work_dir)
    if remote is None:
        remote = config.get("sync.remote_name", "origin")
    refspec = "refs/quipu/history:refs/quipu/history"
    def run_git_command(args: list[str]):
        try:
            result = subprocess.run(["git"] + args, cwd=work_dir, capture_output=True, text=True, check=True)
            if result.stdout: typer.echo(result.stdout, err=True)
            if result.stderr: typer.echo(result.stderr, err=True)
        except subprocess.CalledProcessError as e:
            typer.secho(f"❌ Git 命令执行失败: git {' '.join(args)}", fg=typer.colors.RED, err=True)
            typer.secho(e.stderr, fg=typer.colors.YELLOW, err=True)
            ctx.exit(1)
        except FileNotFoundError:
            typer.secho("❌ 错误: 未找到 'git' 命令。", fg=typer.colors.RED, err=True)
            ctx.exit(1)
    typer.secho(f"⬇️  正在从 '{remote}' 拉取 Axon 历史...", fg=typer.colors.BLUE, err=True)
    run_git_command(["fetch", remote, refspec])
    typer.secho(f"⬆️  正在向 '{remote}' 推送 Axon 历史...", fg=typer.colors.BLUE, err=True)
    run_git_command(["push", remote, refspec])
    typer.secho("\n✅ Axon 历史同步完成。", fg=typer.colors.GREEN, err=True)
    config_get_res = subprocess.run(["git", "config", "--get", f"remote.{remote}.fetch"], cwd=work_dir, capture_output=True, text=True)
    if refspec not in config_get_res.stdout:
        typer.secho("\n💡 提示: 为了让 `git pull` 自动同步 Axon 历史，请执行以下命令:", fg=typer.colors.YELLOW, err=True)
        typer.echo(f'  git config --add remote.{remote}.fetch "{refspec}"')

@app.command()
def discard(
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
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="强制执行，跳过确认提示。")
    ] = False,
):
    """
    丢弃工作区所有未记录的变更，恢复到上一个干净状态。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    if not graph:
        typer.secho("❌ 错误: 找不到任何历史记录，无法确定要恢复到哪个状态。", fg=typer.colors.RED, err=True)
        ctx.exit(1)
    
    target_tree_hash = engine._read_head()
    if not target_tree_hash or target_tree_hash not in graph:
        latest_node = max(graph.values(), key=lambda n: n.timestamp)
        target_tree_hash = latest_node.output_tree
        typer.secho(f"⚠️  HEAD 指针丢失或无效，将恢复到最新历史节点: {latest_node.short_hash}", fg=typer.colors.YELLOW, err=True)
    else:
        latest_node = graph[target_tree_hash]

    current_hash = engine.git_db.get_tree_hash()
    if current_hash == target_tree_hash:
        typer.secho(f"✅ 工作区已经是干净状态 ({latest_node.short_hash})，无需操作。", fg=typer.colors.GREEN, err=True)
        ctx.exit(0)

    diff_stat = engine.git_db.get_diff_stat(target_tree_hash, current_hash)
    typer.secho("\n以下是即将被丢弃的变更:", fg=typer.colors.YELLOW, err=True)
    typer.secho("-" * 20, err=True)
    typer.echo(diff_stat, err=True)
    typer.secho("-" * 20, err=True)

    if not force:
        prompt = f"🚨 即将丢弃上述所有变更，并恢复到状态 {latest_node.short_hash}。\n此操作不可逆。是否继续？"
        if not _prompt_for_confirmation(prompt, default=False):
            typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
            raise typer.Abort()

    try:
        engine.visit(target_tree_hash)
        typer.secho(f"✅ 工作区已成功恢复到节点 {latest_node.short_hash}。", fg=typer.colors.GREEN, err=True)
    except Exception as e:
        typer.secho(f"❌ 恢复状态失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)

@app.command()
def checkout(
    ctx: typer.Context,
    hash_prefix: Annotated[str, typer.Argument(help="目标状态节点的哈希前缀。")],
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
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="强制执行，跳过确认提示。")
    ] = False,
):
    """
    将工作区恢复到指定的历史节点状态。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    
    matches = [node for sha, node in graph.items() if sha.startswith(hash_prefix)]
    if not matches:
        typer.secho(f"❌ 错误: 未找到哈希前缀为 '{hash_prefix}' 的历史节点。", fg=typer.colors.RED, err=True)
        ctx.exit(1)
    if len(matches) > 1:
        typer.secho(f"❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {len(matches)} 个节点。", fg=typer.colors.RED, err=True)
        ctx.exit(1)
    target_node = matches[0]
    target_tree_hash = target_node.output_tree
    
    current_hash = engine.git_db.get_tree_hash()
    if current_hash == target_tree_hash:
        typer.secho(f"✅ 工作区已处于目标状态 ({target_node.short_hash})，无需操作。", fg=typer.colors.GREEN, err=True)
        ctx.exit(0)

    is_dirty = engine.current_node is None or engine.current_node.output_tree != current_hash
    if is_dirty:
        typer.secho("⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...", fg=typer.colors.YELLOW, err=True)
        engine.capture_drift(current_hash)
        typer.secho("✅ 变更已捕获。", fg=typer.colors.GREEN, err=True)
        current_hash = engine.git_db.get_tree_hash()

    diff_stat = engine.git_db.get_diff_stat(current_hash, target_tree_hash)
    if diff_stat:
        typer.secho("\n以下是将要发生的变更:", fg=typer.colors.YELLOW, err=True)
        typer.secho("-" * 20, err=True)
        typer.echo(diff_stat, err=True)
        typer.secho("-" * 20, err=True)

    if not force:
        prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
        if not _prompt_for_confirmation(prompt, default=False):
            typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
            raise typer.Abort()

    _execute_visit(ctx, engine, target_tree_hash, f"正在导航到节点: {target_node.short_hash}")

# --- 结构化导航命令 ---
@app.command()
def undo(
    ctx: typer.Context,
    count: Annotated[int, typer.Option("--count", "-n", help="向上移动的步数。")] = 1,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [结构化导航] 向上移动到当前状态的父节点。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    current_node = _find_current_node(engine, graph)
    if not current_node: ctx.exit(1)
    target_node = current_node
    for i in range(count):
        if not target_node.parent:
            msg = f"已到达历史根节点 (移动了 {i} 步)。" if i > 0 else "已在历史根节点。"
            typer.secho(f"✅ {msg}", fg=typer.colors.GREEN, err=True)
            if target_node == current_node: ctx.exit(0)
            break
        target_node = target_node.parent
    
    _execute_visit(ctx, engine, target_node.output_tree, f"正在撤销到父节点: {target_node.short_hash}")

@app.command()
def redo(
    ctx: typer.Context,
    count: Annotated[int, typer.Option("--count", "-n", help="向下移动的步数。")] = 1,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [结构化导航] 向下移动到子节点 (默认最新)。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    current_node = _find_current_node(engine, graph)
    if not current_node: ctx.exit(1)
    target_node = current_node
    for i in range(count):
        if not target_node.children:
            msg = f"已到达分支末端 (移动了 {i} 步)。" if i > 0 else "已在分支末端。"
            typer.secho(f"✅ {msg}", fg=typer.colors.GREEN, err=True)
            if target_node == current_node: ctx.exit(0)
            break
        target_node = target_node.children[-1]
        if len(current_node.children) > 1:
            typer.secho(f"💡 当前节点有多个分支，已自动选择最新分支 -> {target_node.short_hash}", fg=typer.colors.YELLOW, err=True)
    
    _execute_visit(ctx, engine, target_node.output_tree, f"正在重做到子节点: {target_node.short_hash}")

@app.command()
def prev(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [结构化导航] 切换到上一个兄弟分支。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    current_node = _find_current_node(engine, graph)
    if not current_node: ctx.exit(1)
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
        _execute_visit(ctx, engine, target_node.output_tree, f"正在切换到上一个兄弟节点: {target_node.short_hash}")
    except ValueError: pass

@app.command()
def next(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [结构化导航] 切换到下一个兄弟分支。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph
    current_node = _find_current_node(engine, graph)
    if not current_node: ctx.exit(1)
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
        _execute_visit(ctx, engine, target_node.output_tree, f"正在切换到下一个兄弟节点: {target_node.short_hash}")
    except ValueError: pass

# --- 时序性导航命令 (新增) ---

@app.command()
def back(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [时序性导航] 后退：回到上一次访问的历史状态。
    """
    setup_logging()
    engine = create_engine(work_dir)
    
    try:
        result_hash = engine.back()
        if result_hash:
            typer.secho(f"✅ 已后退到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
        else:
            typer.secho("⚠️  已到达访问历史的起点。", fg=typer.colors.YELLOW, err=True)
    except Exception as e:
        typer.secho(f"❌ 后退操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)

@app.command()
def forward(
    ctx: typer.Context,
    work_dir: Annotated[
        Path,
        typer.Option("--work-dir", "-w", help="工作区根目录。")
    ] = DEFAULT_WORK_DIR,
):
    """
    [时序性导航] 前进：撤销后退操作。
    """
    setup_logging()
    engine = create_engine(work_dir)
    
    try:
        result_hash = engine.forward()
        if result_hash:
            typer.secho(f"✅ 已前进到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
        else:
            typer.secho("⚠️  已到达访问历史的终点。", fg=typer.colors.YELLOW, err=True)
    except Exception as e:
        typer.secho(f"❌ 前进操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)


@app.command()
def log(
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
):
    """
    显示 Axon 历史图谱日志。
    """
    setup_logging()
    engine = create_engine(work_dir)
    graph = engine.history_graph

    if not graph:
        typer.secho("📜 历史记录为空。", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(0)
    nodes = sorted(graph.values(), key=lambda n: n.timestamp, reverse=True)
    typer.secho("--- Axon History Log ---", bold=True, err=True)
    for node in nodes:
        ts = node.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        color = typer.colors.CYAN if node.node_type == "plan" else typer.colors.MAGENTA
        tag = f"[{node.node_type.upper()}]"
        summary = node.summary # Use the authoritative summary from the node object
        typer.secho(f"{ts} {tag:<9} {node.short_hash}", fg=color, nl=False, err=True)
        typer.echo(f" - {summary}", err=True)

@app.command(name="run")
def run_command(
    ctx: typer.Context,
    file: Annotated[
        Optional[Path], 
        typer.Argument(help=f"包含 Markdown 指令的文件路径。", resolve_path=True)
    ] = None,
    work_dir: Annotated[
        Path, 
        typer.Option("--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True)
    ] = DEFAULT_WORK_DIR,
    parser_name: Annotated[str, typer.Option("--parser", "-p", help=f"选择解析器语法。默认为 'auto'。")] = "auto",
    yolo: Annotated[bool, typer.Option("--yolo", "-y", help="跳过所有确认步骤，直接执行 (You Only Look Once)。")] = False,
    list_acts: Annotated[bool, typer.Option("--list-acts", "-l", help="列出所有可用的操作指令及其说明。")] = False
):
    """
    Axon: 执行 Markdown 文件中的操作指令。
    """
    setup_logging()
    if list_acts:
        executor = Executor(root_dir=Path("."), yolo=True)
        from quipu.acts import register_core_acts
        register_core_acts(executor)
        typer.secho("\n📋 可用的 Axon 指令列表:\n", fg=typer.colors.GREEN, bold=True, err=True)
        acts = executor.get_registered_acts()
        for name in sorted(acts.keys()):
            doc = acts[name]
            clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
            indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
            typer.secho(f"🔹 {name}", fg=typer.colors.CYAN, bold=True, err=True)
            typer.echo(f"{indented_doc}\n", err=True)
        ctx.exit(0)
    content = ""; source_desc = ""
    if file:
        if not file.exists(): typer.secho(f"❌ 错误: 找不到指令文件: {file}", fg=typer.colors.RED, err=True); ctx.exit(1)
        if not file.is_file(): typer.secho(f"❌ 错误: 路径不是文件: {file}", fg=typer.colors.RED, err=True); ctx.exit(1)
        content = file.read_text(encoding="utf-8"); source_desc = f"文件 ({file.name})"
    elif not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read()
            if stdin_content: content = stdin_content; source_desc = "STDIN (管道流)"
        except Exception: pass
    if not content and DEFAULT_ENTRY_FILE.exists():
        content = DEFAULT_ENTRY_FILE.read_text(encoding="utf-8"); source_desc = f"默认文件 ({DEFAULT_ENTRY_FILE.name})"
    if file and not file.exists() and file.name in ["log", "checkout", "sync", "init", "ui", "find"]:
        typer.secho(f"❌ 错误: 找不到指令文件: {file}", fg=typer.colors.RED, err=True)
        typer.secho(f"💡 提示: 你是不是想执行 'quipu {file.name}' 命令？", fg=typer.colors.YELLOW, err=True)
        ctx.exit(1)
    if not content.strip():
        if not file:
            typer.secho(f"⚠️  提示: 未提供输入，且当前目录下未找到默认文件 '{DEFAULT_ENTRY_FILE.name}'。", fg=typer.colors.YELLOW, err=True)
            typer.echo("\n用法示例:", err=True); typer.echo("  quipu run my_plan.md", err=True); typer.echo("  echo '...' | quipu run", err=True)
            ctx.exit(0)
    logger.info(f"已加载指令源: {source_desc}"); logger.info(f"工作区根目录: {work_dir}")
    if yolo: logger.warning("⚠️  YOLO 模式已开启：将自动确认所有修改。")
    result = run_quipu(content=content, work_dir=work_dir, parser_name=parser_name, yolo=yolo)
    if result.message:
        color = typer.colors.GREEN if result.success else typer.colors.RED
        typer.secho(f"\n{result.message}", fg=color, err=True)
    if result.data: typer.echo(result.data)
    ctx.exit(result.exit_code)



if __name__ == "__main__":
    app()
~~~~~

### Acts 3: 添加并完善相关测试

现在，我们需要为新功能添加测试。首先测试 `Engine` 的 `find_nodes` API，然后测试 `quipu find` CLI 命令，最后重构依赖 `git log` 的旧测试。

~~~~~act
write_file tests/test_engine.py
~~~~~

~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from quipu.core.state_machine import Engine
from quipu.core.git_db import GitDB
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter


@pytest.fixture
def engine_setup(tmp_path):
    """
    创建一个包含 Git 仓库和 Engine 实例的测试环境。
    默认使用新的 GitObject 存储后端。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)

    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有历史记录的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态 (适用于两种后端)。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    status = engine.align()
    
    assert status == "ORPHAN"
    assert engine.current_node is None

def test_capture_drift_git_object(engine_setup):
    """
    测试场景 (GitObject Backend)：当工作区处于 DIRTY 状态时，引擎应能成功捕获变化，
    创建一个新的 Capture 节点，并更新 Git 引用。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    
    # Manually create an initial commit to act as parent
    initial_commit = engine.git_db.commit_tree(initial_hash, parent_hashes=None, message="Initial")
    engine.git_db.update_ref("refs/quipu/history", initial_commit)
    
    # Create the first node using the writer to simulate a full flow
    engine.writer.create_node("plan", "_" * 40, initial_hash, "Initial content")
    initial_commit = engine.git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()

    # Re-align to load the node we just created
    engine.align()
    
    (repo_path / "main.py").write_text("version = 2", "utf-8")
    dirty_hash = engine.git_db.get_tree_hash()
    assert initial_hash != dirty_hash
    
    # --- The Action ---
    capture_node = engine.capture_drift(dirty_hash)
    
    # --- Assertions ---
    assert len(engine.history_graph) == 2, "历史图谱中应有两个节点"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == dirty_hash
    assert capture_node.node_type == "capture"
    assert capture_node.input_tree == initial_hash
    
    # Key Assertion: Verify the Git ref was updated by the writer
    latest_ref_commit = subprocess.check_output(
        ["git", "rev-parse", "refs/quipu/history"], cwd=repo_path
    ).decode().strip()
    assert latest_ref_commit != initial_commit, "Git 引用必须更新到新的锚点"
    
    # Verify the new commit has the correct parent
    parent_of_latest = subprocess.check_output(
        ["git", "rev-parse", f"{latest_ref_commit}^"], cwd=repo_path
    ).decode().strip()
    assert parent_of_latest == initial_commit

class TestEngineFindNodes:
    @pytest.fixture
    def populated_engine(self, engine_setup):
        engine, repo_path = engine_setup
        
        # Node 1 (Plan)
        engine.create_plan_node("in1", "out1", "# feat: Add feature A")
        # Node 2 (Capture)
        engine.capture_drift("out2", message="Snapshot after feature A")
        # Node 3 (Plan)
        engine.create_plan_node("in3", "out3", "refactor: Cleanup code")
        
        # align to load graph
        engine.align()
        return engine

    def test_find_by_type(self, populated_engine):
        plans = populated_engine.find_nodes(node_type="plan")
        captures = populated_engine.find_nodes(node_type="capture")
        
        assert len(plans) == 2
        assert all(p.node_type == "plan" for p in plans)
        
        assert len(captures) == 1
        assert captures[0].node_type == "capture"

    def test_find_by_summary_regex(self, populated_engine):
        feat_nodes = populated_engine.find_nodes(summary_regex="feat:")
        assert len(feat_nodes) == 1
        assert "Add feature A" in feat_nodes[0].summary
        
        snapshot_nodes = populated_engine.find_nodes(summary_regex="snapshot")
        assert len(snapshot_nodes) == 1
        assert "Snapshot after" in snapshot_nodes[0].summary

    def test_find_combined_filters(self, populated_engine):
        results = populated_engine.find_nodes(summary_regex="refactor", node_type="plan")
        assert len(results) == 1
        assert "Cleanup code" in results[0].summary
        
        empty_results = populated_engine.find_nodes(summary_regex="feat", node_type="capture")
        assert len(empty_results) == 0

    def test_find_limit(self, populated_engine):
        results = populated_engine.find_nodes(limit=1)
        assert len(results) == 1
        # Should be the latest one
        assert "Cleanup code" in results[0].summary

class TestPersistentIgnores:
    def test_sync_creates_file_if_not_exists(self, engine_setup):
        """测试：如果 exclude 文件不存在，应能根据默认配置创建它。"""
        engine, repo_path = engine_setup
        
        (repo_path / ".quipu").mkdir(exist_ok=True)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        assert exclude_file.exists()
        content = exclude_file.read_text("utf-8")
        
        assert "# --- Managed by Quipu ---" in content
        assert ".envs" in content

    def test_sync_appends_to_existing_file(self, engine_setup):
        """测试：如果 exclude 文件已存在，应追加 Quipu 块而不是覆盖。"""
        engine, repo_path = engine_setup
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(exist_ok=True)
        user_content = "# My personal ignores\n*.log\n"
        exclude_file.write_text(user_content)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        content = exclude_file.read_text("utf-8")
        assert user_content in content
        assert "# --- Managed by Quipu ---" in content
        assert "o.md" in content

    def test_sync_updates_existing_block(self, engine_setup):
        """测试：如果 Quipu 块已存在，应更新其内容。"""
        engine, repo_path = engine_setup
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        exclude_file.parent.mkdir(exist_ok=True)
        
        old_block = (
            "# --- Managed by Quipu ---\n"
            "old_rule/\n"
            "# --- End Managed by Quipu ---"
        )
        user_content = f"# My ignores\n{old_block}\n# More ignores"
        exclude_file.write_text(user_content)
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        content = exclude_file.read_text("utf-8")
        assert "old_rule/" not in content
        assert ".vscode" in content
        assert "# My ignores" in content
        assert "# More ignores" in content

    def test_sync_uses_user_config(self, engine_setup):
        """测试：应优先使用 .quipu/config.yml 中的用户配置。"""
        import yaml
        engine, repo_path = engine_setup
        
        config_dir = repo_path / ".quipu"
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.yml"
        
        user_ignores = {
            "sync": {
                "persistent_ignores": ["custom_dir/", "*.tmp"]
            }
        }
        config_file.write_text(yaml.dump(user_ignores), "utf-8")
        
        # 重新初始化 Engine 以触发同步逻辑
        engine = Engine(repo_path, reader=engine.reader, writer=engine.writer)
        
        exclude_file = repo_path / ".git" / "info" / "exclude"
        content = exclude_file.read_text("utf-8")
        
        assert "custom_dir/" in content
        assert "*.tmp" in content
        assert ".envs" not in content
~~~~~

~~~~~act
write_file tests/test_storage_integration.py
~~~~~

~~~~~python
import pytest
import subprocess
from pathlib import Path
from typer.testing import CliRunner

from quipu.cli.main import app
from quipu.cli.factory import create_engine

# A simple plan that creates one file
PLAN_A = """
~~~act
write_file a.txt
~~~
~~~content
File A content
~~~
"""

# A simple plan that creates a different file
PLAN_B = """
~~~act
write_file b.txt
~~~
~~~content
File B content
~~~
"""

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    """Creates a temporary directory and initializes it as a Git repository."""
    ws = tmp_path / "ws"
    ws.mkdir()
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=ws, check=True)
    return ws

def git_rev_parse(ref: str, cwd: Path) -> str:
    """Helper to get the hash of a git ref."""
    result = subprocess.run(["git", "rev-parse", ref], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


class TestStorageSelection:
    """Tests the automatic detection and selection of storage backends."""

    def test_defaults_to_git_object_storage_on_new_project(self, runner, git_workspace):
        """
        SCENARIO: A user starts a new project.
        EXPECTATION: The system should use the new Git Object storage by default.
        """
        # Action: Run a plan in the new workspace
        result = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        
        assert result.exit_code == 0, result.stderr
        
        # Verification
        assert (git_workspace / "a.txt").exists()
        
        # 1. New ref should exist
        ref_hash = git_rev_parse("refs/quipu/history", git_workspace)
        assert len(ref_hash) == 40, "A git ref for quipu history should have been created."
        
        # 2. Old directory should NOT exist
        legacy_history_dir = git_workspace / ".quipu" / "history"
        assert not legacy_history_dir.exists(), "Legacy file system history should not be used."


    def test_continues_using_git_object_storage(self, runner, git_workspace):
        """
        SCENARIO: A user runs quipu in a project already using the new format.
        EXPECTATION: The system should continue using the Git Object storage.
        """
        # Setup: Run one command to establish the new format
        runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        hash_after_a = git_rev_parse("refs/quipu/history", git_workspace)
        assert hash_after_a
        
        # Action: Run a second command
        result = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_B)
        
        assert result.exit_code == 0, result.stderr
        
        # Verification
        # 1. The ref should be updated to a new commit
        hash_after_b = git_rev_parse("refs/quipu/history", git_workspace)
        assert hash_after_b != hash_after_a, "The history ref should point to a new commit."
        
        # 2. The parent of the new commit should be the old one
        parent_hash = git_rev_parse(f"{hash_after_b}^", git_workspace)
        assert parent_hash == hash_after_a, "The new commit should be parented to the previous one."

        # 3. No legacy files should be created
        assert not (git_workspace / ".quipu" / "history").exists()


class TestGitObjectWorkflow:
    """End-to-end tests for core commands using the Git Object backend."""

    def test_full_workflow_with_git_object_storage(self, runner, git_workspace):
        # 1. Run a plan to create state A
        res_run = runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        assert res_run.exit_code == 0
        assert (git_workspace / "a.txt").exists()
        
        # 2. Manually add a file and use `save` to create state B
        (git_workspace / "b.txt").write_text("manual change")
        res_save = runner.invoke(app, ["save", "add b.txt", "-w", str(git_workspace)])
        assert res_save.exit_code == 0
        assert "快照已保存" in res_save.stderr
        
        # 3. Use `log` to check history
        res_log = runner.invoke(app, ["log", "-w", str(git_workspace)])
        assert res_log.exit_code == 0
        assert "add b.txt" in res_log.stderr  # Summary of the save message
        assert "write_file a.txt" in res_log.stderr # Summary of the plan
        
        # 4. Use `find` and `checkout` to go back to state A
        # --- REFACTOR START ---
        # Use the robust find_nodes API via CLI to get the target hash
        res_find = runner.invoke(app, ["find", "--summary", "write_file a.txt", "-w", str(git_workspace)])
        assert res_find.exit_code == 0
        
        # Parse the output to get the full hash
        found_line = res_find.stderr.splitlines()[-1] # Get the last line of output
        output_tree_a = found_line.split()[2] # Hash is the 3rd element
        
        assert len(output_tree_a) == 40
        # --- REFACTOR END ---

        res_checkout = runner.invoke(app, ["checkout", output_tree_a[:8], "-f", "-w", str(git_workspace)])
        assert res_checkout.exit_code == 0, res_checkout.stderr
        
        # Verification of state A
        assert (git_workspace / "a.txt").exists()
        assert not (git_workspace / "b.txt").exists()

class TestFindCliCommand:

    @pytest.fixture
    def populated_workspace(self, git_workspace):
        # Run plan A
        runner.invoke(app, ["run", "-y", "-w", str(git_workspace)], input=PLAN_A)
        # Run save
        (git_workspace / "change.txt").write_text("manual")
        runner.invoke(app, ["save", "Snapshot 1", "-w", str(git_workspace)])
        return git_workspace

    def test_find_cli_by_type(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "--type", "plan", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[PLAN]" in result.stderr
        assert "[CAPTURE]" not in result.stderr
        assert "write_file a.txt" in result.stderr

    def test_find_cli_by_summary(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "-s", "snapshot", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "[CAPTURE]" in result.stderr
        assert "Snapshot 1" in result.stderr
        assert "[PLAN]" not in result.stderr

    def test_find_cli_no_results(self, runner, populated_workspace):
        result = runner.invoke(app, ["find", "-s", "non-existent", "-w", str(populated_workspace)])
        assert result.exit_code == 0
        assert "未找到符合条件" in result.stderr
~~~~~

~~~~~act
write_file tests/test_integration_v2.py
~~~~~

~~~~~python
import pytest
import logging
from pathlib import Path
from typer.testing import CliRunner
from quipu.cli.controller import run_quipu, QuipuResult
from quipu.cli.main import app
from quipu.core.executor import Executor
from quipu.acts.basic import register as register_basic

# --- Fixtures ---

@pytest.fixture(autouse=True)
def reset_logging():
    """
    每次测试前后重置 logging handlers。
    这是解决 CliRunner I/O Error 的关键，防止 handler 持有已关闭的流。
    """
    root = logging.getLogger()
    # Teardown: 清理所有 handlers
    yield
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()

@pytest.fixture
def workspace(tmp_path):
    """准备一个带 git 的工作区"""
    ws = tmp_path / "ws"
    ws.mkdir()
    
    # 初始化 git (Engine 需要)
    import subprocess
    subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
    # 设置 user 避免 commit 报错
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=ws, check=True)
    subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=ws, check=True)
    
    return ws

# --- 1. Controller Layer Tests (The Core) ---
# 这些测试直接验证业务逻辑，不涉及 CLI 参数解析干扰

class TestController:

    def test_run_quipu_success(self, workspace):
        """测试正常执行流程"""
        from quipu.cli.factory import create_engine
        plan = """
~~~act
write_file
~~~
~~~path
hello.txt
~~~
~~~content
Hello Quipu
~~~
"""
        result = run_quipu(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is True
        assert result.exit_code == 0
        assert (workspace / "hello.txt").exists()
        
        # 验证 Engine 是否生成了 Plan 节点 (后端无关)
        engine = create_engine(workspace)
        nodes = engine.reader.load_all_nodes()
        assert len(nodes) >= 1

    def test_run_quipu_execution_error(self, workspace):
        """测试执行期间的预期错误 (如文件不存在)"""
        # 试图追加到一个不存在的文件
        plan = """
~~~act
append_file
~~~
~~~path
ghost.txt
~~~
~~~content
boo
~~~
"""
        result = run_quipu(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is False
        assert result.exit_code == 1
        assert "文件不存在" in result.message

    def test_run_quipu_empty_plan(self, workspace):
        """测试无有效指令"""
        plan = "Just some text, no acts."
        
        result = run_quipu(content=plan, work_dir=workspace, yolo=True)
        
        assert result.success is False # 视为非成功状态（虽然不是错误，但任务未完成）
        assert result.exit_code == 0   # 但退出码为 0，不报错
        assert "未找到任何有效的" in result.message

# --- 2. CLI Layer Tests (The Shell) ---
# 这些测试验证 main.py 是否正确解析参数并传递给 Controller
# 由于 Controller 已经测过了，这里可以用 mock 来隔离

runner = CliRunner()

class TestCLIWrapper:
    
    def test_cli_help(self):
        """测试 --help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Axon" in result.stdout

    def test_cli_file_input(self, tmp_path):
        """测试从文件读取输入"""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("~~~act\nend\n~~~", encoding="utf-8")
        
        # 我们不需要真的跑 git，只要看是否尝试运行即可
        # 如果 work-dir 不是 git repo，Controller 会报错或 Engine 初始化失败
        # 这里为了简单，我们让它在一个临时目录跑，预期可能是 1 (Engine init fail) 或 0 (如果 Engine 容错好)
        # 关键是不要由 CliRunner 抛出 ValueError
        
        # 初始化一个最小 git repo 避免 Engine 报错干扰 CLI 测试
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        
        result = runner.invoke(app, ["run", str(plan_file), "--work-dir", str(tmp_path), "--yolo"])
        
        # 只要不是 Python traceback 导致的 Crash (exit_code != 0 and not handled) 就行
        # 我们的 Controller 会捕获异常返回 exit_code 1
        # 这里的 'end' act 是一个无害操作，应该返回 0
        assert result.exit_code == 0
        assert result.exception is None

    def test_cli_no_input_shows_usage(self, monkeypatch, tmp_path):
        """测试无输入时显示用法"""
        # 1. 临时修改 main 模块中的默认入口文件引用，防止读取当前目录下的 o.md
        # 注意：必须 patch 'main' 模块，而不是 'config' 模块，因为 main 采用了 from import
        from quipu.cli import main
        monkeypatch.setattr(main, "DEFAULT_ENTRY_FILE", tmp_path / "non_existent.md")
        
        # 2. 同时确保 STDIN 不是 TTY，也不是管道（模拟纯交互式空运行）
        # CliRunner 默认就是这种状态，但为了保险起见，我们什么都不输入
        
        result = runner.invoke(app, ["run"]) # 无参数，无管道
        
        assert result.exit_code == 0
        assert "用法示例" in result.stderr

    def test_cli_list_acts(self):
        """测试 --list-acts"""
        # --list-acts 是 'run' 命令的一个选项
        result = runner.invoke(app, ["run", "--list-acts"])
        assert result.exit_code == 0
        assert "write_file" in result.stderr

class TestCheckoutCLI:

    @pytest.fixture
    def populated_workspace(self, workspace):
        """
        Create a workspace with two distinct, non-overlapping history nodes.
        State A contains only a.txt.
        State B contains only b.txt.
        This fixture is backend-agnostic.
        """
        from quipu.cli.factory import create_engine

        # State A: Create a.txt
        plan_a = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nState A\n~~~"
        run_quipu(content=plan_a, work_dir=workspace, yolo=True)
        
        engine_after_a = create_engine(workspace)
        nodes_after_a = sorted(engine_after_a.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_a = nodes_after_a[-1]
        hash_a = node_a.output_tree

        # Manually create State B by removing a.txt and adding b.txt
        (workspace / "a.txt").unlink()
        plan_b = "~~~act\nwrite_file b.txt\n~~~\n~~~content\nState B\n~~~"
        run_quipu(content=plan_b, work_dir=workspace, yolo=True)

        engine_after_b = create_engine(workspace)
        nodes_after_b = sorted(engine_after_b.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_b = nodes_after_b[-1]
        hash_b = node_b.output_tree
        
        return workspace, hash_a, hash_b

    def test_cli_checkout_success(self, populated_workspace):
        """Test checking out from State B to State A."""
        workspace, hash_a, hash_b = populated_workspace
        
        # Pre-flight check: we are in state B
        assert not (workspace / "a.txt").exists()
        assert (workspace / "b.txt").exists()

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])
        
        assert result.exit_code == 0
        assert "✅ 已成功切换到状态" in result.stderr
        
        # Post-flight check: we are now in state A
        assert (workspace / "a.txt").exists()
        assert (workspace / "a.txt").read_text() == "State A"
        assert not (workspace / "b.txt").exists()

    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from quipu.cli.factory import create_engine
        workspace, hash_a, hash_b = populated_workspace
        
        # Make the workspace dirty
        (workspace / "c_dirty.txt").write_text("uncommitted change")
        
        # Get node count via the storage-agnostic reader interface
        engine_before = create_engine(workspace)
        num_nodes_before = len(engine_before.reader.load_all_nodes())

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])

        assert result.exit_code == 0, result.stderr
        assert "⚠️  检测到当前工作区存在未记录的变更" in result.stderr
        
        # Get node count again after the operation
        engine_after = create_engine(workspace)
        num_nodes_after = len(engine_after.reader.load_all_nodes())
        assert num_nodes_after == num_nodes_before + 1, "A new capture node should have been created"

        # Check final state is correct
        assert (workspace / "a.txt").exists()
        assert not (workspace / "c_dirty.txt").exists()

    def test_cli_checkout_not_found(self, populated_workspace):
        """Test checkout with a non-existent hash."""
        workspace, _, _ = populated_workspace
        
        result = runner.invoke(app, ["checkout", "deadbeef", "--work-dir", str(workspace), "--force"])
        
        assert result.exit_code == 1
        assert "❌ 错误: 未找到哈希前缀" in result.stderr

    def test_cli_checkout_already_on_state(self, populated_workspace):
        """Test checking out to the current state does nothing."""
        workspace, _, hash_b = populated_workspace
        
        result = runner.invoke(app, ["checkout", hash_b[:8], "--work-dir", str(workspace), "--force"])
        
        assert result.exit_code == 0
        assert "✅ 工作区已处于目标状态" in result.stderr
~~~~~
