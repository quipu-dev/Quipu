这是因为在当前的 `create_engine` 实现中，默认的 `storage.type` 是 `git_object`，在这种模式下 `db_manager` 不会被初始化，因此 `history.sqlite` 不会被创建，`Hydrator` 也不会运行。

为了测试 SQLite 补水和聚合功能，我们需要在测试用例中显式将 User B 的存储类型配置为 `sqlite`。

## fix: 修复集成测试中 SQLite 数据库未创建的问题

### 错误分析
测试用例 `test_collaboration_subscribe_and_fetch` 断言 `history.sqlite` 文件存在，但默认配置下 Quipu 运行在纯 Git 模式，不创建 SQLite 缓存。只有当配置 `storage.type = sqlite` 时，`create_engine` 才会初始化 `DatabaseManager` 并触发补水逻辑。

### 用户需求
- 修复 `test_sync_workflow.py`，使其能正确验证数据补水逻辑。

### 目标
- 在测试用例中修改 User B 的 `config.yml`，启用 SQLite 存储模式。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/integration-test #task/action/fix-config #task/state/continue

---

### Script

#### Acts 1: 在测试中启用 SQLite 配置

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python
        # User B subscribes to User A
        config_path_b = user_b_path / ".quipu" / "config.yml"
        with open(config_path_b, "r") as f:
            config_b = yaml.safe_load(f)
        config_b["sync"]["subscriptions"] = [user_a_id]
        with open(config_path_b, "w") as f:
            yaml.dump(config_b, f)

        # User B syncs again to fetch User A's data
~~~~~
~~~~~python
        # User B subscribes to User A
        config_path_b = user_b_path / ".quipu" / "config.yml"
        with open(config_path_b, "r") as f:
            config_b = yaml.safe_load(f)
        config_b["sync"]["subscriptions"] = [user_a_id]
        # Explicitly enable SQLite storage to test hydration
        if "storage" not in config_b:
            config_b["storage"] = {}
        config_b["storage"]["type"] = "sqlite"
        with open(config_path_b, "w") as f:
            yaml.dump(config_b, f)

        # User B syncs again to fetch User A's data
~~~~~

### 下一步建议
重新运行测试。
