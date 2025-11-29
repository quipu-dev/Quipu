分析正确。测试失败了，并且错误日志非常清晰地指出了问题所在。

`TypeError: Engine.create_plan_node() got an unexpected keyword argument 'content'`

这表明我在创建 `create_plan_node_with_change` 辅助函数时，调用 `engine.create_plan_node` 方法使用了错误的关键字参数名。我使用了 `content=message`，而 `Engine` 的 `create_plan_node` 方法期望的参数名应该是 `plan_content`。

这是一个简单的笔误，我将立即生成计划来修复它。

## [WIP] fix: 修复测试辅助函数中的错误参数名

### 错误分析
在 `tests/helpers.py` 中新创建的 `create_plan_node_with_change` 函数中，调用 `engine.create_plan_node` 时，错误地将 `plan_content` 参数写成了 `content`。这导致了 `TypeError`，使得所有依赖此辅助函数的测试都失败了。

### 用户需求
修正 `tests/helpers.py` 文件中的错误，使测试能够通过。

### 评论
这是一个典型的重构过程中引入的小错误。清晰的错误日志和全面的测试覆盖使得定位和修复此类问题变得非常高效。

### 目标
1.  修改 `tests/helpers.py` 文件。
2.  将 `engine.create_plan_node(...)` 调用中的 `content=...` 参数更正为 `plan_content=...`。

### 基本原理
通过一个精准的 `patch_file` 操作，我们可以修正这个笔误，而无需重写整个文件。这将使测试恢复正常，并完成我们之前开始的重构任务。

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-helpers #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修正 `tests/helpers.py` 中的参数名

我们将 `content=message` 替换为 `plan_content=message`。

~~~~~act
patch_file tests/helpers.py
~~~~~
~~~~~python
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.create_plan_node(input_tree=parent_hash, output_tree=new_hash, content=message)
    return new_hash
~~~~~
~~~~~python
    """
    (engine.root_dir / file_name).write_text(content)
    new_hash = engine.git_db.get_tree_hash()
    engine.create_plan_node(input_tree=parent_hash, output_tree=new_hash, plan_content=message)
    return new_hash
~~~~~

### 下一步建议
修正已完成。请再次运行测试，确认所有错误都已解决。测试通过后，我们就可以提交这次重构了。
