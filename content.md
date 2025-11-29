好的，我将为你添加一个 `--no-branch-link` 选项到 `quipu export` 命令中。

这个选项将允许你在导出历史记录时，禁用指向“上一分支点”的导航链接，以获得更简洁的输出。

## [WIP] feat(cli): 为 export 命令添加禁用分支点链接的选项

### 用户需求
用户需要在 `quipu export` 命令中增加一个命令行选项，用于在生成的 Markdown 文件导航栏中，禁用指向上一个分支点 (branch point) 的链接。

### 评论
这是一个很好的可用性改进。在某些场景下，例如线性的历史审查，用户可能只关心直接的父子关系，而“上一分支点”的链接可能会引入不必要的跳转，造成干扰。提供禁用选项可以使导航栏更聚焦于当前上下文。

### 目标
1.  在 `packages/quipu-cli/src/quipu/cli/commands/export.py` 的 `export_command` 函数中添加一个新的 `--no-branch-link` 布尔选项。
2.  将此选项的值向下传递给 `_generate_navbar` 辅助函数。
3.  在 `_generate_navbar` 函数中，根据此选项的值，条件性地跳过生成“上一分支点”链接的逻辑。
4.  在 `tests/cli/test_export_command.py` 中添加一个新的测试用例，以验证 `--no-branch-link` 选项的功能是否符合预期。

### 基本原理
通过 Typer 的 `Option` 装饰器，我们可以轻松地在 CLI 接口层添加新的标志。然后，通过函数参数将这个标志的状态（一个布尔值）逐层传递到负责生成导航栏的底层函数。在底层函数中，一个简单的 `if` 语句就可以控制相应链接的生成逻辑，从而实现所需的功能，同时保持代码的清晰和模块化。

### 标签
#intent/build #flow/ready #priority/medium #comp/cli #concept/navigation #scope/ux #ai/instruct #task/domain/cli #task/object/export-command #task/action/feature-enhancement #task/state/begin

---

### Script

#### Acts 1: 在 `export.py` 中实现新选项及逻辑

我们将分两步修改 `export.py`：首先添加新的 CLI 选项并将其传递给 `_generate_file_content`；然后修改 `_generate_navbar` 函数以响应这个新选项。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
        zip_output: Annotated[bool, typer.Option("--zip", help="压缩导出目录")] = False,
        no_nav: Annotated[bool, typer.Option("--no-nav", help="禁用导航栏")] = False,
        no_frontmatter: Annotated[bool, typer.Option("--no-frontmatter", help="禁用 Frontmatter")] = False,
    ):
        """将 Quipu 历史记录导出为一组人类可读的 Markdown 文件。"""
        with engine_context(work_dir) as engine:
            if not engine.history_graph:
                typer.secho("📜 历史记录为空，无需导出。", fg=typer.colors.YELLOW, err=True); ctx.exit(0)

            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                nodes_to_export = _filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                typer.secho(f"❌ 参数错误: {e}", fg=typer.colors.RED, err=True); ctx.exit(1)

            if not nodes_to_export:
                typer.secho("🤷 未找到符合条件的节点。", fg=typer.colors.YELLOW, err=True); ctx.exit(0)

            if output_dir.exists() and any(output_dir.iterdir()):
                if not typer.confirm(f"⚠️ 目录 '{output_dir}' 非空，是否清空并继续?", abort=True):
                    return
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            typer.secho(f"🚀 正在导出 {len(nodes_to_export)} 个节点到 '{output_dir}'...", fg=typer.colors.BLUE, err=True)

            # 预计算文件名和节点集合以供导航栏使用
            filename_map = {node.commit_hash: _generate_filename(node) for node in nodes_to_export}
            exported_hashes_set = {node.commit_hash for node in nodes_to_export}

            with typer.progressbar(nodes_to_export, label="导出进度") as progress:
                for node in progress:
                    filename = filename_map[node.commit_hash]
                    content = _generate_file_content(node, engine, no_frontmatter, no_nav, exported_hashes_set, filename_map)
                    (output_dir / filename).write_text(content, encoding="utf-8")

            if zip_output:
                typer.secho("📦 正在压缩导出文件...", fg=typer.colors.BLUE, err=True)
