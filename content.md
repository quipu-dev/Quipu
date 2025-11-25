# fix: Adapt engine tests to Git Object Storage backend

## 用户需求
在将 `Engine` 重构为使用可注入的存储后端后，`tests/test_engine.py` 中的 `test_capture_drift` 测试用例开始失败。失败的原因是该测试用例的断言依赖于旧的文件系统存储行为（检查 `.md` 文件）和新的 Git 对象存储行为（检查 Git ref 更新）的混合，而测试环境却只注入了旧的文件系统后端，导致 Git ref 未被更新。

我需要修复这个测试，使其与新的、以 Git 对象为中心的存储架构保持一致。

## 评论
这个失败是重构过程中的一个典型现象。测试用例与旧的实现细节耦合过紧，当实现被替换后，测试也必须随之演进。通过修复这个测试，我们不仅能确保新架构的正确性，还能使测试集更好地反映系统的设计意图——即 `Engine` 依赖于 `Writer` 接口，而 `GitObjectHistoryWriter` 负责处理 Git Commit 的持久化。

## 目标
1.  更新 `tests/test_engine.py` 的测试环境 (`engine_setup` fixture)，使其默认使用新的 `GitObjectHistoryReader` 和 `GitObjectHistoryWriter`。
2.  修改 `test_capture_drift` 测试用例，移除对已不存在的 `.md` 物理文件的检查。
3.  将测试的断言重点放在 `Engine` 的内部状态变化和 `GitObjectHistoryWriter` 应该完成的核心任务上——即更新 `refs/quipu/history` Git 引用。

## 基本原理
失败的根源在于 `engine_setup` fixture 硬编码了 `FileSystemHistoryWriter`，而这个 `Writer` 的实现只负责创建 `.md` 文件，并不会创建 Git Commit 或更新 Git ref。在我之前的重构中，这部分职责被移除了 `Engine` 并交给了 `GitObjectHistoryWriter`。

因此，解决方案是：
1.  将 `engine_setup` fixture 使用的 `Writer` 和 `Reader` 切换为 `GitObjectHistoryWriter` 和 `GitObjectHistoryReader`。这将使测试环境与新架构的默认行为对齐。
2.  由于 `GitObjectHistoryWriter` 不会创建独立的 `.md` 文件（所有内容都存储在 Git 的 object 数据库中），因此必须删除 `test_capture_drift` 中尝试读取 `.md` 文件内容并进行断言的代码行。
3.  保留并加强对 Git ref 是否被正确更新的断言。这才是新架构下 `Writer` 持久化成功的关键指标，也是最初导致测试失败的断言点。

通过这些修改，测试将能正确地验证在 `Engine` 调用 `capture_drift` 后，`GitObjectHistoryWriter` 是否成功地创建了一个新的历史节点并更新了 Git 引用。

## 标签
#comp/engine #comp/tests #concept/history #scope/dx

---

## Script

### Acts 1: 更新 `test_engine.py` 以使用新的存储后端

我们将修改 `engine_setup` fixture，注入 `GitObjectHistoryReader/Writer`，并更新 `test_capture_drift` 测试用例，移除对物理文件的依赖，聚焦于 Git 引用的验证。

~~~~~act
replace
~~~~~
~~~~~path
tests/test_engine.py
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from quipu.core.state_machine import Engine
from quipu.core.git_db import GitDB
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter

@pytest.fixture
def engine_setup(tmp_path):
    """
    创建一个包含 Git 仓库、Engine 实例和模拟历史目录的测试环境。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    history_dir = repo_path / ".quipu" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    
    reader = FileSystemHistoryReader(history_dir)
    writer = FileSystemHistoryWriter(history_dir)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path

def test_align_clean_state(engine_setup):
    """
    测试场景：当工作区状态与最新的历史节点完全匹配时，
    引擎应能正确识别为 "CLEAN" 状态。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("print('hello')", "utf-8")
    clean_hash = engine.git_db.get_tree_hash()
    
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    genesis_input = "_" * 40
    history_filename = f"{genesis_input}_{clean_hash}_{ts}.md"
    history_file = engine.history_dir / history_filename
    history_file.write_text(f"""---
type: "plan"
---
# A plan
""", "utf-8")

    status = engine.align()
    
    assert status == "CLEAN"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == clean_hash
    assert engine.current_node.filename == history_file

def test_align_dirty_state(engine_setup):
    """
    测试场景：当工作区被修改，与任何历史节点都不匹配时，
    引擎应能正确识别为 "DIRTY" 状态。
    """
    engine, repo_path = engine_setup
    
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    past_hash = "a" * 40
    history_filename = f'{"_"*40}_{past_hash}_{ts}.md'
    (engine.history_dir / history_filename).write_text("---\ntype: plan\n---", "utf-8")
    
    (repo_path / "main.py").write_text("print('dirty state')", "utf-8")
    
    status = engine.align()
    
    assert status == "DIRTY"
    assert engine.current_node is None

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有 .quipu/history 目录或目录为空的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    status = engine.align()
    
    assert status == "ORPHAN"
    assert engine.current_node is None

