import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.syntax import Syntax

from ..config import DEFAULT_WORK_DIR
from .helpers import engine_context

logger = logging.getLogger(__name__)


def _find_target_node(graph: dict, hash_prefix: str):
    """辅助函数，用于在图中查找唯一的节点。"""
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
        raise typer.Exit(1)

    unique_commits = {node.commit_hash for node in matches}
    if len(unique_commits) > 1:
        unique_output_trees = {node.output_tree for node in matches}
        if len(unique_output_trees) > 1:
            typer.secho(
                f"❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {len(matches)} 个节点。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)
        matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)
    return matches[0]


def register(app: typer.Typer):
    @app.command(help="显示指定历史节点中的文件内容。")
    def show(
        ctx: typer.Context,
        hash_prefix: Annotated[str, typer.Argument(help="目标状态节点的 commit_hash 或 output_tree 的哈希前缀。")],
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        json_output: Annotated[bool, typer.Option("--json", help="以 JSON 格式将结果输出到 stdout。")] = False,
        extract: Annotated[
            list[str] | None, typer.Option("--extract", "-e", help="仅提取并显示指定文件的内容 (可多次使用)。")
        ] = None,
    ):
        with engine_context(work_dir) as engine:
            target_node = _find_target_node(engine.history_graph, hash_prefix)
            blobs = engine.reader.get_node_blobs(target_node.commit_hash)

            if not blobs:
                if json_output:
                    typer.echo("{}", err=False)
                else:
                    typer.secho("🤷 此节点内部无文件内容。", fg=typer.colors.BLUE, err=True)
                raise typer.Exit()

            output_data = {}
            files_to_process = extract if extract else sorted(blobs.keys())

            for filename in files_to_process:
                if filename not in blobs:
                    typer.secho(
                        f"❌ 错误: 在节点内未找到文件 '{filename}'。",
                        fg=typer.colors.RED,
                        err=True,
                    )
                    typer.secho(
                        f"可用文件: {', '.join(blobs.keys())}",
                        fg=typer.colors.BLUE,
                        err=True,
                    )
                    raise typer.Exit(1)

                content_bytes = blobs[filename]
                try:
                    output_data[filename] = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    output_data[filename] = f"<binary data, {len(content_bytes)} bytes>"

            if json_output:
                typer.echo(json.dumps(output_data, indent=2, ensure_ascii=False), err=False)
            else:
                console = Console()
                if extract:
                    for filename, content in output_data.items():
                        if len(extract) > 1:
                            console.rule(f"[bold]{filename}[/bold]", style="blue")

                        # Per user directive, completely disable rich formatting for --extract
                        # to guarantee raw, unmodified output.
                        console.print(content, end="")
                else:
                    # Default view: show summary and all files prettified
                    ts = target_node.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    tag = f"[{target_node.node_type.upper()}]"
                    typer.echo(
                        f"{ts} {tag:<9} {target_node.short_hash} - {target_node.summary}\n",
                        err=False,
                    )

                    for filename, content in output_data.items():
                        console.rule(f"[bold]{filename}[/bold]", style="blue")
                        if filename.endswith(".json"):
                            syntax = Syntax(content, "json", theme="default", line_numbers=False, word_wrap=False)
                            console.print(syntax)
                        else:
                            console.print(content.strip())
                        console.print()
