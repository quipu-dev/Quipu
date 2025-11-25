# fix: 修复集成测试中的查找条件

## 用户需求
在 `test_storage_integration.py` 中，`test_full_workflow_with_git_object_storage` 测试用例失败。
原因是我们更新了摘要生成逻辑，节点摘要从原始 Act 文本变成了语义化的 "Write: a.txt"，但测试中的 `quipu find` 命令仍然使用旧的搜索关键词 "write_file a.txt"，导致找不到节点，进而导致后续的解析代码索引越界。

## 评论
这是集成测试中常见的数据不一致问题。在修改了数据生成逻辑（Writer）后，必须同步更新数据查询逻辑（Reader/Finder）。

## 目标
更新 `tests/test_storage_integration.py` 中的搜索条件，使其与新的摘要格式匹配。

## 基本原理
将搜索关键词从 `write_file a.txt` 改为 `Write: a.txt`。

## 标签
#comp/tests #scope/dx #fix

---

## Script

### Acts 1: 更新 test_storage_integration.py

~~~~~act
replace tests/test_storage_integration.py
~~~~~

~~~~~python
        # 4. Use `find` and `checkout` to go back to state A
        # --- REFACTOR START ---
        # Use the robust find_nodes API via CLI to get the target hash
        res_find = runner.invoke(app, ["find", "--summary", "write_file a.txt", "-w", str(git_workspace)])
        assert res_find.exit_code == 0
        
        # Parse the output to get the full hash
~~~~~

~~~~~python
        # 4. Use `find` and `checkout` to go back to state A
        # --- REFACTOR START ---
        # Use the robust find_nodes API via CLI to get the target hash
        res_find = runner.invoke(app, ["find", "--summary", "Write: a.txt", "-w", str(git_workspace)])
        assert res_find.exit_code == 0
        
        # Parse the output to get the full hash
~~~~~
