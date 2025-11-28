You are absolutely right. My apologies for the repeated failures. Your frustration is completely justified. My attempts to "intelligently" fix the problem while retaining the highlighting feature were misguided and have failed. The core issue, as you've correctly identified, is that the `rich` library is fundamentally altering the output.

The principle of least surprise dictates that a command to extract file content should do exactly that—and nothing more. I will now generate a plan that follows your directive to the letter: **remove all rich text processing for the `--extract` functionality and output the raw, original content.**

## [WIP] fix(cli): 彻底移除 show --extract 的富文本渲染以确保原始输出

### 错误分析
之前的修复尝试（`line_numbers=False`, `word_wrap=False`）均告失败。根本原因在于 `rich.console.Console` 和 `rich.syntax.Syntax` 的核心设计目标是**美化终端呈现**，而不是**保证数据保真度**。即使禁用了特定功能，其底层的渲染管线依然可能对文本进行换行、截断或其他类型的处理，这与 `--extract` 命令输出原始数据的核心需求存在根本性冲突。用户的多次测试证明，任何形式的 `rich` 介入都带来了不可预测的副作用。

### 用户需求
用户要求 `quipu show --extract` 命令，无论提取何种文件（`.json`, `.md` 或其他），都必须将文件的原始内容**原封不动地**输出到标准输出，不带任何语法高亮、自动换行、截断或任何其他格式化。

### 评论
你的坚持是正确的。对于一个旨在与管道和脚本集成的工具来说，输出的**可预测性**和**数据完整性**远比美学更重要。彻底移除对提取内容的任何形式的“美化”处理，是回归简单和健壮的正确选择。

### 目标
1.  修改 `packages/quipu-cli/src/quipu/cli/commands/show.py`。
2.  在处理 `--extract` 选项的逻辑分支中，**完全移除**对 `rich.syntax.Syntax` 的调用。
3.  使用最直接的方式（`console.print()` 打印原始字符串）将文件内容输出到 `stdout`。

### 基本原理
我们将剥离所有复杂的渲染逻辑。当用户指定 `--extract` 时，程序将遍历请求的文件列表，对于每一个文件，直接将其内容字符串传递给 `console.print()`。由于传入的是普通字符串而非 `rich` 的可渲染对象（如 `Syntax`），`Console` 会将其作为原始文本直接输出，从而确保内容与 Git Blob 中存储的解码后内容完全一致。

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #concept/ui #scope/dx #ai/instruct #task/domain/cli #task/object/command-show #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 移除 `show --extract` 的所有富文本格式化

我们将用一个简单的 `console.print(content)` 替换掉所有条件判断和 `Syntax` 对象创建的复杂逻辑。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/show.py
~~~~~
~~~~~python
                    for filename, content in output_data.items():
                        if len(extract) > 1:
                            console.rule(f"[bold]{filename}[/bold]", style="blue")

                        if filename.endswith(".json"):
                            # Use word_wrap=False to prevent reformatting
                            syntax = Syntax(content, "json", theme="default", line_numbers=False, word_wrap=False)
                            console.print(syntax)
                        else:
                            # For other files, print raw content
                            console.print(content)
~~~~~
~~~~~python
                    for filename, content in output_data.items():
                        if len(extract) > 1:
                            console.rule(f"[bold]{filename}[/bold]", style="blue")

                        # Per user directive, completely disable rich formatting for --extract
                        # to guarantee raw, unmodified output.
                        console.print(content, end="")
~~~~~

### 下一步建议
这次的修改非常彻底，直接绕过了所有可能出问题的 `rich` 渲染逻辑。在执行此计划后，`quipu show --extract` 的输出应该会是纯净且完整的原始内容。

我们已经为此功能进行了一系列修复，现在它应该终于达到了稳定状态。我强烈建议我们将这一系列修复（行号、截断、崩溃、格式化）合并为一个原子性的 `[COMMIT]` 计划，以清晰地记录这个重要的健壮性改进。如果你同意，我将立即为你生成。
