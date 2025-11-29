非常敏锐的观察。

**错误分析**:
测试失败的原因不在于 `pull-only` 的逻辑有误，而在于测试用例本身的**设置步骤顺序**出了问题。

```python
# User B creates a node but doesn't push
node_b = create_node(user_b_path, "node_from_b_local")  # <--- 1. 这里创建了节点

# [FIX] User B must subscribe to User A to be able to pull their changes.
runner.invoke(app, ["sync", "--work-dir", str(user_b_path)])  # <--- 2. 这里为了初始化用户身份运行了 sync
```

默认的 `sync` 命令使用的是 `BIDIRECTIONAL`（双向）模式。因此，步骤 2 不仅初始化了用户 ID，还顺便把步骤 1 中创建的 `node_b` 推送到了远程。
这导致后续的断言 `assert node_b not in remote_refs` 必然失败，因为节点在测试的主要动作（pull-only sync）开始之前就已经在远程了。

**解决方案**:
调整测试步骤的顺序：先进行 Onboard（此时没有新节点，Push 为空操作），然后再创建 `node_b`，最后执行 `pull-only` 测试。

## [WIP] test: 修正 test_pull_only_mode 中初始化顺序导致的意外推送

### 错误分析
测试 `test_pull_only_mode` 在准备阶段调用了默认的 `sync` 命令来初始化 User B 的身份配置。然而，在此之前 `node_b` 已经被创建。由于默认 `sync` 包含推送操作，导致 `node_b` 在测试核心逻辑（`pull-only`）执行前就被推送到远程，从而导致后续“远程不应包含该节点”的断言失败。

### 用户需求
确保测试环境的设置步骤不会产生副作用（如意外推送数据），从而准确验证 `pull-only` 模式的行为。

### 评论
这是一个典型的测试逻辑缺陷，修正顺序即可解决。

### 目标
在 `tests/integration/test_sync_modes.py` 中调整 `test_pull_only_mode` 的执行顺序：Onboard -> Create Node -> Pull-Only Sync。

### 基本原理
通过在创建任何历史节点之前运行一次 `sync`，我们可以完成用户 ID 的生成和配置文件的初始化，而不会产生任何实质性的 Git 推送。这样就保证了 `node_b` 仅存在于本地，为验证 `pull-only` 不会推送它提供了干净的初始状态。

### 标签
#intent/fix #flow/ready #priority/medium #comp/tests #concept/sync #scope/core #ai/instruct #task/domain/testing #task/object/sync-test #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 调整测试步骤顺序

~~~~~act
patch_file
tests/integration/test_sync_modes.py
~~~~~
~~~~~python
        # User A creates a node and pushes
        node_a = create_node(user_a_path, "node_from_a_for_pull")
        runner.invoke(app, ["sync", "--work-dir", str(user_a_path)])

        # User B creates a node but doesn't push
        node_b = create_node(user_b_path, "node_from_b_local")

        # [FIX] User B must subscribe to User A to be able to pull their changes.
        runner.invoke(app, ["sync", "--work-dir", str(user_b_path)])  # Onboard B first
        config_path_b = user_b_path / ".quipu" / "config.yml"
        with open(config_path_b, "r") as f:
            config_b = yaml.safe_load(f)
~~~~~
~~~~~python
        # User A creates a node and pushes
        node_a = create_node(user_a_path, "node_from_a_for_pull")
        runner.invoke(app, ["sync", "--work-dir", str(user_a_path)])

        # [FIX] User B must subscribe to User A to be able to pull their changes.
        # Onboard B first (before creating local nodes to avoid accidental push)
        runner.invoke(app, ["sync", "--work-dir", str(user_b_path)])
        
        # User B creates a node but doesn't push
        node_b = create_node(user_b_path, "node_from_b_local")

        config_path_b = user_b_path / ".quipu" / "config.yml"
        with open(config_path_b, "r") as f:
            config_b = yaml.safe_load(f)
~~~~~

### 下一步建议
运行测试 `pytest tests/integration/test_sync_modes.py`。
