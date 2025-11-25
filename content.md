# fix-test: 修复 `test_storage_writer` 中的 `mocker` 依赖问题

## 用户需求
`pytest` 执行 `tests/test_storage_writer.py` 时失败，报告 `fixture 'mocker' not found` 错误。需要修复此问题。

## 评论
分析 `pytest` 的错误输出后发现，`test_generate_summary` 函数在其参数中请求了 `mocker` fixture，但该 fixture（来自 `pytest-mock` 插件）在测试环境中不可用。

进一步检查代码发现，该测试函数虽然请求了 `mocker`，但并未实际使用它来创建 mock 对象。它直接从 `unittest.mock` 导入并使用了 `MagicMock`。因此，`mocker` 参数是一个未被使用的、多余的依赖。

移除这个不必要的参数是解决此问题的最直接、最干净的方法，因为它消除了对 `pytest-mock` 插件的隐式依赖，使测试代码更加自洽和健壮。

## 目标
修改 `tests/test_storage_writer.py` 文件，从 `test_generate_summary` 函数的签名中移除 `mocker` 参数，以解决 `fixture not found` 的错误。

## 基本原理
测试失败的根本原因是测试函数签名请求了一个不存在的 `pytest` fixture。由于该 fixture 在函数体内并未被使用，最简单的解决方案是直接移除该参数，消除对 `pytest-mock` 插件的依赖。这不会影响测试的逻辑，因为 `MagicMock` 已经被直接导入和使用。

## 标签
#comp/tests #scope/dx

---

## Script

### Acts 1: 移除未使用的 mocker fixture

我们将在 `test_generate_summary` 函数的定义中删除 `mocker` 参数。

~~~~~act
replace
~~~~~
~~~~~path
tests/test_storage_writer.py
~~~~~
~~~~~python
    )
    def test_generate_summary(self, mocker, node_type, content, kwargs, expected_summary):
        mock_git_db = MagicMock(spec=GitDB)
        mock_git_db.get_diff_name_status.return_value = [
            ("M", "path/to/file1.py"), 
            ("A", "file2.js"), 
            ("D", "old.css")
        ]
~~~~~
~~~~~python
    )
    def test_generate_summary(self, node_type, content, kwargs, expected_summary):
        mock_git_db = MagicMock(spec=GitDB)
        mock_git_db.get_diff_name_status.return_value = [
            ("M", "path/to/file1.py"),
            ("A", "file2.js"),
            ("D", "old.css")
        ]
~~~~~