好的，这是一个非常好的增强方向。与其为每一种可能的链接类型都添加一个单独的 `--no-` 标志，不如设计一个更通用、更可扩展的选项来控制所有类型的链接。

我将用一个可重复使用的 `--hide-link-type` 选项来替换之前的 `--no-branch-link`，它可以接受 `summary`, `branch`, `parent`, `child` 等值。

## [WIP] feat(cli): 为 export 命令添加对导航链接的精细控制

### 用户需求
用户希望对 `quipu export` 命令生成的导航栏进行更精细的控制，能够选择性地禁用特定类型的链接，例如指向总结节点 (idempotent nodes)、父节点、子节点等的链接。

### 评论
这是一个优秀的“高级用户”功能。通过从多个布尔标志 (`--no-branch-link`) 演进到一个可接受多个值的选项 (`--hide-link-type`)，我们不仅使 CLI 接口更整洁，还为未来的扩展（例如，禁用兄弟节点链接）奠定了基础。这极大地提升了 `export` 命令作为文档生成工具的灵活性。

### 目标
1.  **重构 CLI 接口**: 移除 `export.py` 中的 `--no-branch-link` 选项。
2.  **实现新接口**: 添加一个新的、可多次使用的 `--hide-link-type` 选项，它接受的有效值为 `summary`, `branch`, `parent`, `child`。
3.  **更新核心逻辑**: 修改 `_generate_navbar` 函数，使其接受一个包含要隐藏的链接类型的集合，并根据该集合条件性地生成每种链接。
4.  **增强测试**: 重写 `test_export_command.py` 中的相关测试，使用参数化测试来分别验证禁用每种链接类型的行为是否正确。

### 基本原理
我们将使用 Typer 的能力来处理可重复的选项，该选项会将其所有值收集到一个列表中。在命令的业务逻辑中，我们会将这个列表转换为一个集合 (Set)，以实现高效的 `in` 检查。`_generate_navbar` 函数中的每一段链接生成逻辑都将被一个 `if "link_type" not in hidden_types:` 的条件语句包裹，从而实现精细的控制。这种设计模式清晰、高效且易于扩展。

### 标签
#intent/refine #intent/build #flow/ready #priority/medium #comp/cli #comp/tests #concept/navigation #scope/api #scope/ux #ai/brainstorm #task/domain/cli #task/object/export-command #task/action/feature-enhancement #task/state/continue

---

### Script

#### Acts 1: 重构 `export.py` 以支持精细链接控制

我们将修改 `export_command` 的签名，并更新 `_generate_navbar` 函数以处理新的逻辑。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
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
                zip_path = shutil.make_archive(str(output_dir), 'zip', output_dir)
                shutil.rmtree(output_dir)
                typer.secho(f"\n✅ 导出成功，已保存为压缩包: {zip_path}", fg=typer.colors.GREEN, err=True)
            else:
                typer.secho(f"\n✅ 导出成功完成。", fg=typer.colors.GREEN, err=True)
~~~~~
~~~~~python
        zip_output: Annotated[bool, typer.Option("--zip", help="压缩导出目录")] = False,
        no_nav: Annotated[bool, typer.Option("--no-nav", help="禁用导航栏")] = False,
        no_frontmatter: Annotated[bool, typer.Option("--no-frontmatter", help="禁用 Frontmatter")] = False,
        hide_link_type: Annotated[
            Optional[List[str]],
            typer.Option("--hide-link-type", help="禁用特定类型的导航链接 (可多次使用: summary, branch, parent, child)"),
        ] = None,
    ):
        """将 Quipu 历史记录导出为一组人类可读的 Markdown 文件。"""
        hidden_types = set(hide_link_type) if hide_link_type else set()

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
                        node, engine, no_frontmatter, no_nav, exported_hashes_set, filename_map, hidden_types
                    )
                    (output_dir / filename).write_text(content, encoding="utf-8")

            if zip_output:
                typer.secho("📦 正在压缩导出文件...", fg=typer.colors.BLUE, err=True)
                zip_path = shutil.make_archive(str(output_dir), 'zip', output_dir)
                shutil.rmtree(output_dir)
                typer.secho(f"\n✅ 导出成功，已保存为压缩包: {zip_path}", fg=typer.colors.GREEN, err=True)
            else:
                typer.secho(f"\n✅ 导出成功完成。", fg=typer.colors.GREEN, err=True)
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/export.py
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
~~~~~
~~~~~python
def _generate_navbar(
    current_node: QuipuNode,
    exported_hashes_set: Set[str],
    filename_map: Dict[str, str],
    hidden_link_types: Set[str],
) -> str:
    """生成导航栏 Markdown 字符串。"""
    nav_links = []

    # 1. 总结节点 (↑)
    if "summary" not in hidden_link_types:
        ancestor = current_node.parent
        while ancestor:
            if ancestor.input_tree == ancestor.output_tree and ancestor.commit_hash in exported_hashes_set:
                nav_links.append(f"> ↑ [总结节点]({filename_map[ancestor.commit_hash]})")
                break
            ancestor = ancestor.parent

    # 2. 上一分支点 (↓)
    if "branch" not in hidden_link_types:
        ancestor = current_node.parent
        found_branch_point = None
        while ancestor:
            if len(ancestor.children) > 1 and ancestor.commit_hash in exported_hashes_set:
                found_branch_point = ancestor
                break
            ancestor = ancestor.parent
        if found_branch_point and current_node.parent and found_branch_point.commit_hash != current_node.parent.commit_hash:
            nav_links.append(f"> ↓ [上一分支点]({filename_map[found_branch_point.commit_hash]})")

    # 3. 父节点 (←)
    if "parent" not in hidden_link_types:
        if current_node.parent and current_node.parent.commit_hash in exported_hashes_set:
            nav_links.append(f"> ← [父节点]({filename_map[current_node.parent.commit_hash]})")

    # 4. 子节点 (→)
    if "child" not in hidden_link_types:
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
    hidden_link_types: Set[str],
) -> str:
~~~~~

