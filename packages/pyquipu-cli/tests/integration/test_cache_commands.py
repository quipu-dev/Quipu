import pytest
from quipu.cli.main import app
from quipu.engine.state_machine import Engine


@pytest.fixture
def history_with_redundant_refs(engine_instance: Engine):
    engine = engine_instance
    ws = engine.root_dir

    # root
    (ws / "file.txt").write_text("v0")
    h0 = engine.git_db.get_tree_hash()
    engine.capture_drift(h0, "root")

    # n1
    (ws / "file.txt").write_text("v1")
    h1 = engine.git_db.get_tree_hash()
    engine.capture_drift(h1, "n1")

    # n2 (branch point)
    (ws / "file.txt").write_text("v2")
    h2 = engine.git_db.get_tree_hash()
    n2 = engine.capture_drift(h2, "n2")

    # n3a (leaf A)
    engine.visit(n2.output_tree)
    (ws / "a.txt").touch()
    h3a = engine.git_db.get_tree_hash()
    engine.capture_drift(h3a, "n3a")

    # n3b (leaf B)
    engine.visit(n2.output_tree)
    (ws / "b.txt").touch()
    h3b = engine.git_db.get_tree_hash()
    engine.capture_drift(h3b, "n3b")

    return engine


def test_cache_sync(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace

    result = runner.invoke(app, ["cache", "sync", "-w", str(work_dir)])

    assert result.exit_code == 0
    db_path = work_dir / ".quipu" / "history.sqlite"
    assert db_path.exists()


def test_cache_rebuild_no_db(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace

    result = runner.invoke(app, ["cache", "rebuild", "-w", str(work_dir)])

    assert result.exit_code == 0
    db_path = work_dir / ".quipu" / "history.sqlite"
    assert db_path.exists()


def test_cache_prune_refs_with_redundancy(runner, history_with_redundant_refs):
    engine = history_with_redundant_refs
    work_dir = engine.root_dir

    refs_dir = work_dir / ".git" / "refs" / "quipu" / "local" / "heads"
    assert len(list(refs_dir.iterdir())) == 5, "Pre-condition: 5 refs should exist before pruning"

    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
    assert len(list(refs_dir.iterdir())) == 2, "Post-condition: 2 refs should remain after pruning"


def test_cache_prune_refs_no_redundancy(runner, history_with_redundant_refs):
    engine = history_with_redundant_refs
    work_dir = engine.root_dir
    refs_dir = work_dir / ".git" / "refs" / "quipu" / "local" / "heads"

    # 第一次运行以清理
    runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])
    assert len(list(refs_dir.iterdir())) == 2

    # 第二次运行，此时应保持 2 个有效分支末端
    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
    assert len(list(refs_dir.iterdir())) == 2


def test_cache_prune_refs_empty_repo(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace

    result = runner.invoke(app, ["cache", "prune-refs", "-w", str(work_dir)])

    assert result.exit_code == 0