~~~~~
~~~~~python
        zip_output: Annotated[bool, typer.Option("--zip", help="压缩导出目录")] = False,
        no_nav: Annotated[bool, typer.Option("--no-nav", help="禁用导航栏")] = False,
        no_frontmatter: Annotated[bool, typer.Option("--no-frontmatter", help="禁用 Frontmatter")] = False,
        no_branch_link: Annotated[bool, typer.Option("--no-branch-link", help="禁用指向上一个分支点的导航链接。")] = False,
    ):
        """将 Quipu 历史记录导出为一组人类可读的 Markdown 文件。"""
        with engine_context(work_dir) as engine:
            if not engine.history_graph:
                typer.secho("📜 历史记录为空，无需导出。", fg=typer.colors.YELLOW, err=True); ctx.exit(0)

            all_nodes = sorted(engine.history_graph.values(), key=lambda n: n.timestamp, reverse=True)
            try:
                nodes_to_export = _filter_nodes(all_nodes, limit, since, until)
            except typer.BadParameter as e:
                typer.secho(f"❌ 参数错误: {e}", fg=typer.colors.RED, err=True); ctx.exit(1)

            if not nodes_to_export:
                typer.secho("🤷 未找到符合条件的节点。", fg=typer.colors.YELLOW, err=True); ctx.exit(0)

            if output_dir.exists() and any(output_dir.iterdir()):
                if not typer.confirm(f"⚠️ 目录 '{output_dir}' 非空，是否清空并继续?", abort=True):
                    return
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            typer.secho(f"🚀 正在导出 {len(nodes_to_export)} 个节点到 '{output_dir}'...", fg=typer.colors.BLUE, err=True)

            # 预计算文件名和节点集合以供导航栏使用
            filename_map = {node.commit_hash: _generate_filename(node) for node in nodes_to_export}
            exported_hashes_set = {node.commit_hash for node in nodes_to_export}

            with typer.progressbar(nodes_to_export, label="导出进度") as progress:
                for node in progress:
                    filename = filename_map[node.commit_hash]
                    content = _generate_file_content(
                        node, engine, no_frontmatter, no_nav, exported_hashes_set, filename_map, no_branch_link
                    )
                    (output_dir / filename).write_text(content, encoding="utf-8")

            if zip_output:
                typer.secho("📦 正在压缩导出文件...", fg=typer.colors.BLUE, err=True)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
def _generate_navbar(
    current_node: QuipuNode, exported_hashes_set: Set[str], filename_map: Dict[str, str]
) -> str:
    """生成导航栏 Markdown 字符串。"""
    nav_links = []

    # 1. 总结节点 (↑)
    ancestor = current_node.parent
    while ancestor:
        if ancestor.input_tree == ancestor.output_tree and ancestor.commit_hash in exported_hashes_set:
            nav_links.append(f"> ↑ [总结节点]({filename_map[ancestor.commit_hash]})")
            break
        ancestor = ancestor.parent

    # 2. 上一分支点 (↓)
    # Find the nearest ancestor that is a branch point.
    ancestor = current_node.parent
    found_branch_point = None
    while ancestor:
        if len(ancestor.children) > 1 and ancestor.commit_hash in exported_hashes_set:
            found_branch_point = ancestor
            break
        ancestor = ancestor.parent
    
    # Add the link only if a branch point was found AND it's not the direct parent
    # (to avoid a redundant link).
    if found_branch_point and current_node.parent and found_branch_point.commit_hash != current_node.parent.commit_hash:
        nav_links.append(f"> ↓ [上一分支点]({filename_map[found_branch_point.commit_hash]})")

    # 3. 父节点 (←)
    if current_node.parent and current_node.parent.commit_hash in exported_hashes_set:
        nav_links.append(f"> ← [父节点]({filename_map[current_node.parent.commit_hash]})")

    # 4. 子节点 (→)
    # 子节点已按时间升序排列
    for child in current_node.children:
        if child.commit_hash in exported_hashes_set:
            nav_links.append(f"> → [子节点]({filename_map[child.commit_hash]})")

    if not nav_links:
        return ""
    
    return "\n\n" + "> [!nav] 节点导航\n" + "\n".join(nav_links)


