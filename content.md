# refactor(cli): extract engine factory [统一 Engine 实例化工厂]

## 用户需求
目前 `quipu-cli` 中的 `main.py` 和 `controller.py` 存在重复的 `Engine` 初始化和根目录查找逻辑，违反了 DRY 原则。需要将这些逻辑提取到统一的工厂模块中，以便于维护和保证行为一致性。

## 评论
这是一个基础性的重构，通过集中管理存储策略的选择逻辑，消除了代码异味，并为未来引入新的存储后端（如 SQL 或远程后端）提供了单一的修改点。同时，这也简化了测试代码中对 Engine 的初始化调用。

## 目标
*   创建 `packages/quipu-cli/src/quipu/cli/factory.py`。
*   将 `find_project_root` 和 `create_engine` 逻辑集中于此。
*   重构 `controller.py` 和 `main.py` 以使用新工厂。
*   更新引用了私有辅助函数的测试用例。

## 基本原理
1.  **单一职责**: `factory.py` 负责“构建”对象，`controller` 负责业务流，`main` 负责参数解析。
2.  **代码复用**: 消除重复的存储格式检测代码 (`if git_db.has_quipu_ref...`)。
3.  **一致性**: 确保 `quipu run` 和 `quipu log` 即使在边缘情况（如混合存储格式）下也表现出相同的行为。

## 标签
#comp/cli #scope/dx #refactor

---

## Script

### Acts 1: Create Factory Module

创建新的工厂模块，封装根目录解析和引擎构建逻辑。

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/factory.py
~~~~~

~~~~~python
import logging
from pathlib import Path
from typing import Optional

from quipu.core.state_machine import Engine
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.core.git_db import GitDB

logger = logging.getLogger(__name__)

def find_project_root(start_path: Path) -> Optional[Path]:
    """向上递归查找包含 .git 的目录作为项目根目录"""
    try:
        current = start_path.resolve()
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists():
                return parent
    except Exception:
        pass
    return None

def resolve_root(work_dir: Path) -> Path:
    """解析项目根目录，如果未找到则回退到 work_dir"""
    root = find_project_root(work_dir)
    return root if root else work_dir

