好的。

### fix(tests): 修复因 HistoryReader 接口变更导致的测试失败

#### 评论
本次提交修复了在 `HistoryReader` 接口中添加 `get_descendant_output_trees` 和 `get_node_position` 方法后，导致整个测试套件大面积失败的问题。

#### 目标
-   使所有测试用例恢复并通过。

#### 基本原理
-   在测试使用的模拟类 `InMemoryHistoryManager` (用于 `engine` 测试) 和 `MockHistoryReader` (用于 `cli` 测试) 中，实现了新增的抽象方法。
-   更新了部分 `cli` 测试用例的断言逻辑，以匹配新的双向可达性模型（祖先+后代）。

#### 标签
#intent/fix #flow/done #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 提交测试修复

~~~~~act
git_add
tests/helpers.py
tests/cli/test_view_model.py
tests/cli/test_tui_reachability.py
~~~~~
~~~~~act
git_commit
~~~~~
~~~~~
fix(tests): 修复因 HistoryReader 接口变更导致的测试失败

在 `HistoryReader` 接口中添加 `get_descendant_output_trees` 和
`get_node_position` 两个抽象方法后，所有依赖该接口的测试模拟类
（`InMemoryHistoryManager` 和 `MockHistoryReader`）都未能提供实现，
导致 `TypeError` 和大面积测试失败。

本次提交为这两个模拟类添加了相应的方法实现，并更新了受影响的
测试用例的断言逻辑，以反映新的双向可达性模型。
~~~~~
