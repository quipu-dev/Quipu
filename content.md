分析正确。测试失败暴露了两个核心问题：一个是由 `QuipuNode` 对象不可哈希导致的 `TypeError`，另一个是测试用例中对 `Engine` 的不正确实例化。

**错误分析**:

1.  **`TypeError: unhashable type: 'QuipuNode'`**: 这是导致前五个测试失败的根本原因。在 `export.py` 中，我试图将 `QuipuNode` 对象直接用作字典的键 (`filename_map`)和集合的元素 (`exported_nodes_set`)。由于 `QuipuNode` 是一个包含列表（`children`）的数据类，它是可变的，因此不可哈希。这导致了程序在尝试构建这些数据结构时崩溃，无法生成任何导出文件。
2.  **`TypeError: Engine.__init__() missing ... arguments`**: 在 `test_export_edge_cases` 中，我使用了 `engine = Engine(work_dir)` 来实例化引擎。这是一个错误，因为 `Engine` 的构造函数需要 `db`, `reader`, 和 `writer` 等多个依赖项。正确的做法是使用 `conftest.py` 中定义的 `engine_instance` 或 `quipu_workspace` fixture，它们会返回一个被正确初始化的 `Engine` 实例。

**解决方案**:

1.  **修复 `TypeError`**: 我将修改 `export.py`，不再使用 `QuipuNode` 对象作为键。取而代之，我将使用每个节点唯一的、可哈希的 `commit_hash` 字符串作为标识符。所有相关的数据结构和函数调用都将进行相应调整。
2.  **修复测试实例化**: 我将修改 `test_export_edge_cases`，使用 `quipu_workspace` fixture 来获取一个正确构造的 `Engine` 实例，而不是错误地直接调用其构造函数。
3.  **修正测试断言**: 我还发现 `test_export_navbar_logic` 中对“总结节点”的断言逻辑存在瑕疵，将一并修正以确保测试的准确性。

## [COMMIT] fix: 修正 export 命令的哈希错误和测试实例化问题

### 错误分析
`quipu export` 命令因使用不可哈希的 `QuipuNode` 对象作为字典键和集合元素而引发 `TypeError`，导致所有相关测试失败。此外，`test_export_edge_cases` 测试用例中对 `Engine` 的实例化方式不正确，未能提供必要的依赖项，导致了另一个 `TypeError`。

### 用户需求
修复 `export.py` 中的哈希问题和 `test_export_command.py` 中的 `Engine` 实例化问题，使所有 `export` 命令相关的测试都能通过。

### 评论
这是一个典型的由数据结构选择不当和对测试 Fixture 理解不足引发的问题。通过将键替换为稳定的 `commit_hash` 并遵循正确的 Fixture 使用模式，我们可以快速修复这些问题，并使代码更加健壮和可预测。

### 目标
1.  修改 `export.py`，将 `filename_map` 和 `exported_nodes_set` 的键/元素从 `QuipuNode` 对象更改为 `node.commit_hash` 字符串。
2.  相应地更新 `_generate_navbar` 和 `_generate_file_content` 函数，以使用 `commit_hash` 进行查找。
3.  修改 `test_export_edge_cases` 测试，从 `quipu_workspace` fixture 获取 `engine` 实例。
4.  修正 `test_export_navbar_logic` 中关于总结节点的断言逻辑。

### 基本原理
Python 的核心数据结构 `dict` 和 `set` 要求其键和元素必须是可哈希的。可变对象（如列表）是不可哈希的。通过使用节点唯一的、不可变的 `commit_hash` 字符串作为代理标识符，我们解决了这个核心问题。在测试中，始终优先使用 Fixture 来获取复杂的、带依赖的对象实例，是确保测试环境正确性的最佳实践。

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #comp/tests #concept/history #scope/core #ai/instruct #task/domain/cli #task/object/export-command #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 修复 `export.py` 中的 `TypeError`

