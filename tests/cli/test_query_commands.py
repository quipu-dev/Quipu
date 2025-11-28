from quipu.cli.main import app


def test_log_empty(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace
    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "历史记录为空" in result.stderr


def test_log_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace
    
    # 创建一些历史
    (work_dir / "f1").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 1")
    
    (work_dir / "f2").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 2")
    
    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "Node 1" in result.stderr
    assert "Node 2" in result.stderr
    assert "[CAPTURE]" in result.stderr


def test_find_command(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    (work_dir / "f1").touch()
    capture_node = engine.capture_drift(engine.git_db.get_tree_hash(), message="Fix bug")
    hash_v1 = capture_node.output_tree

    (work_dir / "f2").touch()
    hash_v2 = engine.git_db.get_tree_hash()
    engine.create_plan_node(
        input_tree=hash_v1,
        output_tree=hash_v2,
        plan_content="content",
        summary_override="Implement feature",
    )

    # 查找 "Fix"
    result = runner.invoke(app, ["find", "-s", "Fix", "-w", str(work_dir)])
    assert "Fix bug" in result.stderr
    assert "Implement feature" not in result.stderr
    
    # 查找类型 "plan"
    result_type = runner.invoke(app, ["find", "-t", "plan", "-w", str(work_dir)])
    assert "Implement feature" in result_type.stderr
    assert "Fix bug" not in result_type.stderr