def create_engine(work_dir: Path) -> Engine:
    """
    实例化完整的 Engine 堆栈。
    自动检测存储格式 (Git Object vs. File System) 并加载相应后端。
    该函数会自动调用 engine.align() 来加载历史图谱。
    """
    real_root = resolve_root(work_dir)
    
    # 1. 创建 GitDB 实例
    # 假设工作区是一个有效的 git 仓库。如果不是，GitDB 初始化可能会抛出异常。
    git_db = GitDB(real_root)
    
    # 2. 检测存储格式并选择策略
    # 优先检测新格式 (Git refs)
    if git_db.has_quipu_ref():
        logger.debug("Detected Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)
    # 回退检测旧格式 (FS directory)
    elif (real_root / ".quipu" / "history").exists():
        logger.debug("Detected File System storage format (legacy).")
        history_dir = real_root / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
    # 默认在新项目中使用新格式
    else:
        logger.debug("No existing history found. Defaulting to Git Object storage format.")
        reader = GitObjectHistoryReader(git_db)
        writer = GitObjectHistoryWriter(git_db)

    # 3. 注入依赖并实例化 Engine
    engine = Engine(real_root, reader=reader, writer=writer)
    engine.align()  # 对齐以加载历史图谱
    
    return engine
~~~~~

### Acts 2: Refactor Controller

更新 `controller.py` 以使用工厂方法，移除重复代码。

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/controller.py
~~~~~

~~~~~python
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from quipu.core.result import QuipuResult
from quipu.core.executor import Executor, ExecutionError
from quipu.core.exceptions import ExecutionError as CoreExecutionError
from quipu.core.parser import get_parser, detect_best_parser
from quipu.core.plugin_loader import load_plugins

# 从配置导入
from .config import PROJECT_ROOT
from .factory import find_project_root, create_engine
from quipu.acts import register_core_acts

logger = logging.getLogger(__name__)

def _load_extra_plugins(executor: Executor, work_dir: Path):
    """
    按照层级顺序加载外部插件，高优先级会覆盖低优先级。
    优先级顺序: Project > Env > Home
    """
    plugin_sources = []
    
    # 优先级由低到高添加，后面的会覆盖前面的
    # 1. User Home (Lowest priority)
    home_acts = Path.home() / ".quipu" / "acts"
    plugin_sources.append(("🏠 Global", home_acts))

    # 2. Config / Env
    env_path = os.getenv("AXON_EXTRA_ACTS_DIR")
    if env_path:
        plugin_sources.append(("🔧 Env", Path(env_path)))
    
    # 3. Project Root (Highest priority)
    project_root = find_project_root(work_dir)
    if project_root:
        proj_acts = project_root / ".quipu" / "acts"
        plugin_sources.append(("📦 Project", proj_acts))

    seen_paths = set()
    for label, path in plugin_sources:
        if not path.exists() or not path.is_dir():
            continue
        
        resolved_path = path.resolve()
        if resolved_path in seen_paths:
            continue
        
        load_plugins(executor, path)
        seen_paths.add(resolved_path)

def run_quipu(
    content: str,
    work_dir: Path,
    parser_name: str = "auto",
    yolo: bool = False
) -> QuipuResult:
    """
    Axon 核心业务逻辑入口。
    
    负责协调 Engine (状态), Parser (解析), Executor (执行) 三者的工作。
    任何异常都会被捕获并转化为失败的 QuipuResult。
    """
    try:
        # --- Phase 0: Root Canonicalization (根目录规范化) ---
        project_root = find_project_root(work_dir)
        if not project_root:
            # 如果不在 Git 仓库内，则使用原始 work_dir，但 Engine 初始化可能会失败。
            project_root = work_dir
        
        logger.info(f"Project Root resolved to: {project_root}")

        # --- Phase 1: Engine Initialization & Perception ---
        # 使用工厂创建 Engine，这会自动处理存储后端检测和 align
        engine = create_engine(work_dir)
        
        # --- Phase 2: Decision (Lazy Capture) ---
        current_hash = engine.git_db.get_tree_hash()
        
        # 判断是否 Dirty/Orphan
        # 如果 current_node 存在且其 output_tree 与当前 hash 一致，则为 Clean
        is_clean = engine.current_node is not None and engine.current_node.output_tree == current_hash
        
        if not is_clean:
            # 如果环境有漂移（或全新项目），先生成一个 Capture 节点
            # 这确保了后续的 Plan 是基于一个已知的、干净的状态执行的
            engine.capture_drift(current_hash)
            # 捕获后，is_clean 逻辑上变为 True
        
        # 记录执行前的状态，作为 Plan 的 input_tree
        if engine.current_node:
            input_tree_hash = engine.current_node.output_tree
        else:
            # 此处处理极端的创世状态（理论上 capture_drift 应该已经处理了所有情况，除非 capture 失败）
            input_tree_hash = current_hash

        # --- Phase 3: Action (Execution) ---
        
        # 3.1 Parser
        final_parser_name = parser_name
        if parser_name == "auto":
            final_parser_name = detect_best_parser(content)
            if final_parser_name != "backtick":
                logger.info(f"🔍 自动检测到解析器: {final_parser_name}")

        parser = get_parser(final_parser_name)
        statements = parser.parse(content)
        
        if not statements:
            return QuipuResult(
                success=False, 
                exit_code=0, # 没找到指令不算错误，但也无需继续
                message=f"⚠️  使用 '{final_parser_name}' 解析器未找到任何有效的 'act' 操作块。"
            )

        # 3.2 Executor Setup
        executor = Executor(root_dir=project_root, yolo=yolo) # 使用 project_root
        
        # 加载插件
        register_core_acts(executor) # 内置 (从 runtime 包加载)
        _load_extra_plugins(executor, project_root)       # 外部 (也基于 project_root)

        # 3.3 Execute
        executor.execute(statements)

        # --- Phase 4: Recording (Plan Crystallization) ---
        
        # 执行成功后，计算新的状态
        output_tree_hash = engine.git_db.get_tree_hash()
        
        # 如果状态发生了变化，或者我们想记录即使无变化的 Plan（通常记录一下比较好）
        # 这里我们调用 Engine 的 create_plan_node 方法
        engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content
        )

        return QuipuResult(success=True, exit_code=0, message="✨ 执行成功")

    except (ExecutionError, CoreExecutionError) as e:
        # 预期的执行错误 (如文件找不到，Git 冲突等)
        logger.error(f"❌ 操作失败: {e}")
        return QuipuResult(success=False, exit_code=1, message=str(e), error=e)
        
    except Exception as e:
        # 意外的运行时错误
        logger.error(f"运行时错误: {e}", exc_info=True)
        return QuipuResult(success=False, exit_code=1, message=f"系统错误: {e}", error=e)