我们将修改 `export.py`，使用 `commit_hash` 作为唯一的、可哈希的键。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
def _generate_navbar(
    current_node: QuipuNode, exported_nodes_set: Set[QuipuNode], filename_map: Dict[QuipuNode, str]
) -> str:
    """生成导航栏 Markdown 字符串。"""
    nav_links = []

    # 1. 总结节点 (↑)
    ancestor = current_node.parent
    while ancestor:
        if ancestor.input_tree == ancestor.output_tree and ancestor in exported_nodes_set:
            nav_links.append(f"> ↑ [总结节点]({filename_map[ancestor]})")
            break
        ancestor = ancestor.parent

    # 2. 上一分支点 (↓)
    ancestor = current_node.parent
    while ancestor:
        if len(ancestor.children) > 1 and ancestor in exported_nodes_set:
            nav_links.append(f"> ↓ [上一分支点]({filename_map[ancestor]})")
            break
        ancestor = ancestor.parent

    # 3. 父节点 (←)
    if current_node.parent and current_node.parent in exported_nodes_set:
        nav_links.append(f"> ← [父节点]({filename_map[current_node.parent]})")

    # 4. 子节点 (→)
    # 子节点已按时间升序排列
    for child in current_node.children:
        if child in exported_nodes_set:
            nav_links.append(f"> → [子节点]({filename_map[child]})")

    if not nav_links:
        return ""
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
    ancestor = current_node.parent
    while ancestor:
        if len(ancestor.children) > 1 and ancestor.commit_hash in exported_hashes_set:
            nav_links.append(f"> ↓ [上一分支点]({filename_map[ancestor.commit_hash]})")
            break
        ancestor = ancestor.parent

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
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
def _generate_file_content(
    node: QuipuNode, engine: Engine, no_frontmatter: bool, no_nav: bool,
    exported_nodes_set: Set[QuipuNode], filename_map: Dict[QuipuNode, str]
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
        navbar_str = _generate_navbar(node, exported_nodes_set, filename_map)
        content_str += navbar_str
        
    return content_str
~~~~~
~~~~~python
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

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
~~~~~
~~~~~python
            output_dir.mkdir(parents=True, exist_ok=True)
            typer.secho(f"🚀 正在导出 {len(nodes_to_export)} 个节点到 '{output_dir}'...", fg=typer.colors.BLUE, err=True)

            # 预计算文件名和节点集合以供导航栏使用
            filename_map = {node: _generate_filename(node) for node in nodes_to_export}
            exported_nodes_set = set(nodes_to_export)

            with typer.progressbar(nodes_to_export, label="导出进度") as progress:
                for node in progress:
                    filename = filename_map[node]
                    content = _generate_file_content(node, engine, no_frontmatter, no_nav, exported_nodes_set, filename_map)
                    (output_dir / filename).write_text(content, encoding="utf-8")

            if zip_output:
                typer.secho("📦 正在压缩导出文件...", fg=typer.colors.BLUE, err=True)
~~~~~
~~~~~python
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

#### Acts 2: 修复 `test_export_command.py` 中的错误

我们将修正测试文件中的 `Engine` 实例化错误和不正确的断言。

~~~~~act
patch_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
def test_export_navbar_logic(runner, populated_history):
    """验证导航栏链接的正确性。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    files = list(output_dir.glob("*.md"))
    
    # Test Branch Point links (Node 2)
    branch_point_file = next(f for f in files if "Branch_Point" in f.name)
    content = branch_point_file.read_text()
    assert content.count("→ [子节点]") == 2
    assert "← [父节点]" in content

    # Test Summary and Branch Point ancestor links (Node 4)
    summary_node_file = next(f for f in files if "Summary_Node" in f.name)
    content = summary_node_file.read_text()
    assert "↑ [总结节点]" in content # It is its own summary node, so no link to ancestor
    assert "↓ [上一分支点]" in content
    assert "Branch_Point" in content # Check it links to the correct file
~~~~~
~~~~~python
def test_export_navbar_logic(runner, populated_history):
    """验证导航栏链接的正确性。"""
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    files = list(output_dir.glob("*.md"))
    
    # Test Branch Point links (Node 2)
    branch_point_file = next(f for f in files if "Branch_Point" in f.name)
    content = branch_point_file.read_text()
    assert content.count("→ [子节点]") == 2
    assert "← [父节点]" in content

    # Test Summary and Branch Point ancestor links (Node 4)
    summary_node_file = next(f for f in files if "Summary_Node" in f.name)
    content = summary_node_file.read_text()
    # n4 is a summary node, but its ancestors are not. So it should not have a summary link.
    assert "↑ [总结节点]" not in content
    assert "↓ [上一分支点]" in content
    assert "Branch_Point" in content # Check it links to the correct file
~~~~~

~~~~~act
patch_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
def test_export_edge_cases(runner, quipu_workspace):
    """测试边界情况。"""
    work_dir, _, _ = quipu_workspace # Empty history
    
    # Test empty history
    result = runner.invoke(app, ["export", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "历史记录为空" in result.stderr

    # Create one node, then test no-match filter
    (work_dir / "f").touch()
    engine = Engine(work_dir) # Re-init engine
    engine.capture_drift(engine.git_db.get_tree_hash())
    
    result = runner.invoke(app, ["export", "-w", str(work_dir), "--since", "2099-01-01 00:00"])
    assert result.exit_code == 0
    assert "未找到符合条件的节点" in result.stderr
~~~~~
~~~~~python
def test_export_edge_cases(runner, quipu_workspace):
    """测试边界情况。"""
    work_dir, _, engine = quipu_workspace # Empty history
    
    # Test empty history
    result = runner.invoke(app, ["export", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "历史记录为空" in result.stderr

    # Create one node, then test no-match filter
    (work_dir / "f").touch()
    # Use the properly initialized engine from the fixture
    engine.capture_drift(engine.git_db.get_tree_hash())
    
    result = runner.invoke(app, ["export", "-w", str(work_dir), "--since", "2099-01-01 00:00"])
    assert result.exit_code == 0
    assert "未找到符合条件的节点" in result.stderr
~~~~~

### 下一步建议
所有已知的 Bug 都已修复。现在，我们应该重新运行完整的测试套件，以确保我们的修复没有引入任何回归问题。如果所有测试都通过，这个功能就可以被认为已经完成并准备好提交了。
