# fix-test: 修复因 Engine 依赖注入变更导致的测试失败

## 用户需求
在 `Engine` 类的构造函数中引入 `reader` 和 `writer` 依赖后，多个测试用例因为仍在使用旧的 `Engine(repo_path)` 方式进行实例化而失败，抛出 `TypeError`。需要更新这些测试用例以符合新的 `Engine` 初始化契约。

## 评论
这是重构过程中典型的连锁反应。修复这些测试是确保新架构正确性的最后一步。通过更新测试中的 `Engine` 实例化逻辑，我们不仅能让测试重新通过，还能验证新的依赖注入模式是可行且易于在测试环境中模拟的。

## 目标
1.  修改 `tests/test_head_and_root.py` 中的 `engine_with_repo` fixture。
2.  修改 `tests/test_idempotent_node.py` 中的 `test_idempotent_plan_creation` 函数。
3.  修改 `tests/test_navigation.py` 中的 `nav_workspace` 和 `cli_workspace` fixtures。
4.  在所有上述位置，都使用 `FileSystemHistoryReader` 和 `FileSystemHistoryWriter` 来正确地实例化 `Engine`。

## 基本原理
测试代码也是代码，它必须与生产代码的接口保持同步。本次修复将遵循依赖注入的原则，在测试的 `fixture` 或设置阶段，手动创建 `Engine` 所需的依赖（`Reader` 和 `Writer` 的文件系统实现），并将它们传递给 `Engine` 的构造函数。这确保了测试环境能够准确地模拟 `Engine` 在真实应用中的运行方式。

## 标签
#comp/tests #comp/engine #scope/dx

---

## Script

### Acts 1: 修复 `test_head_and_root.py`

更新 `engine_with_repo` fixture 以正确实例化 `Engine`。

~~~~~act
write_file
~~~~~

~~~~~path
tests/test_head_and_root.py
~~~~~

~~~~~python
import pytest
import os
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.controller import find_project_root
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestHeadTracking:
    @pytest.fixture
    def engine_with_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        # Config git user
        subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Axon Test"], cwd=repo, check=True)
        
        history_dir = repo / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
        return Engine(repo, reader=reader, writer=writer)

    def test_head_persistence(self, engine_with_repo):
        """测试 HEAD 指针的创建和更新"""
        engine = engine_with_repo
        
        # 1. 初始状态，无 HEAD
        assert not engine.head_file.exists()
        assert engine._read_head() is None
        
        # 2. 创建一个 Plan 节点
        # 这会自动更新 HEAD
        (engine.root_dir / "a.txt").touch()
        tree1 = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", tree1, "plan content")
        
        assert engine.head_file.exists()
        assert engine._read_head() == tree1
        
        # 3. Align 应该保持 HEAD
        engine.align()
        assert engine._read_head() == tree1
        
    def test_drift_uses_head(self, engine_with_repo):
        """测试漂移捕获时使用 HEAD 作为父节点"""
        engine = engine_with_repo
        
        # 1. 建立 State A 并确立 HEAD
        (engine.root_dir / "f.txt").write_text("v1")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "setup")
        assert engine._read_head() == hash_a
        
        # 2. 制造漂移 (State B)
        (engine.root_dir / "f.txt").write_text("v2")
        hash_b = engine.git_db.get_tree_hash()
        
        # 3. 捕获漂移
        # 此时 engine 应该读取 HEAD (hash_a) 作为 input_tree
        capture_node = engine.capture_drift(hash_b)
        
        assert capture_node.input_tree == hash_a
        assert capture_node.output_tree == hash_b
        
        # 4. 验证 capture 后 HEAD 更新
        assert engine._read_head() == hash_b

    def test_checkout_updates_head(self, engine_with_repo):
        """验证 engine.checkout 正确更新 HEAD"""
        engine = engine_with_repo
        
        # 1. Create State A (Plan)
        (engine.root_dir / "f.txt").write_text("v1")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("genesis", hash_a, "State A")
        
        # 2. Create State B (Plan)
        (engine.root_dir / "f.txt").write_text("v2")
        hash_b = engine.git_db.get_tree_hash()
        engine.create_plan_node(hash_a, hash_b, "State B")
        
        assert engine._read_head() == hash_b
        
        # 3. Checkout to State A
        engine.checkout(hash_a)
        
        # 4. Assert Physical State
        assert (engine.root_dir / "f.txt").read_text() == "v1"
        
        # 5. Assert Logical State (HEAD)
        assert engine._read_head() == hash_a

