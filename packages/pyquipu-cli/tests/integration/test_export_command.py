import zipfile

import pytest
from quipu.cli.main import app
from quipu.engine.state_machine import Engine
from quipu.test_utils.helpers import create_branching_history, create_complex_link_history


@pytest.fixture
def populated_history(engine_instance: Engine):
    return create_branching_history(engine_instance)


@pytest.fixture
def history_for_all_links(engine_instance: Engine):
    return create_complex_link_history(engine_instance)


def test_export_basic(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir)])

    assert result.exit_code == 0

    assert output_dir.exists()
    files = list(output_dir.glob("*.md"))
    assert len(files) == 6
    target_file = next((f for f in files if "Branch_A_change" in f.name), None)
    assert target_file is not None
    content = target_file.read_text()
    assert content.startswith("---") and "> [!nav] 节点导航" in content


def test_export_filtering(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_filter"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "-n", "2"])

    assert result.exit_code == 0
    assert len(list(output_dir.glob("*.md"))) == 2


def test_export_edge_cases(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    # Empty history
    result = runner.invoke(app, ["export", "-w", str(work_dir)])
    assert result.exit_code == 0

    # No matching nodes
    (work_dir / "f").touch()
    engine.capture_drift(engine.git_db.get_tree_hash())

    result = runner.invoke(app, ["export", "-w", str(work_dir), "--since", "2099-01-01 00:00"])
    assert result.exit_code == 0


def test_export_no_frontmatter(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_fm"

    result = runner.invoke(
        app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-frontmatter", "-n", "1"]
    )
    assert result.exit_code == 0
    a_file = next(output_dir.glob("*.md"))
    assert not a_file.read_text().startswith("---")


def test_export_no_nav(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_no_nav"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--no-nav", "-n", "1"])
    assert result.exit_code == 0
    a_file = next(output_dir.glob("*.md"))
    assert "> [!nav] 节点导航" not in a_file.read_text()


def test_export_zip(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_zip"

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--zip"])

    assert result.exit_code == 0

    zip_path = output_dir.with_suffix(".zip")
    assert not output_dir.exists() and zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert len(zf.namelist()) == 6


@pytest.mark.parametrize(
    "link_type_to_hide, text_not_expected, text_still_expected",
    [
        ("summary", "↑ [总结节点]", "↓ [上一分支点]"),
        ("branch", "↓ [上一分支点]", "← [父节点]"),
        ("parent", "← [父节点]", "→ [子节点]"),
        ("child", "→ [子节点]", "↑ [总结节点]"),
    ],
)
def test_export_hide_link_type(
    runner, history_for_all_links, link_type_to_hide, text_not_expected, text_still_expected
):
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
    engine = history_for_all_links
    output_dir = engine.root_dir / ".quipu" / "test_export_hide_multi"

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
    assert "↑ [总结节点]" not in content and "→ [子节点]" not in content
    assert "↓ [上一分支点]" in content and "← [父节点]" in content


def test_export_reachable_only(runner, populated_history):
    engine = populated_history
    output_dir = engine.root_dir / ".quipu" / "test_export_reachable"

    # The fixture leaves HEAD on branch B. We'll checkout a node on branch A.
    summary_node = next(n for n in engine.history_graph.values() if n.summary == "Summary Node")
    engine.visit(summary_node.output_tree)

    result = runner.invoke(app, ["export", "-w", str(engine.root_dir), "-o", str(output_dir), "--reachable-only"])
    assert result.exit_code == 0

    files = list(output_dir.glob("*.md"))
    # Branch A path: Root -> Linear 1 -> Branch Point -> Branch A -> Summary (5 nodes)
    # Branch B is now unreachable and should be excluded.
    assert len(files) == 5

    filenames = {f.name for f in files}
    assert not any("Branch_B_change" in name for name in filenames)
    assert any("Branch_A_change" in name for name in filenames)
