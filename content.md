# fix-test: 修复 TUI 摘要测试用例以匹配新实现

## 用户需求
在运行 `pytest` 时，`tests/test_ui_logic.py` 中的 `TestUiLogic.test_get_node_summary` 测试用例失败。失败原因是该测试错误地假设 TUI 会从 `node.content` 动态生成摘要，而新实现是直接使用 `node.summary` 字段。

## 评论
这是一个典型的因代码重构而导致测试用例过时的案例。修复此测试可以确保我们对 TUI 的渲染逻辑有正确的验证，并消除测试套件中的失败项。

## 目标
1.  修改 `tests/test_ui_logic.py` 中的 `test_get_node_summary` 函数。
2.  更新测试逻辑，使其验证 `QuipuUiApp._get_node_summary` 方法能正确返回 `QuipuNode` 实例中预设的 `summary` 字段。
3.  同时验证当 `summary` 字段为空时，该方法能正确回退到 `"No description"`。

## 基本原理
测试应该验证代码的**实际行为**，而不是**过时的期望**。本次修复将使测试用例与 `QuipuUiApp` 的当前实现保持一致。`QuipuUiApp` 的设计目标是高性能渲染，因此它消费预处理好的数据 (`node.summary`)，而不是在渲染循环中执行昂贵的解析操作。测试代码必须反映这一设计决策。

## 标签
#comp/tests #comp/cli #scope/dx #fix

---

## Script

### Acts 1: 修正测试用例

我将重写 `test_get_node_summary` 函数，使其正确反映 TUI 的行为。

~~~~~act
replace
~~~~~
~~~~~path
tests/test_ui_logic.py
~~~~~
~~~~~python
    def test_get_node_summary(self):
        node = QuipuNode("a", "b", datetime.now(), Path("f"), "plan", content="~~~act\nrun\n~~~")
        app = QuipuUiApp([], None)
        assert app._get_node_summary(node) == "run"
~~~~~
~~~~~python
    def test_get_node_summary(self):
        """
        测试 TUI 是否正确使用预加载的 summary 字段，而不是动态解析。
        """
        app = QuipuUiApp([], None)

        # 案例 1: 节点带有预设的 summary
        # TUI 应该直接使用它。
        node_with_summary = QuipuNode(
            "a", "b", datetime.now(), Path("f1"), "plan",
            summary="This is a pre-calculated summary."
        )
        assert app._get_node_summary(node_with_summary) == "This is a pre-calculated summary."

        # 案例 2: 节点的 summary 为空
        # TUI 应该回退到默认值。
        node_without_summary = QuipuNode(
            "c", "d", datetime.now(), Path("f2"), "capture",
            summary=""  # 明确为空
        )
        assert app._get_node_summary(node_without_summary) == "No description"
~~~~~