class TestRootDiscovery:
    def test_find_project_root(self, tmp_path):
        # /project/.git
        # /project/src/subdir
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()
        
        subdir = project / "src" / "subdir"
        subdir.mkdir(parents=True)
        
        # Case 1: From subdir
        assert find_project_root(subdir) == project.resolve()
        
        # Case 2: From root
        assert find_project_root(project) == project.resolve()
        
        # Case 3: Outside
        outside = tmp_path / "outside"
        outside.mkdir()
        assert find_project_root(outside) is None
~~~~~

### Acts 2: 修复 `test_idempotent_node.py`

更新 `test_idempotent_plan_creation` 测试函数中的 `Engine` 实例化。

~~~~~act
write_file
~~~~~

~~~~~path
tests/test_idempotent_node.py
~~~~~

~~~~~python
import pytest
from pathlib import Path
from quipu.core.state_machine import Engine
from quipu.cli.controller import run_quipu
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

class TestIdempotentNode:
    
    def test_idempotent_plan_creation(self, tmp_path: Path):
        """验证无文件变更的操作也能生成历史节点"""
        # 1. 初始化环境
        workspace = tmp_path / "ws"
        workspace.mkdir()
        import subprocess
        subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        
        # 2. 先执行一个会产生变更的操作 (State A)
        plan_1 = "~~~act\nwrite_file a.txt\n~~~\n~~~content\nA\n~~~"
        run_quipu(plan_1, workspace, yolo=True)
        
        history_dir = workspace / ".quipu" / "history"
        
        # 此处 Engine 的实例化仅用于验证，非测试核心
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
        engine = Engine(workspace, reader=reader, writer=writer)

        nodes_1 = list(history_dir.glob("*.md"))
        assert len(nodes_1) == 1
        
        # 3. 执行一个无变更的操作 (State A -> State A)
        # 例如读取文件或运行 ls
        plan_2 = "~~~act\nread_file a.txt\n~~~"
        result = run_quipu(plan_2, workspace, yolo=True)
        
        assert result.success is True
        
        # 4. 验证是否生成了新节点
        nodes_2 = list(history_dir.glob("*.md"))
        assert len(nodes_2) == 2
        
        # 验证新节点的 input == output
        # 加载最新的节点
        latest_file = max(nodes_2, key=lambda p: p.stat().st_mtime)
        content = latest_file.read_text("utf-8")
        
        # 简单的字符串检查
        import yaml
        parts = content.split("---")
        meta = yaml.safe_load(parts[1])
        
        assert meta["input_tree"] == meta["output_tree"]
        assert meta["type"] == "plan"
~~~~~

### Acts 3: 修复 `test_navigation.py`

更新 `nav_workspace` 和 `cli_workspace` 两个 fixture 以正确实例化 `Engine`。

~~~~~act
write_file
~~~~~

~~~~~path
tests/test_navigation.py
~~~~~

~~~~~python
import pytest
import subprocess
from pathlib import Path
from typer.testing import CliRunner

from quipu.core.state_machine import Engine
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
from quipu.cli.main import app

# --- Fixtures ---

@pytest.fixture
def nav_workspace(tmp_path):
    """
    创建一个包含 Git 仓库和 Engine 实例的测试环境。
    """
    repo_path = tmp_path / "nav_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    history_dir = repo_path / ".quipu" / "history"
    reader = FileSystemHistoryReader(history_dir)
    writer = FileSystemHistoryWriter(history_dir)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    # Helper to create distinct states
    def create_state(content: str) -> str:
        (repo_path / "file.txt").write_text(content)
        return engine.git_db.get_tree_hash()

    return engine, create_state

@pytest.fixture
def runner():
    return CliRunner()

# --- 1. Unit Tests (Engine Logic) ---