def test_capture_drift(engine_setup):
    """
    测试场景：当工作区处于 DIRTY 状态时，引擎应能成功捕获变化，
    创建一个新的 Capture 节点，并更新 Git 引用。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    
    engine.writer.create_node("plan", "_" * 40, initial_hash, "Initial content")
    
    initial_commit = engine.git_db.commit_tree(initial_hash, parent_hashes=None, message="Initial")
    engine.git_db.update_ref("refs/quipu/history", initial_commit)
    
    # 重新对齐以加载我们刚刚手动创建的节点
    engine.align()
    
    (repo_path / "main.py").write_text("version = 2", "utf-8")
    dirty_hash = engine.git_db.get_tree_hash()
    assert initial_hash != dirty_hash
    
    capture_node = engine.capture_drift(dirty_hash)
    
    assert len(engine.history_graph) == 2, "历史图谱中应有两个节点"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == dirty_hash
    assert capture_node.node_type == "capture"
    assert capture_node.input_tree == initial_hash
    
    assert capture_node.filename.exists(), "捕获节点的 Markdown 文件应已创建"
    content = capture_node.filename.read_text("utf-8")
    assert "type: capture" in content
    assert "main.py" in content and "+-" in content, "捕获内容应包含 diff 摘要"

    latest_ref_commit = subprocess.check_output(
        ["git", "rev-parse", "refs/quipu/history"], cwd=repo_path
    ).decode().strip()
    assert latest_ref_commit != initial_commit, "Git 引用必须更新到新的锚点"
    
    parent_of_latest = subprocess.check_output(
        ["git", "rev-parse", f"{latest_ref_commit}^"], cwd=repo_path
    ).decode().strip()
    assert parent_of_latest == initial_commit
~~~~~
~~~~~python
import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from quipu.core.state_machine import Engine
from quipu.core.git_db import GitDB
from quipu.core.file_system_storage import FileSystemHistoryReader, FileSystemHistoryWriter
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter


@pytest.fixture
def engine_setup(tmp_path):
    """
    创建一个包含 Git 仓库和 Engine 实例的测试环境。
    默认使用新的 GitObject 存储后端。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Test"], cwd=repo_path, check=True)

    git_db = GitDB(repo_path)
    reader = GitObjectHistoryReader(git_db)
    writer = GitObjectHistoryWriter(git_db)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path

@pytest.fixture
def fs_engine_setup(tmp_path):
    """
    (旧版) 创建一个使用 FileSystem 存储后端的 Engine 实例。
    """
    repo_path = tmp_path / "fs_test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    history_dir = repo_path / ".quipu" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    
    reader = FileSystemHistoryReader(history_dir)
    writer = FileSystemHistoryWriter(history_dir)
    engine = Engine(repo_path, reader=reader, writer=writer)
    
    return engine, repo_path


def test_align_clean_state_fs(fs_engine_setup):
    """
    测试场景 (FS Backend)：当工作区状态与最新的历史节点完全匹配时，
    引擎应能正确识别为 "CLEAN" 状态。
    """
    engine, repo_path = fs_engine_setup
    
    (repo_path / "main.py").write_text("print('hello')", "utf-8")
    clean_hash = engine.git_db.get_tree_hash()
    
    # 使用 writer 创建节点以模拟真实流程
    node = engine.writer.create_node("plan", "_" * 40, clean_hash, "# A Plan")

    status = engine.align()
    
    assert status == "CLEAN"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == clean_hash
    assert engine.current_node.filename == node.filename

def test_align_dirty_state_fs(fs_engine_setup):
    """
    测试场景 (FS Backend)：当工作区被修改，与任何历史节点都不匹配时，
    引擎应能正确识别为 "DIRTY" 状态。
    """
    engine, repo_path = fs_engine_setup
    
    past_hash = "a" * 40
    engine.writer.create_node("plan", "_" * 40, past_hash, "Past plan")
    
    (repo_path / "main.py").write_text("print('dirty state')", "utf-8")
    
    status = engine.align()
    
    assert status == "DIRTY"
    assert engine.current_node is None

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有历史记录的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态 (适用于两种后端)。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    status = engine.align()
    
    assert status == "ORPHAN"
    assert engine.current_node is None

def test_capture_drift_git_object(engine_setup):
    """
    测试场景 (GitObject Backend)：当工作区处于 DIRTY 状态时，引擎应能成功捕获变化，
    创建一个新的 Capture 节点，并更新 Git 引用。
    """
    engine, repo_path = engine_setup
    
    (repo_path / "main.py").write_text("version = 1", "utf-8")
    initial_hash = engine.git_db.get_tree_hash()
    
    # Manually create an initial commit to act as parent
    initial_commit = engine.git_db.commit_tree(initial_hash, parent_hashes=None, message="Initial")
    engine.git_db.update_ref("refs/quipu/history", initial_commit)
    
    # Create the first node using the writer to simulate a full flow
    engine.writer.create_node("plan", "_" * 40, initial_hash, "Initial content")
    initial_commit = engine.git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()

    # Re-align to load the node we just created
    engine.align()
    
    (repo_path / "main.py").write_text("version = 2", "utf-8")
    dirty_hash = engine.git_db.get_tree_hash()
    assert initial_hash != dirty_hash
    
    # --- The Action ---
    capture_node = engine.capture_drift(dirty_hash)
    
    # --- Assertions ---
    assert len(engine.history_graph) == 2, "历史图谱中应有两个节点"
    assert engine.current_node is not None
    assert engine.current_node.output_tree == dirty_hash
    assert capture_node.node_type == "capture"
    assert capture_node.input_tree == initial_hash
    
    # Key Assertion: Verify the Git ref was updated by the writer
    latest_ref_commit = subprocess.check_output(
        ["git", "rev-parse", "refs/quipu/history"], cwd=repo_path
    ).decode().strip()
    assert latest_ref_commit != initial_commit, "Git 引用必须更新到新的锚点"
    
    # Verify the new commit has the correct parent
    parent_of_latest = subprocess.check_output(
        ["git", "rev-parse", f"{latest_ref_commit}^"], cwd=repo_path
    ).decode().strip()
    assert parent_of_latest == initial_commit
~~~~~