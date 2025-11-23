import typer
import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

from logger_config import setup_logging
from core.controller import run_axon
from config import DEFAULT_WORK_DIR, DEFAULT_ENTRY_FILE, PROJECT_ROOT
from core.plugin_loader import load_plugins
from core.executor import Executor
import inspect

# 注意：不要在模块级别直接调用 setup_logging()，
# 否则会导致 CliRunner 测试中的 I/O 流过早绑定/关闭问题。
logger = logging.getLogger(__name__)

app = typer.Typer(add_completion=False)

@app.command()
def cli(
    ctx: typer.Context,
    file: Annotated[
        Optional[Path], 
        typer.Argument(
            help=f"包含 Markdown 指令的文件路径。",
            resolve_path=True
        )
    ] = None,
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
    parser_name: Annotated[
        str,
        typer.Option(
            "--parser", "-p",
            help=f"选择解析器语法。默认为 'auto'。",
        )
    ] = "auto",
    yolo: Annotated[
        bool,
        typer.Option(
            "--yolo", "-y",
            help="跳过所有确认步骤，直接执行 (You Only Look Once)。",
        )
    ] = False,
    list_acts: Annotated[
        bool,
        typer.Option(
            "--list-acts", "-l",
            help="列出所有可用的操作指令及其说明。",
        )
    ] = False
):
    """
    Axon: 执行 Markdown 文件中的操作指令。
    支持从文件参数、管道 (STDIN) 或默认文件中读取指令。
    """
    # 延迟初始化日志，确保流处理正确
    setup_logging()
    
    # --- 1. 特殊指令处理 ---
    if list_acts:
        executor = Executor(root_dir=Path("."), yolo=True)
        load_plugins(executor, PROJECT_ROOT / "acts")
        
        typer.secho("\n📋 可用的 Axon 指令列表:\n", fg=typer.colors.GREEN, bold=True, err=True)
        
        acts = executor.get_registered_acts()
        for name in sorted(acts.keys()):
            doc = acts[name]
            clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
            indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
            
            typer.secho(f"🔹 {name}", fg=typer.colors.CYAN, bold=True, err=True)
            typer.echo(f"{indented_doc}\n", err=True)
            
        ctx.exit(0)

    # --- 2. 输入源处理 (Input Normalization) ---
    content = ""
    source_desc = ""

    # A. 显式文件参数
    if file:
        if not file.exists():
            typer.secho(f"❌ 错误: 找不到指令文件: {file}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
        if not file.is_file():
            typer.secho(f"❌ 错误: 路径不是文件: {file}", fg=typer.colors.RED, err=True)
            ctx.exit(1)
        content = file.read_text(encoding="utf-8")
        source_desc = f"文件 ({file.name})"

    # B. 尝试读取 STDIN (管道)
    # 只要不是 TTY，就尝试读取。这解决了 isatty 在测试环境中的歧义。
    elif not sys.stdin.isatty():
        try:
            # 读取所有内容，如果为空字符串说明没有数据
            stdin_content = sys.stdin.read()
            if stdin_content:
                content = stdin_content
                source_desc = "STDIN (管道流)"
        except Exception:
            pass # 读取失败则忽略

    # C. 回退到默认文件
    if not content and DEFAULT_ENTRY_FILE.exists():
        content = DEFAULT_ENTRY_FILE.read_text(encoding="utf-8")
        source_desc = f"默认文件 ({DEFAULT_ENTRY_FILE.name})"

    # D. 最终检查
    if not content.strip():
        typer.secho(f"⚠️  提示: 未提供输入，且当前目录下未找到默认文件 '{DEFAULT_ENTRY_FILE.name}'。", fg=typer.colors.YELLOW, err=True)
        typer.echo("\n用法示例:", err=True)
        typer.echo("  axon my_plan.md       # 指定文件", err=True)
        typer.echo("  echo '...' | axon     # 管道输入", err=True)
        typer.echo("\n更多选项请使用 --help", err=True)
        ctx.exit(0) # 这是一个正常的空运行退出，不应报错

    logger.info(f"已加载指令源: {source_desc}")
    logger.info(f"工作区根目录: {work_dir}")
    
    if yolo:
        logger.warning("⚠️  YOLO 模式已开启：将自动确认所有修改。")

    # --- 3. 调用核心控制器 (Core Execution) ---
    result = run_axon(
        content=content,
        work_dir=work_dir,
        parser_name=parser_name,
        yolo=yolo
    )

    # --- 4. 处理结果 (Output Mapping) ---
    if result.message:
        # 将摘要信息输出到 stderr
        color = typer.colors.GREEN if result.success else typer.colors.RED
        typer.secho(f"\n{result.message}", fg=color, err=True)

    # 如果有数据需要输出到 stdout (例如 read_file 的内容)，在这里处理
    # 目前 Controller 还没有数据返回机制，暂时保留接口
    if result.data:
        typer.echo(result.data)

    # 使用 ctx.exit 而不是 raise typer.Exit，对测试框架更友好
    ctx.exit(result.exit_code)

if __name__ == "__main__":
    app()