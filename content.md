好的，我们继续执行重构计划。现在进入第五阶段，处理核心的 `navigation` 命令。这是一个涉及多个命令和复杂用户反馈的模块，是展示 `MessageBus` 优势的关键步骤。

## [WIP] refactor: 将 `navigation` 命令的输出迁移到 MessageBus

### 用户需求
根据 `MessageBus` 重构计划，需要将 `quipu` 的所有导航相关命令 (`checkout`, `undo`, `redo`, `prev`, `next`, `back`, `forward`) 及其辅助函数中的用户界面输出，从硬编码的 `typer.secho` 调用迁移到标准化的 `MessageBus` 服务。同时，更新相关的测试用例以验证语义消息调用，而非具体的输出字符串。

### 评论
导航是 `Quipu` 交互的核心，其输出信息的清晰度和一致性至关重要。将这部分逻辑迁移到 `MessageBus`，不仅能统一用户体验，还能极大地简化代码，将复杂的 `typer.secho` 调用链替换为清晰的、自解释的 `bus` 方法调用。重构测试用例将确保这一核心功能的稳定性和正确性。

### 目标
1.  在 `locales/zh/cli.json` 中添加 `navigation` 命令所需的所有消息模板。
2.  修改 `packages/quipu-cli/src/quipu/cli/commands/helpers.py`，用 `bus` 调用替换所有 `typer.secho`。
3.  修改 `packages/quipu-cli/src/quipu/cli/commands/navigation.py`，用 `bus` 调用替换所有 `typer.secho`。
4.  重写 `tests/cli/test_navigation_commands.py`，使用 `unittest.mock` 注入 `mock_bus` 并断言其方法调用。

### 基本原理
我们将首先在 `locales` 层定义好所有导航相关的消息文案，为重构提供“弹药”。接着，自底向上地修改代码：先是所有导航命令都依赖的 `helpers.py`，然后是 `navigation.py` 本身。通过这种方式，我们可以确保所有依赖路径都被覆盖。最后，重写测试用例，将它们从对 UI 输出的脆弱依赖中解放出来，转而验证更稳定、更具业务意义的 `MessageBus` 事件。

### 标签
#intent/refine #flow/ready #priority/high #comp/cli #comp/tests #concept/navigation #scope/core #ai/instruct #task/domain/cli #task/object/message-bus #task/action/refactor #task/state/continue #task/status/active

---

### Script

#### Acts 1: 定义消息模板

我们在 `locales/zh/cli.json` 中为 `navigation` 组件添加所有需要的消息。

