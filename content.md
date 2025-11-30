好的，我理解了你的需求。你需要为 `quipu log` 命令添加与 `quipu export` 类似的过滤功能（如 `since`, `until`, `limit`），并且严格遵循 DRY（Don't Repeat Yourself）原则，将通过重构将共用的过滤逻辑提取出来。

这是一个典型的重构加新功能的任务。

## [WIP] feat(cli): 为 log 命令实现筛选逻辑并重构公共代码

### 用户需求
1.  **功能增强**: `quipu log` 命令需要支持按时间范围 (`--since`, `--until`) 和数量 (`--limit`) 过滤输出结果。
2.  **代码质量**: 遵循 DRY 原则，避免在 `log` 和 `export` 命令之间复制粘贴过滤逻辑。需将原有的 `_filter_nodes` 逻辑提取为公共组件。

### 评论
这是一个非常合理的改进。`log` 命令作为查看历史的主要入口，随着历史记录的增长，缺乏过滤功能会使其可用性降低。同时，将过滤逻辑集中管理可以确保两个命令在处理时间戳格式和边界条件时行为一致。

### 目标
1.  在 `packages/quipu-cli/src/pyquipu/cli/commands/helpers.py` 中实现通用的 `filter_nodes` 函数。
2.  重构 `export.py`，移除其私有的 `_filter_nodes`，改为调用公共辅助函数。
3.  修改 `query.py` 中的 `log` 命令，添加参数并集成过滤逻辑。
4.  更新测试以验证 `log` 命令的过滤功能。

### 基本原理
我们将把原本紧耦合在 `export.py` 中的过滤逻辑（时间解析、列表切片）剥离出来。需要注意的是，`export` 命令为了按时间正序生成文件/导航，原逻辑在过滤后进行了 `reversed()` 操作。而 `log` 命令通常期望逆序（最新在前）。因此，公共的 `filter_nodes` 函数应只负责“过滤”，不负责“排序”，排序逻辑由调用者根据业务需求决定。

### 标签
#intent/build #intent/refine #flow/ready #priority/medium #comp/cli #concept/history #scope/ux #scope/dx #ai/instruct #task/domain/cli #task/object/log-command #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 提取公共过滤逻辑到 `helpers.py`

我们将把过滤逻辑移动到 `helpers.py`。这需要引入 `datetime` 和 `typer` 等依赖。

~~~~~act
write_file packages/quipu-cli/src/pyquipu/cli/commands/helpers.py
~~~~~
~~~~~python
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

import typer
from pyquipu.common.messaging import bus
from pyquipu.engine.state_machine import Engine
from pyquipu.interfaces.models import QuipuNode

from ..factory import create_engine
from ..logger_config import setup_logging

logger = logging.getLogger(__name__)


@contextmanager
def engine_context(work_dir: Path) -> Generator[Engine, None, None]:
    """Context manager to set up logging, create, and automatically close a Quipu engine."""
    setup_logging()
    engine = None
    try:
        engine = create_engine(work_dir)
        yield engine
    finally:
        if engine:
            engine.close()


def _find_current_node(engine: Engine, graph: Dict[str, QuipuNode]) -> Optional[QuipuNode]:
    """在图中查找与当前工作区状态匹配的节点"""
    current_hash = engine.git_db.get_tree_hash()
    # 修复：直接从 graph 中通过 output_tree hash 查找
    for node in graph.values():
        if node.output_tree == current_hash:
            return node

    bus.warning("navigation.warning.workspaceDirty")
    bus.info("navigation.info.saveHint")
    return None


def _execute_visit(ctx: typer.Context, engine: Engine, target_hash: str, msg_id: str, **kwargs):
    """辅助函数：执行 engine.visit 并处理结果"""
    bus.info(msg_id, **kwargs)
    try:
        engine.visit(target_hash)
        bus.success("navigation.success.visit", short_hash=target_hash[:7])
    except Exception as e:
        logger.error(f"导航操作失败 (目标哈希: {target_hash[:12]})", exc_info=True)
        bus.error("navigation.error.generic", error=str(e))
        ctx.exit(1)