class TestNavigationEngine:

    def test_basic_back_and_forward(self, nav_workspace):
        engine, create_state = nav_workspace
        
        hash_a = create_state("A")
        hash_b = create_state("B")
        
        engine.visit(hash_a)
        engine.visit(hash_b)
        
        # We are at B, go back to A
        engine.back()
        assert (engine.root_dir / "file.txt").read_text() == "A"
        
        # We are at A, go forward to B
        engine.forward()
        assert (engine.root_dir / "file.txt").read_text() == "B"

    def test_boundary_conditions(self, nav_workspace):
        engine, create_state = nav_workspace
        
        hash_a = create_state("A")
        engine.visit(hash_a)
        
        # At the end, forward should do nothing
        assert engine.forward() is None
        assert (engine.root_dir / "file.txt").read_text() == "A"
        
        # At the beginning, back should do nothing
        assert engine.back() is None
        assert (engine.root_dir / "file.txt").read_text() == "A"

    def test_history_truncation_on_new_visit(self, nav_workspace):
        engine, create_state = nav_workspace
        
        hash_a = create_state("A")
        hash_b = create_state("B")
        hash_c = create_state("C")
        hash_d = create_state("D")
        
        engine.visit(hash_a)
        engine.visit(hash_b)
        engine.visit(hash_c)
        
        # History: [A, B, C], ptr at C
        
        # Go back to B
        engine.back()
        # History: [A, B, C], ptr at B
        
        # Now visit a new state D. This should truncate C.
        engine.visit(hash_d)
        # History: [A, B, D], ptr at D
        
        # Verify state
        assert (engine.root_dir / "file.txt").read_text() == "D"
        
        # Verify that forward is now impossible
        assert engine.forward() is None
        
        # Go back twice to verify the new history
        engine.back() # -> B
        assert (engine.root_dir / "file.txt").read_text() == "B"
        engine.back() # -> A
        assert (engine.root_dir / "file.txt").read_text() == "A"
        
    def test_visit_idempotency(self, nav_workspace):
        engine, create_state = nav_workspace
        hash_a = create_state("A")
        
        engine.visit(hash_a)
        engine.visit(hash_a)
        engine.visit(hash_a)
        
        log, _ = engine._read_nav()
        # The log might contain the initial HEAD, so we check the end
        assert log[-1] == hash_a
        assert len([h for h in log if h == hash_a]) <= 1 

# --- 2. Integration Tests (CLI) ---

class TestNavigationCLI:

    @pytest.fixture
    def cli_workspace(self, tmp_path):
        ws = tmp_path / "cli_ws"
        ws.mkdir()
        subprocess.run(["git", "init"], cwd=ws, check=True, capture_output=True)
        # Create some history nodes for checkout
        history_dir = ws / ".quipu" / "history"
        reader = FileSystemHistoryReader(history_dir)
        writer = FileSystemHistoryWriter(history_dir)
        engine = Engine(ws, reader=reader, writer=writer)

        (ws / "a.txt").write_text("A")
        hash_a = engine.git_db.get_tree_hash()
        engine.create_plan_node("_" * 40, hash_a, "State A")

        (ws / "b.txt").write_text("B")
        (ws / "a.txt").unlink()
        hash_b = engine.git_db.get_tree_hash()
        engine.create_plan_node(hash_a, hash_b, "State B")
        
        return ws, hash_a, hash_b

    def test_cli_back_forward_flow(self, runner, cli_workspace):
        workspace, hash_a, hash_b = cli_workspace
        
        # Initial state is B. Let's checkout to A.
        runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])
        assert (workspace / "a.txt").exists()
        assert not (workspace / "b.txt").exists()
        
        # Now we are at A. Let's go back. It should go to the previous state (B).
        result_back = runner.invoke(app, ["back", "-w", str(workspace)])
        assert result_back.exit_code == 0
        assert "✅ 已后退到状态" in result_back.stderr
        assert (workspace / "b.txt").exists()
        assert not (workspace / "a.txt").exists()
        
        # Now we are back at B. Let's go forward to A again.
        result_fwd = runner.invoke(app, ["forward", "-w", str(workspace)])
        assert result_fwd.exit_code == 0
        assert "✅ 已前进到状态" in result_fwd.stderr
        assert (workspace / "a.txt").exists()
        assert not (workspace / "b.txt").exists()

    def test_cli_boundary_messages(self, runner, cli_workspace):
        workspace, hash_a, hash_b = cli_workspace
        
        # Go to a known state
        runner.invoke(app, ["checkout", hash_a[:7], "-w", str(workspace), "-f"])

        # Back until the beginning
        runner.invoke(app, ["back", "-w", str(workspace)]) # to B
        result1 = runner.invoke(app, ["back", "-w", str(workspace)]) # to genesis state if any was recorded
        result2 = runner.invoke(app, ["back", "-w", str(workspace)]) # one more should hit boundary
        
        assert "已到达访问历史的起点" in result2.stderr
        
        # Forward until the end
        runner.invoke(app, ["forward", "-w", str(workspace)]) # to B
        runner.invoke(app, ["forward", "-w", str(workspace)]) # to A
        result3 = runner.invoke(app, ["forward", "-w", str(workspace)]) # should fail
        
        assert "已到达访问历史的终点" in result3.stderr
~~~~~