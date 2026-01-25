好的，我来分析并修复这个失败的测试。

## [WIP] fix(cli): 统一 `list-acts` 命令的输出流以修复测试

### 错误分析
测试 `test_cli_list_acts` 失败的根本原因是，测试用例的断言与 `run --list-acts` 命令的实际输出行为不匹配。

1.  **断言**: 测试 `assert 'write_file' in result.stdout` 期望在标准输出 (`stdout`) 中找到 act 的名称 (`write_file`)。
2.  **实际行为**: 当前的实现将 act 列表的输出分成了两部分：
    *   act 的名称（例如 `🔹 write_file`）通过 `bus.info` 发送到了标准错误 (`stderr`)。
    *   act 的文档字符串（当前为空，所以显示为 `暂无说明`）通过 `bus.data` 发送到了标准输出 (`stdout`)。

因此，`stdout` 中只包含文档字符串，不包含 act 名称，导致断言失败。

### 用户需求
修复 `tests/integration/test_cli_workflow.py::TestCLIWrapper::test_cli_list_acts` 测试用例的失败。

### 评论
将 act 的名称和其文档字符串输出到不同的流（`stderr` 和 `stdout`）是一种不佳的用户体验。用户期望看到一个完整的、连续的列表。

因此，修复方案不仅是为了通过测试，也是为了改进 CLI 的可用性。我将修改实现，将 act 的名称和其文档字符串统一输出到 `stdout`，这符合数据输出到 `stdout`，元信息输出到 `stderr` 的原则。

### 目标
1.  修改 `quipu run --list-acts` 命令的实现，将 act 名称和其文档字符串合并后一起输出到 `stdout`。
2.  对 `quipu axon --list-acts` 命令执行相同的修改，因为它复用了相同的逻辑。

### 基本原理
我将利用 `pyquipu.bus` 的 `bus.get()` 方法。这个方法可以像 `bus.info()` 一样格式化消息字符串，但不会立即将其打印出来，而是返回格式化后的字符串。

修改后的逻辑将是：
1.  在循环中，使用 `bus.get()` 获取格式化后的 act 名称行（例如 `🔹 write_file`）。
2.  将这个名称行与 act 的文档字符串拼接成一个完整的条目。
3.  使用 `bus.data()` 将这个完整的条目发送到 `stdout`。

这样，`stdout` 将包含测试所期望的 `write_file` 字符串，从而修复测试。

### 标签
#intent/fix #flow/ready #priority/high #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/testing #task/object/cli-output #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修正 `run` 和 `axon` 命令的 `list-acts` 输出逻辑

我将修改 `run.py` 和 `axon.py` 中处理 `--list-acts` 选项的循环，以确保所有列表内容都定向到 `stdout`。

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/run.py
~~~~~
~~~~~python.old
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                bus.info("run.listActs.ui.actItem", name=name)
                bus.data(f"{indented_doc}\n")
~~~~~
~~~~~python.new
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("run.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/axon.py
~~~~~
~~~~~python.old
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                bus.info("axon.listActs.ui.actItem", name=name)
                bus.data(f"{indented_doc}\n")
~~~~~
~~~~~python.new
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("axon.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
~~~~~

### 下一步建议
现在测试应该可以通过了。然而，`--list-acts` 的输出中仍然显示 `暂无说明`。为了让这个功能真正有用，下一步我建议为 `pyquipu-runtime` 中的所有核心 `act` 函数添加详细的 Python docstrings。这将极大地提升开发者体验。
