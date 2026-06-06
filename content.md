## [WIP] fix: 修正降序排序权重倒置并增强状态对齐集成测试

### 用户需求
修正同态树状态下对齐、导航、检索的权重判断逻辑，使系统在降序排序下正确选择高连通度的骨干节点，并修正测试用例使其包含真实的层级关系。

### 评论
这个修复能够让前一阶段的设计意图真正落地。通过理顺排序权重的方向，Quipu 的 Engine 状态机和 CLI 工具在面对重复物理树时，能够精确、无误地锁定并回归到最具历史可信度的链条上。

### 目标
1. 修正 `state_machine.py`、`navigation.py` 与 `show.py` 中的降序排序 Key，使高连通性节点排在首位。
2. 重构 `test_engine.py` 中的 `test_align_prefers_connected_node` 集成测试，加入创世父节点，提供真实的祖先层级关系。
3. 重新执行自动化测试，验证其 100% 顺利通过。

### 基本原理
在 `reverse=True` 的降序机制下，赋予我们期望排在前面的节点更**大**的数值权重。即有父节点的节点权重为 `1`，无父节点的节点权重为 `0`。
```python
key = lambda n: (1 if n.parent else 0, n.timestamp)
```
这样元组比较时 `(1, ts)` 必然大于 `(0, ts)`，从而实现“父节点连通优先”的正确降序排序。

### 标签
#intent/fix #flow/ready #priority/high
#comp/engine #comp/cli #concept/state #concept/navigation #scope/core #scope/ux
#ai/delegate
#task/domain/storage
#task/object/state-alignment-priority
#task/action/bug-fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 `state_machine.py` 中的对齐排序 key

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
        matches = [node for node in self.history_graph.values() if node.output_tree == current_hash]
        if matches:
            matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)
            found_node = matches[0]
        else:
            found_node = None
~~~~~
~~~~~python.new
        matches = [node for node in self.history_graph.values() if node.output_tree == current_hash]
        if matches:
            matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)
            found_node = matches[0]
        else:
            found_node = None
~~~~~

#### Acts 2: 修正 `navigation.py` 中的导航对齐排序 key

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python.old
            unique_output_trees = {node.output_tree for node in matches}
            if len(unique_output_trees) > 1:
                bus.error(L.navigation.checkout.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)

            if len(matches) > 1:
                matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)

            target_node = matches[0]
~~~~~
~~~~~python.new
            unique_output_trees = {node.output_tree for node in matches}
            if len(unique_output_trees) > 1:
                bus.error(L.navigation.checkout.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)

            if len(matches) > 1:
                matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)

            target_node = matches[0]
~~~~~

#### Acts 3: 修正 `show.py` 中的展示对齐排序 key

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/show.py
~~~~~
~~~~~python.old
    unique_commits = {node.commit_hash for node in matches}
    if len(unique_commits) > 1:
        unique_output_trees = {node.output_tree for node in matches}
        if len(unique_output_trees) > 1:
            bus.error(L.show.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
            raise typer.Exit(1)
        matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)
    return matches[0]
~~~~~
~~~~~python.new
    unique_commits = {node.commit_hash for node in matches}
    if len(unique_commits) > 1:
        unique_output_trees = {node.output_tree for node in matches}
        if len(unique_output_trees) > 1:
            bus.error(L.show.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
            raise typer.Exit(1)
        matches.sort(key=lambda n: (1 if n.parent else 0, n.timestamp), reverse=True)
    return matches[0]
~~~~~

#### Acts 4: 重构 `test_engine.py` 中的集成测试数据上下文

我们将增加一个初始创世节点，从而让 `node_connected` 获得高权重的 parent 指针，完成真实的对齐竞争测试。

~~~~~act
patch_file
packages/pyquipu-engine/tests/integration/test_engine.py
~~~~~
~~~~~python.old
def test_align_prefers_connected_node(engine_instance: Engine):
    engine = engine_instance
    repo_path = engine.root_dir

    # 1. 创建状态 A
    (repo_path / "file.txt").write_text("v1")
    hash_a = engine.git_db.get_tree_hash()
    
    # 2. 正常计划节点（连接链中）
    node_connected = engine.create_plan_node(EMPTY_TREE_HASH, hash_a, "connected plan")

    # 3. 本地漂移节点（孤立，无 parent）也指向 hash_a
    node_orphan = engine.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=hash_a,
        content="orphan capture",
    )

    # 4. 对齐
    engine.align()

    # 5. 验证是否优先对齐到连接链更完备的节点
    assert engine.current_node is not None
    assert engine.current_node.commit_hash == node_connected.commit_hash
~~~~~
~~~~~python.new
def test_align_prefers_connected_node(engine_instance: Engine):
    engine = engine_instance
    repo_path = engine.root_dir

    # 1. 创建初始状态并提交为第一个节点
    (repo_path / "file.txt").write_text("v0")
    hash_init = engine.git_db.get_tree_hash()
    node_init = engine.create_plan_node(EMPTY_TREE_HASH, hash_init, "init plan")

    # 2. 在其基础上创建状态 A 并作为子节点提交
    (repo_path / "file.txt").write_text("v1")
    hash_a = engine.git_db.get_tree_hash()
    node_connected = engine.create_plan_node(hash_init, hash_a, "connected plan")

    # 3. 本地漂移节点（孤立，无 parent）也指向 hash_a
    node_orphan = engine.writer.create_node(
        node_type="capture",
        input_tree=EMPTY_TREE_HASH,
        output_tree=hash_a,
        content="orphan capture",
    )

    # 4. 对齐
    engine.align()

    # 5. 验证是否优先对齐到连接链更完备的节点
    assert engine.current_node is not None
    assert engine.current_node.commit_hash == node_connected.commit_hash
~~~~~

### 下一步建议
- **执行本计划中的 acts**：由于对齐逻辑与集成测试现在都已经做好了完备对应，执行该计划后，`test_align_prefers_connected_node` 以及所有其他新增/存量测试应该都能变成绿色通过状态。
- **提交代码**：验证测试全部通过后，可以执行 git commit 保持分支清洁。
