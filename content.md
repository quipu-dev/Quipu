好的，我理解你的需求。当前 Quipu 的 Markdown 解析器在识别代码块语言时，只支持纯字母数字和下划线 (`\w`)。这导致 `python.old` 这样的语言标识符无法被正确识别，从而无法将其内容作为指令的参数 (context)。

为了支持包含点 (`.`) 或连字符 (`-`) 的语言标识符，我们需要修改 `RegexBlockParser` 中的正则表达式，使其能更灵活地匹配语言名称。

### **受影响的核心组件分析**

1.  **`packages/quipu-runtime/src/pyquipu/runtime/parser.py`**: 这里定义了 `RegexBlockParser`，其 `start_pattern` 正则表达式需要更新以支持新的语言标识符格式。
2.  **`tests/runtime/test_parser_and_basic_acts.py`**: 需要添加新的测试用例，以验证对 `python.old` 等扩展语言标识符的正确解析。

---

### **分步实施操作列表**

#### **第 1 步：修改 `RegexBlockParser` 的 `start_pattern`**

我们将扩展语言标识符的匹配规则，使其能包含点 (`.`) 和连字符 (`-`)，这是许多语言及其变体常用的命名约定。

1.  **打开文件**: `packages/quipu-runtime/src/pyquipu/runtime/parser.py`
2.  **定位代码**: 找到 `RegexBlockParser` 类的 `__init__` 方法中的 `self.start_pattern` 定义。
    ```python
    # packages/quipu-runtime/src/pyquipu/runtime/parser.py

    class RegexBlockParser(BaseParser):
        def __init__(self, fence_char: str):
            self.fence_char = fence_char
            # 原始代码: (\w*)
            self.start_pattern = re.compile(rf"^({re.escape(fence_char)}{{3,}})(\w*)\s*$", re.MULTILINE)
    ```
3.  **修改为**: 将 `(\w*)` 更改为 `([\w_.-]*)`。这将允许语言标识符包含字母、数字、下划线、点和连字符。
    ```python
    # packages/quipu-runtime/src/pyquipu/runtime/parser.py

    class RegexBlockParser(BaseParser):
        def __init__(self, fence_char: str):
            self.fence_char = fence_char
            # 修改后: ([\w_.-]*)
            self.start_pattern = re.compile(rf"^({re.escape(fence_char)}{{3,}})([\w_.-]*)\s*$", re.MULTILINE)
    ```

#### **第 2 步：添加测试用例**

为确保修改正确且没有引入回归问题，我们将添加一个专门的测试用例来验证对扩展语言标识符的解析。

1.  **打开文件**: `tests/runtime/test_parser_and_basic_acts.py`
2.  **在 `TestParser` 类中添加新测试方法**:
    ```python
    # tests/runtime/test_parser_and_basic_acts.py

    class TestParser:
        # ... 现有测试方法 ...

        def test_extended_lang_identifiers(self):
            """测试解析器是否能正确识别并捕获带有 . 或 - 的语言标识符的块内容。"""
            md = """
```act
echo
```
```python.old
# This is some old Python code
print("Hello from old version")
```
```python-new
# This is some new Python code
print("Hello from new version")
```
"""
            parser = BacktickParser()
            stmts = parser.parse(md)

            assert len(stmts) == 1
            assert stmts[0]["act"] == "echo"
            assert len(stmts[0]["contexts"]) == 2

            # 验证第一个上下文块的内容
            expected_old_code = "# This is some old Python code\nprint(\"Hello from old version\")"
            assert stmts[0]["contexts"][0].strip() == expected_old_code.strip()

            # 验证第二个上下文块的内容
            expected_new_code = "# This is some new Python code\nprint(\"Hello from new version\")"
            assert stmts[0]["contexts"][1].strip() == expected_new_code.strip()

        def test_extended_lang_identifiers_tilde(self):
            """测试 tilde 解析器是否也能处理带有 . 或 - 的语言标识符。"""
            md = """
~~~act
echo
~~~
~~~yaml.config
key: value
version: 1.0
~~~
"""
            parser = TildeParser()
            stmts = parser.parse(md)

            assert len(stmts) == 1
            assert stmts[0]["act"] == "echo"
            assert len(stmts[0]["contexts"]) == 1

            expected_yaml = "key: value\nversion: 1.0"
            assert stmts[0]["contexts"][0].strip() == expected_yaml.strip()

    ```

#### **第 3 步：更新文档 (可选，但推荐)**

虽然对于 `act` 指令本身不需要使用 `act.old` 这样的格式，但为了提高文档的完整性，可以在 `QUIPU_ACT_PROTO.md` 中提及代码块语言标识符支持的字符范围。

1.  **打开文件**: `docs/02_PROMPTS/20_Quipu开发/QUIPU_ACT_PROTO.md`
2.  **在“围栏语法 (Deep Fencing)”部分或“最佳实践”部分添加说明**:
    ```markdown
    ### 1. 围栏语法 (Deep Fencing)

    为了防止你的输出中包含的代码块（通常使用 3 个反引号）与 Quipu 指令冲突，并确保解析稳定：

    *   **符号选择**：必须优先使用波浪号 `~` 作为围栏符。
    *   **长度规定**：围栏长度**必须从 5 个字符开始**（即 `~~~~~`）。
    *   **语言标识符**: 现在支持在语言标识符中使用点 `.` 和连字符 `-` (例如 `python.old`, `json-patch`)。
    *   **结构**：操作由“动作块”开始，紧随后续的“参数块”。
    ```

---

完成以上步骤后，Quipu 将能够正确识别 ````python.old` 和 ````python.new` 这样的代码块，并将其内容作为参数传递给 `act` 指令。
