好的，我设计了针对此次逻辑重构的专项测试方案。该方案包含两个核心测试文件：一个用于验证 Engine 层的对齐优先级和存储层的关系聚合逻辑，另一个用于验证 CLI 层在处理同态树哈希时的导航容错性。

这些测试将模拟你之前遇到的“分布式捕获导致的重复状态”场景，确保系统在面临同态数据时表现得更加智能。

## [WIP] test: 增加针对同态树哈希逻辑的单元与集成测试

### 用户需求
需要自动化测试来验证系统对“相同物理树哈希（`output_tree`）对应不同 Quipu 提交（Commit Hash）”场景的处理能力，包括 Engine 层的智能对齐、存储层的可达性合并以及 CLI 层的导航容错。

### 评论
高质量的测试是确保复杂分布式状态对齐逻辑稳健性的唯一手段。通过模拟手动构造的同态节点，我们可以精确验证算法在极端边缘情况下的表现。

### 目标
1.  **验证对齐优先级**：确保 Engine 总是优先选择有父节点的节点进行对齐。
2.  **验证可达性聚合**：确保 `HistoryReader` 能合并所有等价起点的祖先/后代集合。
3.  **验证导航容错**：确保 `checkout` 在遇到相同物理树时不再报错。

### 基本原理
利用 `git_db` 的底层接口手动构造两个具有相同 `output_tree` 但 parent 不同的 commit，然后通过 `Engine` 和 CLI 命令对其进行操作，观察系统的选择和反馈。

### 标签
#intent/tooling #flow/ready #priority/high
#comp/engine #comp/cli #comp/tests #concept/state #concept/navigation
#ai/delegate
#task/domain/testing
#task/object/duplicate-tree-logic
#task/action/test-implementation
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 创建 Engine 层同态逻辑单元测试

该测试文件专门用于验证存储层在多起点场景下的关系计算，以及 Engine 层的智能对齐算法。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/pyquipu-engine/tests/engine
~~~~~

~~~~~act
write_file
packages/pyquipu-engine/tests/engine/test_duplicate_trees.py
~~~~~
~~~~~python
import pytest
from quipu.spec.constants import EMPTY_TREE_HASH

def test_engine_align_priority_with_identical_trees(engine_instance):
    """验证 align 逻辑是否优先选择连通性更好的节点。"""
    ws = engine_instance.root_dir
    git_db = engine_instance.git_db
    
    # 1. 构造一个正常的骨干分支: Root -> Node A
    (ws / "file.txt").write_text("v1")
    tree_v1 = git_db.get_tree_hash()
    node_a = engine_instance.create_plan_node(
        EMPTY_TREE_HASH, tree_v1, "Normal Node A", summary_override="Bone Node"
    )
    
    # 2. 手动构造一个同态但孤立的节点: Node B (Tree 也是 tree_v1, 但 parent 是空)
    # 我们直接通过底层 writer 创建一个不带父节点的同态节点
    node_b = engine_instance.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=tree_v1,
        content="Isolated Node B",
        summary_override="Isolated Node"
    )
    
    # 重新加载 graph 模拟重启或同步后的状态
    engine_instance.align()
    
    # 验证: 虽然有两个节点都指向 tree_v1，但 align 应该选择有 parent 的 node_a
    assert engine_instance.current_node is not None
    assert engine_instance.current_node.commit_hash == node_a.commit_hash
    assert engine_instance.current_node.parent is not None

def test_storage_reachability_aggregation(engine_instance):
    """验证可达性计算是否跨越同态节点进行了联合。"""
    ws = engine_instance.root_dir
    git_db = engine_instance.git_db
    
    # 分支 1: Root -> A -> B (Tree X)
    (ws / "f").write_text("1")
    h_root = engine_instance.create_plan_node(EMPTY_TREE_HASH, git_db.get_tree_hash(), "1").output_tree
    
    (ws / "f").write_text("2")
    h_a = engine_instance.create_plan_node(h_root, git_db.get_tree_hash(), "2").output_tree
    
    (ws / "f").write_text("X")
    h_x = git_db.get_tree_hash()
    node_b = engine_instance.create_plan_node(h_a, h_x, "3")
    
    # 分支 2: C (Tree X) - 孤立同态点
    node_c = engine_instance.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=h_x,
        content="Isolated"
    )
    
    # 刷新引擎
    engine_instance.align()
    
    # 验证祖先聚合: 从 h_x 开始找，应该能找到 h_root 和 h_a
    ancestors = engine_instance.reader.get_ancestor_output_trees(h_x)
    assert h_root in ancestors
    assert h_a in ancestors
    
    # 验证后代聚合: 从 h_root 开始找，应该能找到 h_x (不论是通过 node_b 还是 node_c 触达)
    descendants = engine_instance.reader.get_descendant_output_trees(h_root)
    assert h_x in descendants
~~~~~

#### Acts 2: 创建 CLI 层导航集成测试

验证 `checkout` 命令在面对同态状态时不再因歧义而报错，并支持直接使用 `commit_hash`。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/pyquipu-cli/tests/cli
~~~~~

~~~~~act
write_file
packages/pyquipu-cli/tests/cli/test_navigation_duplicates.py
~~~~~
~~~~~python
import pytest
from quipu.cli.main import app
from quipu.spec.constants import EMPTY_TREE_HASH

def test_checkout_identical_tree_ambiguity_bypass(runner, quipu_workspace):
    """验证 checkout 在遇到同态树时是否能自动规避歧义。"""
    ws, git_db, engine = quipu_workspace
    
    # 1. 创建两个同态节点
    (ws / "data.txt").write_text("Hello")
    tree_h = git_db.get_tree_hash()
    
    node_1 = engine.create_plan_node(EMPTY_TREE_HASH, tree_h, "Plan 1")
    node_2 = engine.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=tree_h,
        content="Capture 2"
    )
    
    # 2. 尝试使用 tree hash 前缀进行检出
    # 以前这会因为匹配到两个节点而报错
    prefix = tree_h[:8]
    result = runner.invoke(app, ["checkout", prefix, "--work-dir", str(ws), "-f"])
    
    assert result.exit_code == 0
    assert "Workspace reset to target state" in result.output or "noAction" in result.output

def test_checkout_by_commit_hash(runner, quipu_workspace):
    """验证是否可以通过精确的 commit_hash 进行检出。"""
    ws, git_db, engine = quipu_workspace
    
    (ws / "data.txt").write_text("Target")
    node = engine.create_plan_node(EMPTY_TREE_HASH, git_db.get_tree_hash(), "Target Plan")
    commit_hash = node.commit_hash
    
    # 先切回起点
    engine.visit(EMPTY_TREE_HASH)
    assert not (ws / "data.txt").exists()
    
    # 通过 commit_hash 检出
    result = runner.invoke(app, ["checkout", commit_hash[:10], "--work-dir", str(ws), "-f"])
    assert result.exit_code == 0
    assert (ws / "data.txt").read_text() == "Target"
~~~~~

### 下一步建议
测试已经部署完成。你可以通过运行 `pytest packages/pyquipu-engine/tests/engine/test_duplicate_trees.py` 和 `pytest packages/pyquipu-cli/tests/cli/test_navigation_duplicates.py` 来验证之前的逻辑重构是否达到了预期效果。如果测试通过，说明系统已经具备了处理分布式重复状态的能力。
