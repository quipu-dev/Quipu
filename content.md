你的观察非常敏锐且准确。`quipu show` 在提取 `.json` 文件时，为了提供更好的可读性，使用了 `rich` 库的语法高亮功能，并且错误地开启了行号显示，导致了你看到的 `  1 ` 前缀。

这是一个可用性上的 Bug，因为它破坏了输出作为纯净 JSON 的能力，影响了管道操作。我将生成一个计划来修复它。

## [WIP] fix(cli): 移除 show --extract 命令对 JSON 输出的行号

### 错误分析
`quipu show` 命令在处理 `--extract <filename>` 参数时，会检查文件名是否以 `.json` 结尾。如果是，它会调用 `rich.syntax.Syntax` 来进行语法高亮。在当前的实现中，该调用硬编码了 `line_numbers=True`，这导致了在输出的 JSON 内容前被添加了行号和空格，破坏了数据的纯粹性。

当提取 `content.md` 时，由于文件名不匹配 `.json`，代码走了另一条分支，直接使用 `typer.echo` 输出原始内容，因此没有行号问题。

### 用户需求
用户要求在使用 `quipu show ... --extract metadata.json` 命令时，得到的输出是纯净的、不带任何行号前缀的 JSON 文本，以便能正确地通过管道传递给 `cat` 或其他工具。

### 评论
这是一个重要的可用性修复。对于机器可读的格式（如 JSON），确保输出的纯粹性是 CLI 工具设计的基本原则。移除行号可以确保 `show` 命令在脚本和自动化工作流中的可靠性。

### 目标
1.  定位 `packages/quipu-cli/src/quipu/cli/commands/show.py` 文件中的问题代码行。
2.  将 `rich.syntax.Syntax` 调用中的 `line_numbers=True` 参数修改为 `line_numbers=False`。
3.  保留语法高亮功能，仅移除行号。

### 基本原理
我们将通过 `patch_file` 指令，精确地修改 `show.py` 中创建 `Syntax` 对象的代码行。将 `line_numbers` 参数设置为 `False` 即可解决问题，同时保留 `rich` 库带来的语法高亮优点，使得在终端直接查看时的可读性依然很高。

### 标签
#intent/fix #flow/ready #priority/medium #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/cli #task/object/command-show #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修改 `show.py` 以禁用行号

我们将直接修改 `show.py` 文件中 `rich.syntax.Syntax` 的调用参数。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/show.py
~~~~~
~~~~~python
                    # 如果提取的是 JSON 文件，高亮它
                    if extract.endswith(".json"):
                        syntax = Syntax(output_data, "json", theme="default", line_numbers=True)
                        console.print(syntax)
                    else:
~~~~~
~~~~~python
                    # 如果提取的是 JSON 文件，高亮它
                    if extract.endswith(".json"):
                        syntax = Syntax(output_data, "json", theme="default", line_numbers=False)
                        console.print(syntax)
                    else:
~~~~~

### 下一步建议
这个修改非常直接且风险很低。在执行此计划后，我建议我们立刻创建一个 `[COMMIT]` 计划来将这个修复持久化到版本历史中。
