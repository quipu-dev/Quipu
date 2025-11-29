好的，我们继续。

现在我们将为 `export` 命令填充核心的业务逻辑。这包括从历史记录中筛选节点，并根据我们定义的规范生成对应的文件名和文件内容（暂时不包含复杂的导航栏）。

## [WIP] feat: 实现 export 命令的核心过滤与文件生成逻辑

### 用户需求
在 `quipu export` 命令的框架内，实现其核心功能：根据用户指定的 `--limit`, `--since`, `--until` 选项过滤历史节点，并为每个节点生成符合命名和内容规范的 Markdown 文件。

### 评论
这是 `export` 命令的关键部分。通过引入辅助函数来处理过滤、命名和内容生成，我们可以保持主命令逻辑的清晰性，并为后续添加导航栏和压缩功能做好准备。使用 `typer.progressbar` 还能提供良好的用户交互体验。

### 目标
1.  在 `export.py` 中添加辅助函数，用于净化文件名、生成标准文件名和格式化 YAML Frontmatter。
2.  实现一个核心的 `_filter_nodes` 函数，用于处理所有过滤逻辑。
3.  实现 `_generate_file_content` 函数，用于构建单个 Markdown 文件的完整内容。
4.  修改 `export_command` 主函数，调用上述辅助函数，遍历筛选后的节点，并将生成的内容写入到指定的输出目录中。

### 基本原理
我们将采用“分而治之”的策略。主命令函数 `export_command` 负责协调和流程控制（获取数据、创建目录、循环、报告进度），而将具体的、可复用的逻辑（如字符串处理、日期比较、内容拼接）封装在独立的私有辅助函数中。这提高了代码的可读性、可维护性和可测试性。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #concept/history #scope/core #ai/instruct #task/domain/cli #task/object/export-command #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 在 `export.py` 中实现核心逻辑

我们将用完整的实现替换 `export.py` 文件中的占位逻辑。这包括所有必要的辅助函数和主循环。

~~~~~act
write_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional, List

import typer
import yaml

from .helpers import engine_context
from ..config import DEFAULT_WORK_DIR
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine

logger = logging.getLogger(__name__)


def _sanitize_summary(summary: str) -> str:
    """净化摘要以用作安全的文件名部分。"""
    if not summary:
        return "no-summary"
    # 移除或替换非法字符
    sanitized = re.sub(r'[\\/:#\[\]|]', '_', summary)
    # 压缩连续的空格或下划线
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    # 截断到合理长度
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
    
    # 使用 PyYAML 库来确保格式正确，并避免手动拼接的风险
    # Dumper=yaml.SafeDumper 保证输出是标准的 YAML 格式
    yaml_str = yaml.dump(data, Dumper=yaml.SafeDumper, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---"


def _filter_nodes(
    nodes: List[QuipuNode],
    limit: Optional[int],
    since: Optional[str],
    until: Optional[str],
) -> List[QuipuNode]:
    """根据时间戳和数量过滤节点列表。"""
    # 节点已按时间倒序排列
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

    # 过滤后，反转列表，使其按时间正序排列，便于导航栏生成
    return list(reversed(filtered))


def _generate_file_content(
    node: QuipuNode,
    engine: Engine,
    no_frontmatter: bool,
    no_nav: bool
) -> str:
    """构建单个 Markdown 文件的完整内容。"""
    parts = []

    if not no_frontmatter:
        parts.append(_format_frontmatter(node))

    # 公共内容
    public_content = engine.reader.get_node_content(node) or ""
    parts.append("# content.md")
    parts.append(public_content.strip())

    # 私有内容
    private_content = engine.reader.get_private_data(node.commit_hash)
    if private_content:
        parts.append("# 开发者意图")
        parts.append(private_content.strip())
        
    # 导航栏 (待实现)
    if not no_nav:
        # Placeholder for navigation bar generation
        pass

    # 使用两个换行符连接所有部分，以确保 Markdown 格式正确
    return "\n\n".join(parts)


def register(app: typer.Typer):
    @app.command(name="export")
    def export_command(
        ctx: typer.Context,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        output_dir: Annotated[
            Path,
            typer.Option(
                "--output-dir",
                "-o",
                help="导出文件的存放目录。",
                file_okay=False,
                dir_okay=True,
                resolve_path=True,
            ),
        ] = Path("./.quipu/export"),
        limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="限制导出的最新节点数量。")] = None,
        since: Annotated[Optional[str], typer.Option("--since", help="仅导出指定时间戳 (YYYY-MM-DD HH:MM) 之后的节点。")] = None,
        until: Annotated[Optional[str], typer.Option("--until", help="仅导出指定时间戳 (YYYY-MM-DD HH:MM) 之前的节点。")] = None,
        zip_output: Annotated[bool, typer.Option("--zip", help="将导出目录压缩成一个 .zip 文件。")] = False,
        no_nav: Annotated[bool, typer.Option("--no-nav", help="禁止在文件末尾生成导航栏。")] = False,
        no_frontmatter: Annotated[bool, typer.Option("--no-frontmatter", help="禁止在文件开头生成 YAML Frontmatter。")] = False,
    ):
        """
        将 Quipu 历史记录导出为一组人类可读的 Markdown 文件。
        """
        with engine_context(work_dir) as engine:
            if not engine.history_graph:
                typer.secho("📜 历史记录为空，无需导出。", fg=typer.colors.YELLOW, err=True)
                ctx.exit(0)

            # 1. 获取并排序所有节点 (时间倒序)
            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)

            # 2. 过滤节点
            try:
                nodes_to_export = _filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                typer.secho(f"❌ 参数错误: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)

            if not nodes_to_export:
                typer.secho("🤷 未找到符合条件的节点进行导出。", fg=typer.colors.YELLOW, err=True)
                ctx.exit(0)

            # 3. 创建输出目录
            output_dir.mkdir(parents=True, exist_ok=True)
            typer.secho(f"🚀 正在导出 {len(nodes_to_export)} 个节点到 '{output_dir}'...", fg=typer.colors.BLUE, err=True)

            # 4. 导出循环
            with typer.progressbar(nodes_to_export, label="导出进度") as progress:
                for node in progress:
                    filename = _generate_filename(node)
                    content = _generate_file_content(node, engine, no_frontmatter, no_nav)
                    
                    filepath = output_dir / filename
                    filepath.write_text(content, encoding="utf-8")

            typer.secho(f"\n✅ 导出成功完成。", fg=typer.colors.GREEN, err=True)
~~~~~

### 下一步建议
核心功能已实现。现在我们可以专注于最后的高级功能：
1.  **导航栏生成**: 实现一个 `_generate_navbar` 函数，它需要能够查找父节点、子节点、总结节点和分支点，并生成对应的 Markdown 链接。
2.  **压缩功能**: 在导出循环结束后，如果 `--zip` 选项被激活，则调用 `shutil` 模块将输出目录压缩成一个 zip 文件。

如果你同意，我将开始实现导航栏的生成逻辑。
