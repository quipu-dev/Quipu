## [WIP] fix: 修复 mock_runtime_bus 以适配 render_to_string

### 错误分析
测试失败的原因是 `mock_runtime_bus` fixture 中的 Mock 对象没有配置 `render_to_string` 方法的副作用。
1.  代码中现在调用 `bus.render_to_string("some.id")`。
2.  Mock 对象默认返回一个新的 `MagicMock` 实例。
3.  `ExecutionError` 被抛出，包含这个 Mock 对象作为 message。
4.  `pytest.raises(..., match="some.id")` 试图匹配异常消息，但发现它是 `<MagicMock ...>`，因此断言失败。

此前 `bus.get` 被 Mock 为返回 `msg_id` 字符串，现在需要对 `render_to_string` 做同样的处理。

### 用户需求
修复 `pyquipu-runtime` 的单元测试失败。

### 评论
这是一个典型的重构后测试夹具（Test Fixture）更新遗漏。修复此 Mock 行为将使测试能够正确验证业务逻辑是否传递了正确的消息 ID。

### 目标
修改 `packages/pyquipu-test-utils/src/quipu/test_utils/fixtures.py`，配置 `m_bus.render_to_string` 返回输入的 `msg_id`。

### 基本原理
为了验证“意图”（即代码试图渲染哪条消息），我们在测试中让 Bus 直接回显消息 ID。这样测试就可以断言 `ExecutionError("acts.error.missingArgs")` 被抛出，而不是验证最终渲染的自然语言文本。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/executor #task/domain/testing #task/object/fixture #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 更新 mock_runtime_bus

~~~~~act
patch_file
packages/pyquipu-test-utils/src/quipu/test_utils/fixtures.py
~~~~~
~~~~~python
@pytest.fixture
def mock_runtime_bus(monkeypatch):
    m_bus = MagicMock()
    # 让 bus.get 返回传入的 msg_id，方便测试断言语义
    m_bus.get.side_effect = lambda msg_id, **kwargs: msg_id

    patch_targets = [
~~~~~
~~~~~python
@pytest.fixture
def mock_runtime_bus(monkeypatch):
    m_bus = MagicMock()
    # 让 bus.render_to_string (及旧的 get) 返回传入的 msg_id 字符串
    # 这样测试代码断言异常消息时，能匹配到预期的 ID (例如 "acts.error.missingArgs")
    def echo_id(msg_id, **kwargs):
        return str(msg_id)

    m_bus.get.side_effect = echo_id
    m_bus.render_to_string.side_effect = echo_id

    patch_targets = [
~~~~~

### 下一步建议
运行测试以确认修复。如果所有单元测试通过，我们可以继续进行更深层次的重构，例如引入 `L` 指针。