~~~~~

### Acts 3: Refactor Main CLI

更新 `main.py` 以使用工厂方法。

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
from quipu.core.migration import HistoryMigrator

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
    if file and not file.exists() and file.name in ["log", "checkout", "sync", "init", "ui"]:
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
    root = resolve_root(work_dir)
    
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

### Acts 4: Update Tests

更新引用了私有辅助函数的测试用例，改用公共工厂方法。

~~~~~act
replace tests/test_root_invariance.py
~~~~~

~~~~~python
        # 2. 验证 Engine 状态记录的正确性 (后端无关)
        from quipu.cli.main import _setup_engine
        engine = _setup_engine(project_root)
        nodes = engine.reader.load_all_nodes()
~~~~~

~~~~~python
        # 2. 验证 Engine 状态记录的正确性 (后端无关)
        from quipu.cli.factory import create_engine
        engine = create_engine(project_root)
        nodes = engine.reader.load_all_nodes()
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
    def test_run_quipu_success(self, workspace):
        """测试正常执行流程"""
        from quipu.cli.main import _setup_engine
        plan = """
~~~~~

~~~~~python
    def test_run_quipu_success(self, workspace):
        """测试正常执行流程"""
        from quipu.cli.factory import create_engine
        plan = """
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
        # 验证 Engine 是否生成了 Plan 节点 (后端无关)
        engine = _setup_engine(workspace)
        nodes = engine.reader.load_all_nodes()
        assert len(nodes) >= 1
~~~~~