```````act
patch_file
locales/zh/cli.json
```````
```````json
  "cache.rebuild.info.deleting": "🗑️  旧数据库已删除。",
  "cache.rebuild.error.deleteFailed": "❌ 删除旧数据库失败: {error}",
  "workspace.save.success": "📸 快照已保存: {short_hash}{msg_suffix}",
  "workspace.save.noChanges": "✅ 工作区状态未发生变化，无需创建快照。",
  "workspace.save.error": "❌ 创建快照失败: {error}",
```````
```````json
  "cache.rebuild.info.deleting": "🗑️  旧数据库已删除。",
  "cache.rebuild.error.deleteFailed": "❌ 删除旧数据库失败: {error}",
  "navigation.info.navigating": "🚀 正在导航到节点: {short_hash}",
  "navigation.success.visit": "✅ 已成功切换到状态 {short_hash}。",
  "navigation.error.generic": "❌ 导航操作失败: {error}",
  "navigation.warning.workspaceDirty": "⚠️  当前工作区状态未在历史中找到，或存在未保存的变更。",
  "navigation.info.saveHint": "💡  请先运行 'quipu save' 创建一个快照，再进行导航。",
  "navigation.checkout.error.notFound": "❌ 错误: 未找到 output_tree 哈希前缀为 '{hash_prefix}' 的历史节点。",
  "navigation.checkout.error.notUnique": "❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {count} 个节点。",
  "navigation.checkout.info.noAction": "✅ 工作区已处于目标状态 ({short_hash})，无需操作。",
  "navigation.checkout.info.capturingDrift": "⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...",
  "navigation.checkout.success.driftCaptured": "✅ 变更已捕获。",
  "navigation.checkout.ui.diffHeader": "\n以下是将要发生的变更:",
  "navigation.undo.atRoot": "✅ 已在历史根节点。",
  "navigation.undo.reachedRoot": "✅ 已到达历史根节点 (移动了 {steps} 步)。",
  "navigation.redo.atEnd": "✅ 已在分支末端。",
  "navigation.redo.reachedEnd": "✅ 已到达分支末端 (移动了 {steps} 步)。",
  "navigation.redo.info.multiBranch": "💡 当前节点有多个分支，已自动选择最新分支 -> {short_hash}",
  "navigation.prev.noSiblings": "✅ 当前节点没有兄弟分支。",
  "navigation.prev.atOldest": "✅ 已在最旧的兄弟分支。",
  "navigation.next.noSiblings": "✅ 当前节点没有兄弟分支。",
  "navigation.next.atNewest": "✅ 已在最新的兄弟分支。",
  "navigation.back.success": "✅ 已后退到状态: {short_hash}",
  "navigation.back.atStart": "⚠️  已到达访问历史的起点。",
  "navigation.back.error": "❌ 后退操作失败: {error}",
  "navigation.forward.success": "✅ 已前进到状态: {short_hash}",
  "navigation.forward.atEnd": "⚠️  已到达访问历史的终点。",
  "navigation.forward.error": "❌ 前进操作失败: {error}",
  "workspace.save.success": "📸 快照已保存: {short_hash}{msg_suffix}",
  "workspace.save.noChanges": "✅ 工作区状态未发生变化，无需创建快照。",
  "workspace.save.error": "❌ 创建快照失败: {error}",
```````

#### Acts 2: 重构 `helpers.py`

我们首先重构被 `navigation.py` 广泛使用的辅助函数。

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/helpers.py
```````
```````python
import typer
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine

from ..factory import create_engine
from ..logger_config import setup_logging
```````
```````python
import typer
from quipu.interfaces.models import QuipuNode
from quipu.engine.state_machine import Engine

from ..factory import create_engine
from ..logger_config import setup_logging
from quipu.common.messaging import bus
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/helpers.py
```````
```````python
    for node in graph.values():
        if node.output_tree == current_hash:
            return node

    typer.secho("⚠️  当前工作区状态未在历史中找到，或存在未保存的变更。", fg=typer.colors.YELLOW, err=True)
    typer.secho("💡  请先运行 'quipu save' 创建一个快照，再进行导航。", fg=typer.colors.YELLOW, err=True)
    return None
```````
```````python
    for node in graph.values():
        if node.output_tree == current_hash:
            return node

    bus.warning("navigation.warning.workspaceDirty")
    bus.info("navigation.info.saveHint")
    return None
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/helpers.py
```````
```````python
def _execute_visit(ctx: typer.Context, engine: Engine, target_hash: str, description: str):
    """辅助函数：执行 engine.visit 并处理结果"""
    typer.secho(f"🚀 {description}", err=True)
    try:
        engine.visit(target_hash)
        typer.secho(f"✅ 已成功切换到状态 {target_hash[:7]}。", fg=typer.colors.GREEN, err=True)
    except Exception as e:
        logger.error(f"导航操作失败 (目标哈希: {target_hash[:12]})", exc_info=True)
        typer.secho(f"❌ 导航操作失败: {e}", fg=typer.colors.RED, err=True)
        ctx.exit(1)