def filter_nodes(
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
    return filtered
~~~~~

#### Acts 2: 重构 `export.py` 使用公共逻辑

我们需要删除本地的 `_filter_nodes` 并导入新的 helper。注意保持原有的 `reversed` 逻辑，因为 `filter_nodes` 现在返回输入顺序（通常是逆序），而 `export` 需要正序处理。

~~~~~act
patch_file packages/quipu-cli/src/pyquipu/cli/commands/export.py
~~~~~
~~~~~python
from datetime import datetime
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set

import typer
import yaml
from pyquipu.common.messaging import bus
from pyquipu.engine.state_machine import Engine
from pyquipu.interfaces.models import QuipuNode

from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from .helpers import engine_context
~~~~~
~~~~~python
import logging
import re
import shutil
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set

import typer
import yaml
from pyquipu.common.messaging import bus
from pyquipu.engine.state_machine import Engine
from pyquipu.interfaces.models import QuipuNode

from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from .helpers import engine_context, filter_nodes
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/pyquipu/cli/commands/export.py
~~~~~
~~~~~python
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
~~~~~
~~~~~python
    return f"---\n{yaml_str}---"


def _generate_navbar(
    current_node: QuipuNode,
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/pyquipu/cli/commands/export.py
~~~~~
~~~~~python
            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                nodes_to_export = _filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                bus.error("export.error.badParam", error=str(e))
                ctx.exit(1)
~~~~~
~~~~~python
            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                # filter_nodes returns preserving input order (reverse chrono),
                # but export expects chronological order for file generation/processing
                filtered = filter_nodes(all_nodes, limit, since, until)
                nodes_to_export = list(reversed(filtered))
            except typer.BadParameter as e:
                bus.error("export.error.badParam", error=str(e))
                ctx.exit(1)
~~~~~

#### Acts 3: 更新 `query.py` 以支持过滤

在 `log` 命令中添加参数并调用 `filter_nodes`。

~~~~~act
patch_file packages/quipu-cli/src/pyquipu/cli/commands/query.py
~~~~~
~~~~~python
from ..config import DEFAULT_WORK_DIR
from .helpers import engine_context
~~~~~
~~~~~python
from ..config import DEFAULT_WORK_DIR
from .helpers import engine_context, filter_nodes
~~~~~

~~~~~act
patch_file packages/quipu-cli/src/pyquipu/cli/commands/query.py
~~~~~
~~~~~python
    @app.command()
    def log(
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        json_output: Annotated[bool, typer.Option("--json", help="以 JSON 格式输出结果。")] = False,
    ):
        """
        显示 Quipu 历史图谱日志。
        """
        with engine_context(work_dir) as engine:
            graph = engine.history_graph

            if not graph:
                if json_output:
                    bus.data("[]")
                else:
                    bus.info("query.info.emptyHistory")
                raise typer.Exit(0)

            nodes = sorted(graph.values(), key=lambda n: n.timestamp, reverse=True)

            if json_output:
                bus.data(_nodes_to_json_str(nodes))
                raise typer.Exit(0)

            bus.info("query.log.ui.header")
            for node in nodes:
~~~~~
~~~~~python
    @app.command()
    def log(
        ctx: typer.Context,
        work_dir: Annotated[
            Path,
            typer.Option(
                "--work-dir", "-w", help="操作执行的根目录（工作区）", file_okay=False, dir_okay=True, resolve_path=True
            ),
        ] = DEFAULT_WORK_DIR,
        limit: Annotated[Optional[int], typer.Option("--limit", "-n", help="限制显示的节点数量。")] = None,
        since: Annotated[Optional[str], typer.Option("--since", help="起始时间戳 (YYYY-MM-DD HH:MM)。")] = None,
        until: Annotated[Optional[str], typer.Option("--until", help="截止时间戳 (YYYY-MM-DD HH:MM)。")] = None,
        json_output: Annotated[bool, typer.Option("--json", help="以 JSON 格式输出结果。")] = False,
    ):
        """
        显示 Quipu 历史图谱日志。
        """
        with engine_context(work_dir) as engine:
            graph = engine.history_graph

            if not graph:
                if json_output:
                    bus.data("[]")
                else:
                    bus.info("query.info.emptyHistory")
                raise typer.Exit(0)

            all_nodes = sorted(graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                nodes = filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                bus.error("common.error.invalidConfig", error=str(e))
                ctx.exit(1)

            if not nodes:
                if json_output:
                    bus.data("[]")
                else:
                    bus.info("query.info.noResults")
                raise typer.Exit(0)

            if json_output:
                bus.data(_nodes_to_json_str(nodes))
                raise typer.Exit(0)

            bus.info("query.log.ui.header")
            for node in nodes:
~~~~~

#### Acts 4: 添加测试用例

在 `tests/cli/test_query_commands.py` 中添加针对 `log` 过滤功能的测试。

~~~~~act
patch_file tests/cli/test_query_commands.py
~~~~~
~~~~~python
    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.data.assert_called_once_with("[]")
~~~~~
~~~~~python
    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.data.assert_called_once_with("[]")


def test_log_filtering(runner, quipu_workspace, monkeypatch):
    """Test limit and time filtering logic for log command."""
    work_dir, _, engine = quipu_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("pyquipu.cli.commands.query.bus", mock_bus)

    # Create 3 nodes
    (work_dir / "f1").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 1")
    (work_dir / "f2").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 2")
    (work_dir / "f3").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 3")

    # 1. Test Limit
    result = runner.invoke(app, ["log", "-n", "1", "-w", str(work_dir)])
    assert result.exit_code == 0
    # Should only print header + 1 node
    assert mock_bus.data.call_count == 1
    assert "Node 3" in mock_bus.data.call_args_list[0].args[0]  # Newest

    # 2. Test Filtering Result Empty
    mock_bus.reset_mock()
    # Using a future date
    result = runner.invoke(app, ["log", "--since", "2099-01-01 00:00", "-w", str(work_dir)])
    assert result.exit_code == 0
    mock_bus.info.assert_called_with("query.info.noResults")
~~~~~

### 下一步建议
现在 `log` 和 `export` 共享了过滤逻辑。可以进一步检查 `find` 命令是否也需要类似的过滤机制，或者是否需要将 `limit` 参数在 `find` 中也标准化（目前 `find` 已有 limit 参数，但可以复用 helper）。目前 `find` 的主要逻辑是基于 regex 的，与单纯的列表切片略有不同，因此保持现状是可以接受的。

同时，由于 `log` 命令现在可能返回空结果（因为过滤），我们在 UI 反馈中添加了 `query.info.noResults` 的处理，这提升了用户体验。