~~~~~python
        # 验证 Engine 是否生成了 Plan 节点 (后端无关)
        engine = create_engine(workspace)
        nodes = engine.reader.load_all_nodes()
        assert len(nodes) >= 1
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
        State B contains only b.txt.
        This fixture is backend-agnostic.
        """
        from quipu.cli.main import _setup_engine

        # State A: Create a.txt
~~~~~

~~~~~python
        State B contains only b.txt.
        This fixture is backend-agnostic.
        """
        from quipu.cli.factory import create_engine

        # State A: Create a.txt
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
        plan_a = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nState A\n~~~"
        run_quipu(content=plan_a, work_dir=workspace, yolo=True)
        
        engine_after_a = _setup_engine(workspace)
        nodes_after_a = sorted(engine_after_a.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_a = nodes_after_a[-1]
~~~~~

~~~~~python
        plan_a = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nState A\n~~~"
        run_quipu(content=plan_a, work_dir=workspace, yolo=True)
        
        engine_after_a = create_engine(workspace)
        nodes_after_a = sorted(engine_after_a.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_a = nodes_after_a[-1]
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
        plan_b = "~~~act\nwrite_file b.txt\n~~~\n~~~content\nState B\n~~~"
        run_quipu(content=plan_b, work_dir=workspace, yolo=True)

        engine_after_b = _setup_engine(workspace)
        nodes_after_b = sorted(engine_after_b.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_b = nodes_after_b[-1]
~~~~~

~~~~~python
        plan_b = "~~~act\nwrite_file b.txt\n~~~\n~~~content\nState B\n~~~"
        run_quipu(content=plan_b, work_dir=workspace, yolo=True)

        engine_after_b = create_engine(workspace)
        nodes_after_b = sorted(engine_after_b.reader.load_all_nodes(), key=lambda n: n.timestamp)
        node_b = nodes_after_b[-1]
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from quipu.cli.main import _setup_engine
        workspace, hash_a, hash_b = populated_workspace
        
        # Make the workspace dirty
~~~~~

~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from quipu.cli.factory import create_engine
        workspace, hash_a, hash_b = populated_workspace
        
        # Make the workspace dirty
~~~~~

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
        # Get node count via the storage-agnostic reader interface
        engine_before = _setup_engine(workspace)
        num_nodes_before = len(engine_before.reader.load_all_nodes())

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])

        assert result.exit_code == 0, result.stderr
        assert "⚠️  检测到当前工作区存在未记录的变更" in result.stderr
        
        # Get node count again after the operation
        engine_after = _setup_engine(workspace)
        num_nodes_after = len(engine_after.reader.load_all_nodes())
~~~~~

~~~~~python
        # Get node count via the storage-agnostic reader interface
        engine_before = create_engine(workspace)
        num_nodes_before = len(engine_before.reader.load_all_nodes())

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])

        assert result.exit_code == 0, result.stderr
        assert "⚠️  检测到当前工作区存在未记录的变更" in result.stderr
        
        # Get node count again after the operation
        engine_after = create_engine(workspace)
        num_nodes_after = len(engine_after.reader.load_all_nodes())
~~~~~

~~~~~act
replace tests/test_plugins.py
~~~~~

~~~~~python
import pytest
import sys
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins
from quipu.cli.controller import find_project_root  # 从 Controller 导入辅助函数

class TestPluginLoading:
~~~~~

~~~~~python
import pytest
import sys
from pathlib import Path
from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins
from quipu.cli.factory import find_project_root  # 从 Factory 导入辅助函数

class TestPluginLoading:
~~~~~

~~~~~act
replace tests/test_head_and_root.py
~~~~~

~~~~~python
import pytest
import os
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.controller import find_project_root
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestHeadTracking:
~~~~~

~~~~~python
import pytest
import os
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.factory import find_project_root
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestHeadTracking:
~~~~~

~~~~~act
replace tests/test_idempotent_node.py
~~~~~

~~~~~python
        history_dir = workspace / ".quipu" / "history"
        
        # 使用正确的 Engine 设置来验证
        from quipu.cli.main import _setup_engine
        engine1 = _setup_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
        assert len(nodes1) >= 1
        
        # 3. 执行一个无变更的操作 (State A -> State A)
        plan_2 = "~~~act\nread_file a.txt\n~~~"
        result = run_quipu(plan_2, workspace, yolo=True)
        
        assert result.success is True
        
        # 4. 验证是否生成了新节点
        engine2 = _setup_engine(workspace)
        nodes2 = sorted(engine2.reader.load_all_nodes(), key=lambda n: n.timestamp)
        assert len(nodes2) == len(nodes1) + 1
~~~~~

~~~~~python
        history_dir = workspace / ".quipu" / "history"
        
        # 使用正确的 Engine 设置来验证
        from quipu.cli.factory import create_engine
        engine1 = create_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
        assert len(nodes1) >= 1
        
        # 3. 执行一个无变更的操作 (State A -> State A)
        plan_2 = "~~~act\nread_file a.txt\n~~~"
        result = run_quipu(plan_2, workspace, yolo=True)
        
        assert result.success is True
        
        # 4. 验证是否生成了新节点
        engine2 = create_engine(workspace)
        nodes2 = sorted(engine2.reader.load_all_nodes(), key=lambda n: n.timestamp)
        assert len(nodes2) == len(nodes1) + 1
~~~~~