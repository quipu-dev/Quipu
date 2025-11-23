import pytest
import subprocess
from pathlib import Path
from datetime import datetime
from core.engine import Engine
from core.git_db import GitDB

@pytest.fixture
def engine_setup(tmp_path):
    """
    创建一个包含 Git 仓库、Engine 实例和模拟历史目录的测试环境。
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    
    engine = Engine(repo_path)
    engine.history_dir.mkdir(parents=True, exist_ok=True)
    
    return engine, repo_path

def test_align_clean_state(engine_setup):
    """
    测试场景：当工作区状态与最新的历史节点完全匹配时，
    引擎应能正确识别为 "CLEAN" 状态。
    """
    engine, repo_path = engine_setup
    
    # 1. 在工作区创建一个文件并获取其状态哈希
    (repo_path / "main.py").write_text("print('hello')", "utf-8")
    clean_hash = engine.git_db.get_tree_hash()
    
    # 2. 手动伪造一个历史文件，其 output_tree 与当前状态匹配
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    # 创世节点的 input_hash 可以是全零或下划线
    genesis_input = "_" * 40
    
    history_filename = f"{genesis_input}_{clean_hash}_{ts}.md"
    history_file = engine.history_dir / history_filename
    history_file.write_text(f"""---
type: "plan"
---
# A plan
""", "utf-8")

    # 3. 运行对齐方法
    status = engine.align()
    
    # 4. 断言结果
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
    
    # 1. 伪造一个过去的历史节点
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    past_hash = "a" * 40
    history_filename = f'{"_"*40}_{past_hash}_{ts}.md'
    (engine.history_dir / history_filename).write_text("---\ntype: plan\n---", "utf-8")
    
    # 2. 在工作区创建一个新文件，确保当前 hash 与历史不匹配
    (repo_path / "main.py").write_text("print('dirty state')", "utf-8")
    
    # 3. 运行对齐
    status = engine.align()
    
    # 4. 断言
    assert status == "DIRTY"
    assert engine.current_node is None # 在漂移状态下，引擎不应锁定到任何节点

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有 .axon/history 目录或目录为空的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态。
    """
    engine, repo_path = engine_setup
    
    # 1. 确保 history 目录是空的 (fixture 已经保证了这一点)
    # 2. 在工作区创建文件
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    # 3. 运行对齐
    status = engine.align()
    
    # 4. 断言
    assert status == "ORPHAN"
    assert engine.current_node is None
    """
    测试场景：当工作区被修改，与任何历史节点都不匹配时，
    引擎应能正确识别为 "DIRTY" 状态。
    """
    engine, repo_path = engine_setup
    
    # 1. 伪造一个过去的历史节点
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    past_hash = "a" * 40
    history_filename = f'{"_"*40}_{past_hash}_{ts}.md'
    (engine.history_dir / history_filename).write_text("---\ntype: plan\n---", "utf-8")
    
    # 2. 在工作区创建一个新文件，确保当前 hash 与历史不匹配
    (repo_path / "main.py").write_text("print('dirty state')", "utf-8")
    
    # 3. 运行对齐
    status = engine.align()
    
    # 4. 断言
    assert status == "DIRTY"
    assert engine.current_node is None # 在漂移状态下，引擎不应锁定到任何节点

def test_align_orphan_state(engine_setup):
    """
    测试场景：在一个没有 .axon/history 目录或目录为空的项目中运行时，
    引擎应能正确识别为 "ORPHAN" 状态。
    """
    engine, repo_path = engine_setup
    
    # 1. 确保 history 目录是空的 (fixture 已经保证了这一点)
    # 2. 在工作区创建文件
    (repo_path / "main.py").write_text("print('new project')", "utf-8")
    
    # 3. 运行对齐
    status = engine.align()
    
    # 4. 断言
    assert status == "ORPHAN"
    assert engine.current_node is None