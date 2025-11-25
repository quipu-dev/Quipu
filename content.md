# fix-test 修复因存储层重构导致的 `checkout` 安全捕获测试失败

## 用户需求
在 `pytest` 测试套件中，`TestCheckoutCLI.test_cli_checkout_with_safety_capture` 测试用例失败。该测试旨在验证当工作区处于“脏”状态（存在未记录的变更）时，`quipu checkout` 命令是否会自动创建一个快照 (Capture 节点) 来保存这些变更，然后再切换到目标状态。失败的原因是测试代码直接检查文件系统中的历史文件数量，而新的 Git 对象存储后端不再创建这些文件。

## 评论
这是完成存储层重构后的最后一步清理工作。修复这个测试非常重要，因为它验证了 `checkout` 命令的一个关键安全特性——防止用户意外丢失未保存的工作。通过将测试重构为与存储后端解耦，我们不仅修复了当前的失败，也提高了测试套件的长期健壮性。

## 目标
*   修复 `tests/test_integration_v2.py` 中失败的 `test_cli_checkout_with_safety_capture` 测试。
*   确保该测试的验证逻辑不再依赖于特定的存储实现（文件系统），而是通过抽象的 `HistoryReader` 接口来工作。

## 基本原理
修复方案的核心是将测试中断言所依赖的数据源，从直接的文件系统扫描 (`.quipu/history/*.md`) 切换为通过 `_setup_engine` 工厂函数获取 `Engine` 实例，并调用其 `engine.reader.load_all_nodes()` 方法。这个方法遵循我们在前几步中建立的接口，可以透明地从文件系统或 Git 对象库中读取历史节点。通过在 `checkout` 操作前后分别调用此方法来获取节点数量，我们可以准确地验证是否有名为“安全捕获”的新增节点，而无需关心它具体是如何被存储的。

## 标签
#comp/tests #comp/cli #fix #concept/history #scope/dx

---

## Script

### Acts 1: 重构失败的测试用例

修改 `tests/test_integration_v2.py`，将 `test_cli_checkout_with_safety_capture` 中检查历史节点数量的方式，从直接扫描文件系统改为通过 `Engine` 的 `Reader` 接口获取。

~~~~~act
replace tests/test_integration_v2.py
~~~~~

~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        workspace, hash_a, hash_b = populated_workspace
        
        # Make the workspace dirty
        (workspace / "c_dirty.txt").write_text("uncommitted change")
        
        history_dir = workspace / ".quipu" / "history"
        num_nodes_before = len(list(history_dir.glob("*.md")))

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])

        assert result.exit_code == 0
        assert "⚠️  检测到当前工作区存在未记录的变更" in result.stderr
        
        num_nodes_after = len(list(history_dir.glob("*.md")))
        assert num_nodes_after == num_nodes_before + 1, "A new capture node should have been created"

        # Check final state is correct
        assert (workspace / "a.txt").exists()
        assert not (workspace / "c_dirty.txt").exists()
~~~~~

~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from quipu.cli.main import _setup_engine
        workspace, hash_a, hash_b = populated_workspace
        
        # Make the workspace dirty
        (workspace / "c_dirty.txt").write_text("uncommitted change")
        
        # Get node count via the storage-agnostic reader interface
        engine_before = _setup_engine(workspace)
        num_nodes_before = len(engine_before.reader.load_all_nodes())

        result = runner.invoke(app, ["checkout", hash_a[:8], "--work-dir", str(workspace), "--force"])

        assert result.exit_code == 0, result.stderr
        assert "⚠️  检测到当前工作区存在未记录的变更" in result.stderr
        
        # Get node count again after the operation
        engine_after = _setup_engine(workspace)
        num_nodes_after = len(engine_after.reader.load_all_nodes())
        assert num_nodes_after == num_nodes_before + 1, "A new capture node should have been created"

        # Check final state is correct
        assert (workspace / "a.txt").exists()
        assert not (workspace / "c_dirty.txt").exists()
~~~~~