### fix: 在 checkout 命令中预览文件变更摘要

#### 用户需求
`qd discard` 命令会显示将要被丢弃的文件列表，但 `qd checkout` 在切换历史节点时，不会显示工作区将如何变化。用户希望在执行 `checkout` 前，能看到一份类似于 `git diff --stat` 的文件变更摘要。

#### 目标
在 `quipu checkout` 命令的交互式确认环节前，增加一个文件变更预览，告知用户哪些文件将被修改、添加或删除。

#### 基本原理
这个修改将复用 `discard` 命令中已有的实现逻辑。

1.  在 `checkout` 命令函数中，我们已经获取了当前工作区的状态哈希 (`current_hash`) 和目标节点的哈希 (`target_tree_hash`)。
2.  我们将使用 `engine.git_db.get_diff_stat(current_hash, target_tree_hash)` 来生成一份人类可读的差异统计报告。
3.  将这份报告输出到终端，展示在强制确认的提示信息之前，让用户可以明确感知此次操作的影响范围。
4.  这个功能不涉及文件内容的具体 `diff`，只提供文件列表和变更统计，保持了操作的轻量级。

#### 标签
 #feat #cli #ux

---

## Script

### Act 1: 为 `checkout` 命令添加变更预览功能

我将修改 `packages/quipu-cli/src/quipu/cli/main.py` 文件，在 `checkout` 函数中插入用于显示差异的代码块。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~

~~~~~python
    if status in ["DIRTY", "ORPHAN"]:
        typer.secho("⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...", fg=typer.colors.YELLOW, err=True)
        engine.capture_drift(current_hash)
        typer.secho("✅ 变更已捕获。", fg=typer.colors.GREEN, err=True)
    if not force:
        prompt = f"🚨 即将重置工作区到状态 {target_node.short_hash} ({target_node.timestamp})。\n此操作会覆盖未提交的更改。是否继续？"
        if not _prompt_for_confirmation(prompt, default=False):
            typer.secho("\n🚫 操作已取消。", fg=typer.colors.YELLOW, err=True)
            raise typer.Abort()
~~~~~

~~~~~python
    if status in ["DIRTY", "ORPHAN"]:
        typer.secho("⚠️  检测到当前工作区存在未记录的变更，将自动创建捕获节点...", fg=typer.colors.YELLOW, err=True)
        engine.capture_drift(current_hash)
        typer.secho("✅ 变更已捕获。", fg=typer.colors.GREEN, err=True)
        # 捕获后，当前 hash 已更新，重新获取以确保 diff 准确
        current_hash = engine.git_db.get_tree_hash()

    # 显示将要发生的变更
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
~~~~~