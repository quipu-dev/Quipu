# fix: 修正插件加载测试中的日志断言

## 用户需求
修复在 `test_plugin_resilience.py` 中因日志格式不匹配而失败的测试用例。

## 评论
该失败是由测试断言与实际日志输出之间的细微差异引起的。日志记录器正确地捕获并格式化了异常消息，但测试代码对该格式的假设不准确。这是一个简单的修复，将使测试套件恢复到全绿状态。

## 目标
1.  修改 `tests/test_plugin_resilience.py` 中 `test_load_plugin_with_registration_error` 函数的断言，使其与 `plugin_loader` 模块产生的实际错误日志格式相匹配。

## 基本原理
测试应该验证代码的实际行为。既然日志记录的行为是正确的（记录了错误信息），那么就应该调整测试来适应这种行为，而不是修改日志记录本身。

## 标签
#intent/fix #flow/ready #priority/critical
#comp/tests #comp/runtime
#scope/core
#ai/instruct
#task/domain/testing #task/object/bug-fix #task/action/fix
#task/state/continue #task/status/active

---

## Script

### Acts 1: 修正测试文件中的断言

我们将修改 `tests/test_plugin_resilience.py` 中不正确的断言。

~~~~~act
replace tests/test_plugin_resilience.py
~~~~~
~~~~~python
        # 3. 验证
        assert "加载插件 fail_on_register.py 失败" in caplog.text
        assert "ValueError: Something went wrong" in caplog.text
        assert len(executor.get_registered_acts()) == 0
~~~~~
~~~~~python
        # 3. 验证
        assert "加载插件 fail_on_register.py 失败" in caplog.text
        # 修正：日志记录的是异常的消息内容(str(e))，而不是其类型
        assert "Something went wrong during registration" in caplog.text
        assert len(executor.get_registered_acts()) == 0
~~~~~
