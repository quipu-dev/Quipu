好的，我理解了问题所在。`axon log` 的摘要信息确实不够清晰，而且在空仓库中首次运行时不应该创建一个 `CAPTURE` 节点，这违背了“创世状态是已知的干净状态”这一原则。

我将分两步解决这两个问题：
1.  **修复创世节点 Bug**：我会修改 `core/engine.py` 和 `core/controller.py`，让引擎正确识别空的 Git 仓库为一个干净的初始状态，从而避免不必要的 `CAPTURE`。
2.  **优化日志摘要**：我会重写 `main.py` 中的 `log` 命令函数，让它能更智能地解析 `PLAN` 和 `CAPTURE` 节点的内容，以展示更有价值的摘要信息。

请执行以下指令来应用修复：

### 第 1 步：修复创世节点 Bug

首先，我们需要教 `Engine` 识别空的 Git 仓库。

~~~act
replace
~~~
~~~path
core/engine.py
~~~
~~~python
    def align(self) -> str:
        """
        核心对齐方法：确定 "我现在在哪"。
        
        1. 加载历史图谱。
        2. 计算当前工作区的 Tree Hash。
        3. 在图谱中查找该 Hash。
        
        返回状态: "CLEAN", "DIRTY", "ORPHAN"
        """
        # 1. 加载或重新加载历史
        self.history_graph = load_history_graph(self.history_dir)
        
        # 2. 获取当前物理状态
        current_hash = self.git_db.get_tree_hash()
        
        # 3. 在逻辑图谱中定位
        if current_hash in self.history_graph:
            self.current_node = self.history_graph[current_hash]
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            return "CLEAN"
        
        # 未找到匹配节点，进入漂移检测
        # (后续将实现 Capture 逻辑)
        logger.warning(f"⚠️  状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        
        if not self.history_graph:
            return "ORPHAN" # 历史为空，无法判断从何而来
        
        return "DIRTY"
~~~
~~~python
    def align(self) -> str:
        """
        核心对齐方法：确定 "我现在在哪"。
        
        1. 加载历史图谱。
        2. 计算当前工作区的 Tree Hash。
        3. 在图谱中查找该 Hash。
        
        返回状态: "CLEAN", "DIRTY", "ORPHAN"
        """
        # 1. 加载或重新加载历史
        self.history_graph = load_history_graph(self.history_dir)
        
        # 2. 获取当前物理状态
        current_hash = self.git_db.get_tree_hash()

        # 3. 特殊情况：处理创世状态 (空仓库)
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        if current_hash == EMPTY_TREE_HASH and not self.history_graph:
            logger.info("✅ 状态对齐：检测到创世状态 (空仓库)。")
            self.current_node = None # 此时没有物理节点
            return "CLEAN"
        
        # 4. 在逻辑图谱中定位
        if current_hash in self.history_graph:
            self.current_node = self.history_graph[current_hash]
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            return "CLEAN"
        
        # 未找到匹配节点，进入漂移检测
        logger.warning(f"⚠️  状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        
        if not self.history_graph:
            return "ORPHAN" # 历史为空，但工作区非空
        
        return "DIRTY"
~~~

接着，我们需要让 `Controller` 能够处理 `align` 返回 `CLEAN` 但 `current_node` 为 `None` 的创世情况。

~~~act
replace
~~~
~~~path
core/controller.py
~~~
~~~python
        # 记录执行前的状态，作为 Plan 的 input_tree
        if not engine.current_node:
             # 理论上 capture_drift 后一定有 node，除非极端的 git 错误
             raise RuntimeError("Engine failed to lock state.")
             
        input_tree_hash = engine.current_node.output_tree
~~~
~~~python
        # 记录执行前的状态，作为 Plan 的 input_tree
        if engine.current_node:
            input_tree_hash = engine.current_node.output_tree
        else:
            # 此处处理创世状态：当 align() 返回 CLEAN 但 current_node 为 None 时。
            # 输入哈希就是当前的（空的）哈希。
            input_tree_hash = current_hash
~~~

### 第 2 步：优化 `axon log` 的输出摘要

现在，我们替换 `main.py` 中的 `log` 函数，使其能够提取更有意义的信息。

~~~act
replace
~~~
~~~path
main.py
~~~
~~~python
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
    
    history_dir = work_dir.resolve() / ".axon" / "history"
    if not history_dir.exists():
        typer.secho(f"❌ 在 '{work_dir}' 中未找到 Axon 历史记录 (.axon/history)。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    graph = load_history_graph(history_dir)
    if not graph:
        typer.secho("📜 历史记录为空。", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(0)
        
    # 按时间戳降序排序
    nodes = sorted(graph.values(), key=lambda n: n.timestamp, reverse=True)
    
    typer.secho("--- Axon History Log ---", bold=True, err=True)
    for node in nodes:
        ts = node.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # 颜色和标签
        color = typer.colors.CYAN if node.node_type == "plan" else typer.colors.MAGENTA
        tag = f"[{node.node_type.upper()}]"
        
        # 摘要
        first_line = node.content.strip().split('\n')[0]
        # 尝试从 plan 中提取 act 名称作为摘要
        if node.node_type == 'plan' and 'act' in first_line:
            summary = first_line
        else:
             summary = (first_line[:70] + '...') if len(first_line) > 70 else first_line


        typer.secho(f"{ts} {tag:<9} {node.short_hash}", fg=color, nl=False, err=True)
        typer.echo(f" - {summary}", err=True)
~~~
~~~python
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
    
    history_dir = work_dir.resolve() / ".axon" / "history"
    if not history_dir.exists():
        typer.secho(f"❌ 在 '{work_dir}' 中未找到 Axon 历史记录 (.axon/history)。", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)

    graph = load_history_graph(history_dir)
    if not graph:
        typer.secho("📜 历史记录为空。", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(0)
        
    # 按时间戳降序排序
    nodes = sorted(graph.values(), key=lambda n: n.timestamp, reverse=True)
    
    typer.secho("--- Axon History Log ---", bold=True, err=True)
    for node in nodes:
        ts = node.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        color = typer.colors.CYAN if node.node_type == "plan" else typer.colors.MAGENTA
        tag = f"[{node.node_type.upper()}]"
        
        summary = ""
        content_lines = node.content.strip().split('\n')
        
        if node.node_type == 'plan':
            # 查找第一个非空的 act 内容行作为摘要
            in_act_block = False
            for line in content_lines:
                if line.strip().startswith(('~~~act', '```act')):
                    in_act_block = True
                    continue
                if in_act_block and line.strip():
                    summary = line.strip()
                    break
            if not summary:
                summary = "Plan executed" # Fallback
        
        elif node.node_type == 'capture':
            # 查找 diff 摘要
            in_diff_block = False
            diff_summary_lines = []
            for line in content_lines:
                if "变更文件摘要" in line:
                    in_diff_block = True
                    continue
                if in_diff_block and line.strip().startswith('```'):
                    break # 结束块
                if in_diff_block and line.strip():
                    diff_summary_lines.append(line.strip())
            
            if diff_summary_lines:
                # 只显示文件名和变更统计，忽略插入/删除行数
                files_changed = [l.split('|')[0].strip() for l in diff_summary_lines]
                summary = f"Changes captured in: {', '.join(files_changed)}"
            else:
                summary = "Workspace changes captured" # Fallback

        summary = (summary[:75] + '...') if len(summary) > 75 else summary

        typer.secho(f"{ts} {tag:<9} {node.short_hash}", fg=color, nl=False, err=True)
        typer.echo(f" - {summary}", err=True)
~~~

---

执行以上指令后，创世节点问题和日志摘要问题应该都已解决。你可以在一个新的空目录中再次运行 `git init` 和 `axon run ...` 来验证修复效果。