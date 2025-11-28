你分析得非常到位。测试失败暴露了一个关键问题：**测试用例对 `summary` 字段内容的假设过于严格。**

## [WIP] fix(test): 修复测试用例对 `summary` 字段内容的假设过于严格

### 错误分析
测试失败的根本原因在于，`engine.capture_drift()` 在生成节点摘要 (`summary`) 时，不仅仅使用了我们传入的 `message` (`"Node 1"` 或 `"Bugfix B"`)，它还会**自动追加一些上下文信息**（例如操作类型和文件变更摘要，如 `Capture: A f1`），以形成一个更具信息量的完整摘要。

而我们的测试代码错误地假设了 `node.summary` 会与传入的 `message` **完全相等** (`==`)。当引擎的行为提供了更丰富的摘要时，这个严格的断言就失败了。

这不是产品代码的 Bug，而是**测试代码的脆弱性 (brittleness)**。一个好的测试应该验证核心意图，而不是对实现的具体细节（如摘要的精确格式）进行过度拟合。

### 用户需求
修正 `test_query_commands.py` 中的测试用例，使其断言更加健壮，能够适应 `summary` 字段中包含额外上下文信息的情况。

### 评论
这是一个典型的测试重构场景。通过将严格的相等性检查 (`==`) 放宽为包含性检查 (`in`)，我们使测试既能验证核心信息的正确性，又不会因为未来对摘要格式的微小改进（例如添加时间戳或作者信息）而轻易失败，从而提升了测试套件的长期可维护性。

### 目标
1.  修改 `test_log_json_output` 和 `test_find_json_output` 测试函数。
2.  将其中对 `summary` 字段的断言从 `assert data[0]["summary"] == "..."` 修改为 `assert "..." in data[0]["summary"]`。

### 基本原理
我们将采用更灵活的断言策略。我们真正关心的是用户提供的消息是否被成功记录在了摘要中，而不是摘要是否“只有”这个消息。因此，使用 Python 的 `in` 操作符来检查子字符串是否存在，是验证此核心需求的正确且健壮的方法。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/cli #task/object/json-output #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 修正 `test_query_commands.py` 中的断言逻辑

我们将使用 `write_file` 来更新整个测试文件，以确保其内容完全正确。

~~~~~act
write_file
tests/cli/test_query_commands.py
~~~~~
~~~~~python
import json
from quipu.cli.main import app


def test_log_empty(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace
    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "历史记录为空" in result.stderr


def test_log_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace
    (work_dir / "f1").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 1")
    (work_dir / "f2").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 2")
    result = runner.invoke(app, ["log", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert "--- Quipu History Log ---" in result.stderr
    assert "Node 1" in result.stdout
    assert "Node 2" in result.stdout
    assert "Node 1" not in result.stderr


def test_find_command(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace
    (work_dir / "f1").touch()
    hash_v1 = engine.git_db.get_tree_hash()
    engine.capture_drift(hash_v1, message="Fix bug")
    (work_dir / "f2").touch()
    hash_v2 = engine.git_db.get_tree_hash()
    engine.create_plan_node(input_tree=hash_v1, output_tree=hash_v2, plan_content="content", summary_override="Implement feature")
    result = runner.invoke(app, ["find", "-s", "Fix", "-w", str(work_dir)])
    assert "--- 查找结果 ---" in result.stderr
    assert "Fix bug" in result.stdout
    assert "Implement feature" not in result.stdout
    assert "Fix bug" not in result.stderr


def test_log_json_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace
    (work_dir / "f1").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Node 1")
    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert result.stderr.strip() == ""
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert "Node 1" in data[0]["summary"]  # Use 'in' for robust check
    assert "output_tree" in data[0]
    assert "short_hash" in data[0]
    assert "parent" not in data[0]  # Check for excluded field


def test_find_json_output(runner, quipu_workspace):
    work_dir, _, engine = quipu_workspace
    (work_dir / "f1").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Feature A")
    (work_dir / "f2").touch()
    engine.capture_drift(engine.git_db.get_tree_hash(), message="Bugfix B")
    result = runner.invoke(app, ["find", "--summary", "Bugfix", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert result.stderr.strip() == ""
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    assert "Bugfix B" in data[0]["summary"]  # Use 'in' for robust check


def test_log_json_empty(runner, quipu_workspace):
    work_dir, _, _ = quipu_workspace
    result = runner.invoke(app, ["log", "--json", "-w", str(work_dir)])
    assert result.exit_code == 0
    assert result.stderr.strip() == ""
    assert result.stdout.strip() == "[]"
~~~~~

### 下一步建议
我们已经修复了测试用例。现在，请重新运行测试以确认所有问题都已解决。如果测试通过，我将为你生成最终的 `[COMMIT]` 计划，将这个功能及其健壮的测试一同提交。
