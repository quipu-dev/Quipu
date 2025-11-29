好的，我们开始执行下一个重构步骤：抽象共享的测试辅助函数。

这个任务的目标是识别出在不同测试文件中重复出现的、用于准备测试数据（创建 Quipu 历史节点）的逻辑，并将它们提取到一个统一的 `tests/helpers.py` 文件中。这将遵循 DRY (Don't Repeat Yourself) 原则，使我们的测试代码更简洁、更易于维护。

我将：
1.  创建 `tests/helpers.py` 文件，并定义几个通用的“历史工厂”函数。
2.  重构 `tests/engine/test_engine.py` 中的 `populated_engine` Fixture，让它使用这些新的共享辅助函数，以此作为示范。

## [WIP] refactor: 提取共享的测试辅助函数到 tests/helpers.py

### 用户需求
多个测试文件中存在重复的逻辑，用于在测试准备阶段创建文件变更和生成 Quipu 历史节点。需要将这些重复的逻辑抽象成可复用的辅助函数，并存放于统一的 `tests/helpers.py` 模块中。

### 评论
这是提升测试代码质量的关键一步。通过建立共享的测试 `helpers`，我们不仅减少了代码冗余，还为未来编写更复杂的测试场景（例如，构建分支历史）提供了坚实的基础。这将显著提高测试代码的可读性和可维护性。

### 目标
1.  创建一个新的 `tests/helpers.py` 文件。
2.  在该文件中定义通用的辅助函数，如 `create_plan_node_with_change` 和 `create_capture_node_with_change`。
3.  重构 `tests/engine/test_engine.py` 文件中的 `TestEngineFindNodes` 测试类，使其使用新的共享辅助函数来准备测试数据，从而消除本地的辅助函数 `add_commit`。

### 基本原理
我们将在 `tests` 包下创建一个 `helpers.py` 模块，用于存放所有测试共享的工具函数。然后，通过重写 `tests/engine/test_engine.py` 中受影响的部分，将原有的本地化、重复的设置逻辑替换为对新共享函数的调用。这使得测试的“准备 (Arrange)”阶段变得更加声明式和清晰。

### 标签
#intent/refine #flow/ready #priority/low #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-helpers #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 创建共享的 `tests/helpers.py` 文件

我们首先创建这个新文件，并定义核心的辅助函数。

~~~~~act
write_file tests/helpers.py
~~~~~
~~~~~python
from quipu.engine.state_machine import Engine

# A common constant representing the initial empty state of a Git repository.
EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def create_plan_node_with_change(
    engine: Engine, parent_hash: str, file_name: str, content: str, message: str
) -> str:
    """
    Creates a file change in the workspace and generates a new Plan node.
    Returns the output_tree hash of the new node.
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.create_plan_node(input_tree=parent_hash, output_tree=new_hash, content=message)
    return new_hash


def create_capture_node_with_change(engine: Engine, file_name: str, content: str, message: str) -> str:
    """
    Creates a file change in the workspace and generates a new Capture node.
    The new node is parented to the current HEAD of the engine.
    Returns the output_tree hash of the new node.
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.capture_drift(new_hash, message=message)
    return new_hash
~~~~~

#### Acts 2: 重构 `test_engine.py` 以使用新的辅助函数

现在，我们将重写 `tests/engine/test_engine.py` 文件中的 `TestEngineFindNodes` 类，使其完全依赖新的 `helpers` 模块来构建测试环境，从而移除原有的局部辅助函数。

~~~~~act
patch_file tests/engine/test_engine.py
~~~~~
~~~~~python
class TestEngineFindNodes:
    @pytest.fixture
    def populated_engine(self, engine_instance: Engine):
        import time

        engine, repo_path = engine_instance, engine_instance.root_dir

        def add_commit(filename, content, message, node_type, parent_hash):
            """辅助函数：创建文件变更并生成一个新节点"""
            (repo_path / filename).write_text(content)
            time.sleep(0.01)  # 确保时间戳唯一
            new_hash = engine.git_db.get_tree_hash()
            if node_type == "plan":
                engine.create_plan_node(parent_hash, new_hash, message)
            else:  # capture
                # 对于 capture，message 是用户备注，不是 plan content
                engine.capture_drift(new_hash, message=message)
            return new_hash

        # 创世状态
        parent = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # Node 1 (Plan)
        parent = add_commit("f_a.txt", "content_a", "# feat: Add feature A", "plan", parent)
        # Node 2 (Capture)
        parent = add_commit("f_b.txt", "content_b", "Snapshot after feature A", "capture", parent)
        # Node 3 (Plan)
        parent = add_commit("f_c.txt", "content_c", "refactor: Cleanup code", "plan", parent)

        # 重新对齐以加载完整的图谱
        engine.align()
        return engine
~~~~~
~~~~~python
class TestEngineFindNodes:
    @pytest.fixture
    def populated_engine(self, engine_instance: Engine):
        """
        Populates an engine instance with a linear history using shared test helpers.
        History: (Genesis) -> Plan -> Capture -> Plan
        """
        from tests.helpers import (
            create_plan_node_with_change,
            create_capture_node_with_change,
            EMPTY_TREE_HASH,
        )
        import time

        engine = engine_instance
        parent = EMPTY_TREE_HASH

        # Node 1 (Plan)
        parent = create_plan_node_with_change(engine, parent, "f_a.txt", "content_a", "# feat: Add feature A")
        time.sleep(0.01)  # Ensure unique timestamps for ordering

        # Node 2 (Capture) - Parented to Node 1's state
        parent = create_capture_node_with_change(engine, "f_b.txt", "content_b", "Snapshot after feature A")
        time.sleep(0.01)

        # Node 3 (Plan) - Parented to Node 2's state
        parent = create_plan_node_with_change(engine, parent, "f_c.txt", "content_c", "refactor: Cleanup code")

        # Re-align to load the full graph into the reader component for testing
        engine.align()
        return engine
~~~~~

### 下一步建议
重构已经完成。请运行测试套件（特别是 `pytest tests/engine/test_engine.py`），以确保使用新辅助函数的测试用例依然能够全部通过。测试通过后，我们就可以将这项改进提交到版本历史中。