#### Acts 2: 更新 `test_export_command.py` 以使用参数化测试

我们将重写测试来覆盖所有新的可隐藏链接类型。

~~~~~act
write_file
tests/cli/test_export_command.py
~~~~~
~~~~~python
import pytest
import zipfile
from pathlib import Path
from datetime import datetime, timedelta

from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from tests.helpers import EMPTY_TREE_HASH


@pytest.fixture
def history_for_all_links(engine_instance: Engine):
    """
    创建一个复杂的历史记录，确保特定节点拥有所有类型的导航链接。
    History:
    - n0 (root)
      - n1 (Branch Point)
        - n2a (Branch A)
        - n2b (Branch B)
          - n3 (Linear on B, target for testing)
            - n4 (Child of target)
      - n_summary (Summary node, ancestor of n1)
    Node n3 will have: a parent (n2b), a child (n4), an ancestor branch point (n1),
    and an ancestor summary node (n_summary).
    """
    engine = engine_instance
    ws = engine.root_dir

    # n_summary (Summary Node)
    engine.create_plan_node(EMPTY_TREE_HASH, EMPTY_TREE_HASH, "plan sum", summary_override="Ancestor_Summary")

    # n0 (Root)
    (ws / "f").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.create_plan_node(EMPTY_TREE_HASH, h0, "plan 0", summary_override="Root")

    # n1 (Branch Point)
    (ws / "f").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h0, h1, "plan 1", summary_override="Branch_Point")

    # n2a (Branch A)
    engine.visit(h1)
    (ws / "a").touch()
    h2a = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2a, "plan 2a", summary_override="Branch_A")

    # n2b (Branch B)
    engine.visit(h1)
    (ws / "b").touch()
    h2b = engine.git_db.get_tree_hash()
    engine.create_plan_node(h1, h2b, "plan 2b", summary_override="Parent_Node")

    # n3 (Target Node for testing)
    engine.visit(h2b)
    (ws / "c").touch()
    h3 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h2b, h3, "plan 3", summary_override="Test_Target_Node")

    # n4 (Child of Target)
    engine.visit(h3)
    (ws / "d").touch()
    h4 = engine.git_db.get_tree_hash()
    engine.create_plan_node(h3, h4, "plan 4", summary_override="Child_Node")

    return engine


def test_export_basic(runner, history_for_all_links):
    """测试基本的导出功能。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    assert result.exit_code == 0
    assert "导出成功" in result.stderr
    assert output_dir.exists()

    files = list(output_dir.glob("*.md"))
    assert len(files) == 7

    target_file = next((f for f in files if "Test_Target_Node" in f.name), None)
    assert target_file is not None
    content = target_file.read_text()
    assert content.startswith("---")
    assert "> [!nav] 节点导航" in content
    assert "↑ [总结节点]" in content
    assert "↓ [上一分支点]" in content
    assert "← [父节点]" in content
    assert "→ [子节点]" in content


def test_export_no_frontmatter(runner, history_for_all_links):
    """测试 --no-frontmatter 选项。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-frontmatter", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert not a_file.read_text().startswith("---")


def test_export_no_nav(runner, history_for_all_links):
    """测试 --no-nav 选项。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export"
    runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-nav", "-n", "1"])
    a_file = next(output_dir.glob("*.md"))
    assert "> [!nav] 节点导航" not in a_file.read_text()


def test_export_zip(runner, history_for_all_links):
    """测试 --zip 功能。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--zip"])

    assert result.exit_code == 0
    assert "已保存为压缩包" in result.stderr

    zip_path = output_dir.with_suffix(".zip")
    assert not output_dir.exists()
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert len(zf.namelist()) == 7


@pytest.mark.parametrize(
    "link_type_to_hide, text_not_expected, text_still_expected",
    [
        ("summary", "↑ [总结节点]", "↓ [上一分支点]"),
        ("branch", "↓ [上一分支点]", "← [父节点]"),
        ("parent", "← [父节点]", "→ [子节点]"),
        ("child", "→ [子节点]", "↑ [总结节点]"),
    ],
)
def test_export_hide_link_type(runner, history_for_all_links, link_type_to_hide, text_not_expected, text_still_expected):
    """验证 --hide-link-type 选项能成功禁用特定类型的链接。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_links"
    result = runner.invoke(
        app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--hide-link-type", link_type_to_hide]
    )
    assert result.exit_code == 0

    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()

    assert text_not_expected not in content
    assert text_still_expected in content


def test_export_hide_multiple_link_types(runner, history_for_all_links):
    """验证可以同时禁用多种链接类型。"""
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_links"
    result = runner.invoke(
        app,
        [
            "export",
            "-w",
            str(engine.root_dir),
            "-o",
            str(output_dir),
            "--hide-link-type",
            "summary",
            "--hide-link-type",
            "child",
        ],
    )
    assert result.exit_code == 0

    files = {f.name: f for f in output_dir.glob("*.md")}
    target_file = next(f for name, f in files.items() if "Test_Target_Node" in name)
    content = target_file.read_text()

    assert "↑ [总结节点]" not in content
    assert "→ [子节点]" not in content
    assert "↓ [上一分支点]" in content
    assert "← [父节点]" in content
~~~~~

### 下一步建议
我们已经成功地将 `export` 命令重构为一个更强大、更灵活的工具，并更新了测试以保证其健壮性。现在，是时候将这些改进提交到代码库了。
