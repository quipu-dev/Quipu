import json

from quipu.cli.main import app
from quipu.test_utils.helpers import create_linear_history_from_specs, create_query_branching_history


def test_log_empty(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace

    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert not result.stdout.strip()


def test_log_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    specs = [
        {"type": "capture", "summary": "Node 1"},
        {"type": "capture", "summary": "Node 2"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    # The log is in reverse chronological order, so Node 2 comes first in stdout.
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "Node 2" in lines[0]
    assert "Node 1" in lines[1]


def test_find_command(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    specs = [
        {"type": "capture", "summary": "Fix bug"},
        {"type": "plan", "summary": "Implement feature", "content": "content"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["find", "-s", "Fix", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "Fix bug" in result.stdout


def test_log_json_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    create_linear_history_from_specs(engine, [{"type": "capture", "summary": "Node 1"}])

    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0

    json_data = json.loads(result.stdout)
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert "Node 1" in json_data[0]["summary"]


def test_find_json_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    specs = [
        {"type": "capture", "summary": "Feature A"},
        {"type": "capture", "summary": "Bugfix B"},
    ]
    create_linear_history_from_specs(engine, specs)

    result = runner.invoke(app, ["find", "--summary", "Bugfix", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0

    json_data = json.loads(result.stdout)
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert "Bugfix B" in json_data[0]["summary"]


def test_log_json_empty(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace

    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert result.stdout.strip() == "[]"


def test_log_filtering(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    specs = [
        {"type": "capture", "summary": "Node 1"},
        {"type": "capture", "summary": "Node 2"},
        {"type": "capture", "summary": "Node 3"},
    ]
    create_linear_history_from_specs(engine, specs)

    # 1. Test Limit
    result = runner.invoke(app, ["log", "-n", "1", "-w", str(work_dir)])
    assert result.exit_code == 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == 1
    assert "Node 3" in lines[0]  # Newest

    # 2. Test Filtering Result Empty
    result_empty = runner.invoke(app, ["log", "--since", "2099-01-01 00:00", "-w", str(work_dir)])
    assert result_empty.exit_code == 0
    assert not result_empty.stdout.strip()


def test_log_reachable_only(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace

    create_query_branching_history(engine)

    result = runner.invoke(app, ["log", "--reachable-only", "-w", str(work_dir)])
    assert result.exit_code == 0

    output = result.stdout
    assert "Node B" in output  # HEAD is reachable
    assert "Node A" in output  # Ancestor is reachable
    assert "Node C" not in output  # Unrelated branch is not reachable