```````
```````python
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
```````

#### Acts 3: 重构 `navigation.py`

现在，我们对 `navigation.py` 文件进行全面的 `MessageBus` 迁移。

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
import typer

from .helpers import engine_context, _find_current_node, _execute_visit
from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
```````
```````python
import typer

from .helpers import engine_context, _find_current_node, _execute_visit
from ..config import DEFAULT_WORK_DIR
from ..ui_utils import prompt_for_confirmation
from quipu.common.messaging import bus
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
            matches = [node for node in graph.values() if node.output_tree.startswith(hash_prefix)]
            if not matches:
                typer.secho(
                    f"❌ 错误: 未找到 output_tree 哈希前缀为 '{hash_prefix}' 的历史节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)
            if len(matches) > 1:
                typer.secho(
                    f"❌ 错误: 哈希前缀 '{hash_prefix}' 不唯一，匹配到 {len(matches)} 个节点。",
                    fg=typer.colors.RED,
                    err=True,
                )
                ctx.exit(1)
            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree

            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_output_tree_hash:
                typer.secho(
                    f"✅ 工作区已处于目标状态 ({target_node.short_hash})，无需操作。", fg=typer.colors.GREEN, err=True
                )
                ctx.exit(0)

            is_dirty = engine.current_node is None or engine.current_node.output_tree != current_hash
            if is_dirty:
                typer.secho(
                    "⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...", fg=typer.colors.YELLOW, err=True
                )
                engine.capture_drift(current_hash)
                typer.secho("✅ 变更已捕获。", fg=typer.colors.GREEN, err=True)
                current_hash = engine.git_db.get_tree_hash()

            diff_stat = engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)
            if diff_stat:
                typer.secho("\n以下是将要发生的变更:", fg=typer.colors.YELLOW, err=True)
                typer.secho("-" * 20, err=True)
                typer.echo(diff_stat, err=True)
                typer.secho("-" * 20, err=True)

            if not force:
                prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
                if not prompt_for_confirmation(prompt, default=False):
                    typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
                    raise typer.Abort()

            _execute_visit(ctx, engine, target_output_tree_hash, f"正在导航到节点: {target_node.short_hash}")
```````
```````python
            matches = [node for node in graph.values() if node.output_tree.startswith(hash_prefix)]
            if not matches:
                bus.error("navigation.checkout.error.notFound", hash_prefix=hash_prefix)
                ctx.exit(1)
            if len(matches) > 1:
                bus.error("navigation.checkout.error.notUnique", hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)
            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree

            current_hash = engine.git_db.get_tree_hash()
            if current_hash == target_output_tree_hash:
                bus.success("navigation.checkout.info.noAction", short_hash=target_node.short_hash)
                ctx.exit(0)

            is_dirty = engine.current_node is None or engine.current_node.output_tree != current_hash
            if is_dirty:
                bus.warning("navigation.checkout.info.capturingDrift")
                engine.capture_drift(current_hash)
                bus.success("navigation.checkout.success.driftCaptured")
                current_hash = engine.git_db.get_tree_hash()

            diff_stat = engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)
            if diff_stat:
                bus.info("navigation.checkout.ui.diffHeader")
                typer.secho("-" * 20, err=True)
                typer.echo(diff_stat, err=True)
                typer.secho("-" * 20, err=True)

            if not force:
                prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
                if not prompt_for_confirmation(prompt, default=False):
                    bus.warning("common.prompt.cancel")
                    raise typer.Abort()

            _execute_visit(
                ctx,
                engine,
                target_output_tree_hash,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
            target_node = current_node
            for i in range(count):
                if not target_node.parent:
                    msg = f"已到达历史根节点 (移动了 {i} 步)。" if i > 0 else "已在历史根节点。"
                    typer.secho(f"✅ {msg}", fg=typer.colors.GREEN, err=True)
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.parent

            _execute_visit(ctx, engine, target_node.output_tree, f"正在撤销到父节点: {target_node.short_hash}")
```````
```````python
            target_node = current_node
            for i in range(count):
                if not target_node.parent:
                    if i > 0:
                        bus.success("navigation.undo.reachedRoot", steps=i)
                    else:
                        bus.success("navigation.undo.atRoot")
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.parent

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
            target_node = current_node
            for i in range(count):
                if not target_node.children:
                    msg = f"已到达分支末端 (移动了 {i} 步)。" if i > 0 else "已在分支末端。"
                    typer.secho(f"✅ {msg}", fg=typer.colors.GREEN, err=True)
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.children[-1]
                if len(current_node.children) > 1:
                    typer.secho(
                        f"💡 当前节点有多个分支，已自动选择最新分支 -> {target_node.short_hash}",
                        fg=typer.colors.YELLOW,
                        err=True,
                    )

            _execute_visit(ctx, engine, target_node.output_tree, f"正在重做到子节点: {target_node.short_hash}")
```````
```````python
            target_node = current_node
            for i in range(count):
                if not target_node.children:
                    if i > 0:
                        bus.success("navigation.redo.reachedEnd", steps=i)
                    else:
                        bus.success("navigation.redo.atEnd")
                    if target_node == current_node:
                        ctx.exit(0)
                    break
                target_node = target_node.children[-1]
                if len(current_node.children) > 1:
                    bus.info("navigation.redo.info.multiBranch", short_hash=target_node.short_hash)

            _execute_visit(
                ctx,
                engine,
                target_node.output_tree,
                "navigation.info.navigating",
                short_hash=target_node.short_hash,
            )
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
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
                _execute_visit(
                    ctx, engine, target_node.output_tree, f"正在切换到上一个兄弟节点: {target_node.short_hash}"
                )
```````
```````python
            siblings = current_node.siblings
            if len(siblings) <= 1:
                bus.success("navigation.prev.noSiblings")
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == 0:
                    bus.success("navigation.prev.atOldest")
                    ctx.exit(0)
                target_node = siblings[idx - 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    "navigation.info.navigating",
                    short_hash=target_node.short_hash,
                )
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
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
                _execute_visit(
                    ctx, engine, target_node.output_tree, f"正在切换到下一个兄弟节点: {target_node.short_hash}"
                )
```````
```````python
            siblings = current_node.siblings
            if len(siblings) <= 1:
                bus.success("navigation.next.noSiblings")
                ctx.exit(0)
            try:
                idx = siblings.index(current_node)
                if idx == len(siblings) - 1:
                    bus.success("navigation.next.atNewest")
                    ctx.exit(0)
                target_node = siblings[idx + 1]
                _execute_visit(
                    ctx,
                    engine,
                    target_node.output_tree,
                    "navigation.info.navigating",
                    short_hash=target_node.short_hash,
                )
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.back()
                if result_hash:
                    typer.secho(f"✅ 已后退到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
                else:
                    typer.secho("⚠️  已到达访问历史的起点。", fg=typer.colors.YELLOW, err=True)
            except Exception as e:
                logger.error("后退操作失败", exc_info=True)
                typer.secho(f"❌ 后退操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
```````
```````python
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.back()
                if result_hash:
                    bus.success("navigation.back.success", short_hash=result_hash[:7])
                else:
                    bus.warning("navigation.back.atStart")
            except Exception as e:
                logger.error("后退操作失败", exc_info=True)
                bus.error("navigation.back.error", error=str(e))
                ctx.exit(1)
```````