def _generate_file_content(
    node: QuipuNode, engine: Engine, no_frontmatter: bool, no_nav: bool,
    exported_hashes_set: Set[str], filename_map: Dict[str, str]
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
        navbar_str = _generate_navbar(node, exported_hashes_set, filename_map)
        content_str += navbar_str
        
    return content_str
~~~~~
~~~~~python
def _generate_navbar(
    current_node: QuipuNode,
    exported_hashes_set: Set[str],
    filename_map: Dict[str, str],
    no_branch_link: bool,
) -> str:
    """生成导航栏 Markdown 字符串。"""
    nav_links = []

    # 1. 总结节点 (↑)
    ancestor = current_node.parent
    while ancestor:
        if ancestor.input_tree == ancestor.output_tree and ancestor.commit_hash in exported_hashes_set:
            nav_links.append(f"> ↑ [总结节点]({filename_map[ancestor.commit_hash]})")
            break
        ancestor = ancestor.parent

    # 2. 上一分支点 (↓)
    if not no_branch_link:
        # Find the nearest ancestor that is a branch point.
        ancestor = current_node.parent
        found_branch_point = None
        while ancestor:
            if len(ancestor.children) > 1 and ancestor.commit_hash in exported_hashes_set:
                found_branch_point = ancestor
                break
            ancestor = ancestor.parent

        # Add the link only if a branch point was found AND it's not the direct parent
        # (to avoid a redundant link).
        if found_branch_point and current_node.parent and found_branch_point.commit_hash != current_node.parent.commit_hash:
            nav_links.append(f"> ↓ [上一分支点]({filename_map[found_branch_point.commit_hash]})")

    # 3. 父节点 (←)
    if current_node.parent and current_node.parent.commit_hash in exported_hashes_set:
        nav_links.append(f"> ← [父节点]({filename_map[current_node.parent.commit_hash]})")

    # 4. 子节点 (→)
    # 子节点已按时间升序排列
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
    no_branch_link: bool,
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
        navbar_str = _generate_navbar(node, exported_hashes_set, filename_map, no_branch_link)
        content_str += navbar_str

    return content_str
~~~~~

#### Acts 2: 添加测试用例以验证新选项

我们将在 `test_export_command.py` 中增加一个测试函数，专门验证 `--no-branch-link` 选项的行为。

~~~~~act
patch_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
def test_export_navbar_contextual_branch_link(runner, complex_history_for_nav):
    """Tests that the 'previous branch point' link only appears for nodes that have siblings."""
    engine = complex_history_for_nav
    output_dir = engine.root_dir / ".quipu" / "test_export_nav"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    files = {f.name: f for f in output_dir.glob("*.md")}

    # Case 1: Node WITH a sibling.
    # Its parent is the branch point, so the link should NOT be created to avoid redundancy.
    node_with_sibling_file = next(f for name, f in files.items() if "Node_With_Sibling" in name)
    content_with_sibling = node_with_sibling_file.read_text()
    assert "↓ [上一分支点]" not in content_with_sibling
    assert "← [父节点]" in content_with_sibling # It has a parent link to the branch point.

    # Case 2: Node WITHOUT a sibling.
    # It SHOULD have a link to the more distant branch point.
    node_without_sibling_file = next(f for name, f in files.items() if "Node_Without_Sibling" in name)
    content_without_sibling = node_without_sibling_file.read_text()
    assert "↓ [上一分支点]" in content_without_sibling
    assert "Branch_Point" in content_without_sibling
~~~~~
~~~~~python
def test_export_navbar_contextual_branch_link(runner, complex_history_for_nav):
    """Tests that the 'previous branch point' link only appears for nodes that have siblings."""
    engine = complex_history_for_nav
    output_dir = engine.root_dir / ".quipu" / "test_export_nav"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    files = {f.name: f for f in output_dir.glob("*.md")}

    # Case 1: Node WITH a sibling.
    # Its parent is the branch point, so the link should NOT be created to avoid redundancy.
    node_with_sibling_file = next(f for name, f in files.items() if "Node_With_Sibling" in name)
    content_with_sibling = node_with_sibling_file.read_text()
    assert "↓ [上一分支点]" not in content_with_sibling
    assert "← [父节点]" in content_with_sibling # It has a parent link to the branch point.

    # Case 2: Node WITHOUT a sibling.
    # It SHOULD have a link to the more distant branch point.
    node_without_sibling_file = next(f for name, f in files.items() if "Node_Without_Sibling" in name)
    content_without_sibling = node_without_sibling_file.read_text()
    assert "↓ [上一分支点]" in content_without_sibling
    assert "Branch_Point" in content_without_sibling


def test_export_no_branch_link(runner, complex_history_for_nav):
    """验证 --no-branch-link 选项能成功禁用分支点链接。"""
    engine = complex_history_for_nav
    output_dir = engine.root_dir / ".quipu" / "test_export_no_branch"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-branch-link"])

    files = {f.name: f for f in output_dir.glob("*.md")}

    # 找到通常应该有分支点链接的节点文件
    node_without_sibling_file = next(f for name, f in files.items() if "Node_Without_Sibling" in name)
    content = node_without_sibling_file.read_text()

    # 验证分支点链接不存在
    assert "↓ [上一分支点]" not in content
    # 验证其他链接（如父节点链接）仍然存在
    assert "← [父节点]" in content
~~~~~

### 下一步建议
我们已经完成了代码修改和测试用例的添加。现在，你可以运行 `pytest tests/cli/test_export_command.py` 来验证新功能是否按预期工作，并且没有破坏任何现有功能。确认无误后，我们可以将此功能合并。
