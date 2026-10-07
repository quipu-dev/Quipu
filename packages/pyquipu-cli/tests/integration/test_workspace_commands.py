from quipu.cli.main import app


def test_save_clean_workspace(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    (work_dir / "file.txt").write_text("v1")
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Initial")

    head_before = engine._read_head()
    count_before = len(engine.reader.load_all_nodes())

    result = runner.invoke(app, ["save", "-w", str(work_dir)])
    assert result.exit_code == 0

    assert len(engine.reader.load_all_nodes()) == count_before
    assert engine._read_head() == head_before


def test_save_with_changes(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    (work_dir / "file.txt").write_text("v1")
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Initial")

    (work_dir / "file.txt").write_text("v2")
    count_before = len(engine.reader.load_all_nodes())

    result = runner.invoke(app, ["save", "My Snapshot", "-w", str(work_dir)])
    assert result.exit_code == 0

    nodes = engine.reader.load_all_nodes()
    assert len(nodes) == count_before + 1
    assert "My Snapshot" in nodes[0].summary


def test_discard_changes(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    (work_dir / "file.txt").write_text("v1")
    initial_node = engine.capture_drift(engine.git_db.get_tree_hash())
    (work_dir / "file.txt").write_text("v2")

    result = runner.invoke(app, ["discard", "-f", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert (work_dir / "file.txt").read_text() == "v1"
    assert engine.git_db.get_tree_hash() == initial_node.output_tree


def test_discard_interactive_abort(runner, quipu_workspace, monkeypatch):
    work_dir, _, engine = quipu_workspace
    monkeypatch.setattr("click.getchar", lambda echo=False: "n")

    (work_dir / "file.txt").write_text("v1")
    engine.capture_drift(engine.git_db.get_tree_hash())
    (work_dir / "file.txt").write_text("v2")

    result = runner.invoke(app, ["discard", "-w", str(work_dir)])

    assert result.exit_code == 1
    assert (work_dir / "file.txt").read_text() == "v2"