```````act
patch_file
packages/quipu-cli/src/quipu/cli/commands/navigation.py
```````
```````python
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.forward()
                if result_hash:
                    typer.secho(f"✅ 已前进到状态: {result_hash[:7]}", fg=typer.colors.GREEN, err=True)
                else:
                    typer.secho("⚠️  已到达访问历史的终点。", fg=typer.colors.YELLOW, err=True)
            except Exception as e:
                logger.error("前进操作失败", exc_info=True)
                typer.secho(f"❌ 前进操作失败: {e}", fg=typer.colors.RED, err=True)
                ctx.exit(1)
```````
```````python
        with engine_context(work_dir) as engine:
            try:
                result_hash = engine.forward()
                if result_hash:
                    bus.success("navigation.forward.success", short_hash=result_hash[:7])
                else:
                    bus.warning("navigation.forward.atEnd")
            except Exception as e:
                logger.error("前进操作失败", exc_info=True)
                bus.error("navigation.forward.error", error=str(e))
                ctx.exit(1)
```````

#### Acts 4: 重构测试用例

最后，我们重写 `test_navigation_commands.py`，以适应新的 `MessageBus` 架构。

```````act
write_file
tests/cli/test_navigation_commands.py
```````
```````python
import pytest
from unittest.mock import MagicMock, ANY
from quipu.cli.main import app


@pytest.fixture
def populated_workspace(quipu_workspace):
    ws, _, engine = quipu_workspace

    (ws / "a.txt").write_text("A")
    hash_a = engine.git_db.get_tree_hash()
    engine.create_plan_node(
        input_tree="_" * 40, output_tree=hash_a, plan_content="Plan A", summary_override="State A"
    )

    (ws / "b.txt").write_text("B")
    (ws / "a.txt").unlink()
    hash_b = engine.git_db.get_tree_hash()
    engine.create_plan_node(
        input_tree=hash_a, output_tree=hash_b, plan_content="Plan B", summary_override="State B"
    )

    return ws, hash_a, hash_b


def test_cli_back_forward_flow(runner, populated_workspace, monkeypatch):
    workspace, hash_a, hash_b = populated_workspace
    mock_bus_nav = MagicMock()
    mock_bus_helper = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.navigation.bus", mock_bus_nav)
    monkeypatch.setattr("quipu.cli.commands.helpers.bus", mock_bus_helper)

    # Initial state is B. Let's checkout to A.
    runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])
    assert (workspace / "a.txt").exists()
    assert not (workspace / "b.txt").exists()

    # Now we are at A. Let's go back. It should go to the previous state (B).
    result_back = runner.invoke(app, ["back", "-w", str(workspace)])
    assert result_back.exit_code == 0
    mock_bus_nav.success.assert_called_with("navigation.back.success", short_hash=ANY)
    assert (workspace / "b.txt").exists()
    assert not (workspace / "a.txt").exists()

    # Now we are back at B. Let's go forward to A again.
    result_fwd = runner.invoke(app, ["forward", "-w", str(workspace)])
    assert result_fwd.exit_code == 0
    mock_bus_nav.success.assert_called_with("navigation.forward.success", short_hash=ANY)
    assert (workspace / "a.txt").exists()
    assert not (workspace / "b.txt").exists()


def test_cli_boundary_messages(runner, populated_workspace, monkeypatch):
    workspace, hash_a, hash_b = populated_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.navigation.bus", mock_bus)

    # Go to a known state
    runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])

    # Back until the beginning
    runner.invoke(app, ["back", "-w", str(workspace)])  # to B
    runner.invoke(app, ["back", "-w", str(workspace)])
    result2 = runner.invoke(app, ["back", "-w", str(workspace)])  # one more should hit boundary
    assert result2.exit_code == 0
    mock_bus.warning.assert_called_with("navigation.back.atStart")

    # Forward until the end
    runner.invoke(app, ["forward", "-w", str(workspace)])  # to B
    runner.invoke(app, ["forward", "-w", str(workspace)])  # to A
    result3 = runner.invoke(app, ["forward", "-w", str(workspace)])
    assert result3.exit_code == 0
    mock_bus.warning.assert_called_with("navigation.forward.atEnd")


def test_checkout_not_found(runner, populated_workspace, monkeypatch):
    workspace, _, _ = populated_workspace
    mock_bus = MagicMock()
    monkeypatch.setattr("quipu.cli.commands.navigation.bus", mock_bus)

    result = runner.invoke(app, ["checkout", "nonexistent", "-w", str(workspace)])
    assert result.exit_code == 1
    mock_bus.error.assert_called_once_with("navigation.checkout.error.notFound", hash_prefix="nonexistent")
```````

### 下一步建议
我们已经成功完成了对核心导航命令的 `MessageBus` 迁移，这是整个重构计划中最复杂的部分之一。代码的可读性和可测试性得到了显著提升。

下一个合乎逻辑的步骤是处理**核心执行命令 (`run`, `axon`)**。这两个命令是 `Quipu` 系统的主要入口点，重构它们将使整个 CLI 的用户输出体验趋于一致。之后，我们将只剩下一些独立的、外围的命令需要处理。
