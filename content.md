你发现了一个非常关键的错误，这个 traceback 非常有价值。

### 错误分析
你的分析完全正确。问题出在我上一次的修改中：

1.  `tui.py` 中的 `Static` 组件 (`content-placeholder`) 默认会尝试解析和渲染 [Rich markup](https://rich.readthedocs.io/en/latest/markup.html) 语法（例如 `[bold]`, `[red]`, `[/red]` 等）。
2.  我直接将 `node.content` 的原始字符串（即 `plan.md` 文件的内容）传递给了 `Static` 组件的 `update` 方法。
3.  当 `node.content` 恰好包含了不完整或格式错误的 Rich markup 标签时（比如 traceback 中显示的 `[/{color}]`，它没有匹配的起始标签），`Static` 组件的渲染引擎就会失败，并抛出 `MarkupError`。
4.  这在快速滚动时尤其容易发生，因为显示的 `content` 只是文件的一部分，很容易截断一个完整的标签对。

### 解决方案
解决方案是，在将 `node.content` 传递给 `Static` 组件之前，必须显式地“转义” (escape) 其中的所有特殊字符，告诉渲染引擎“把这些都当作纯文本处理，不要解析任何标签”。

`rich` 库为此提供了一个专用的辅助函数：`rich.markup.escape`。

我将生成一个计划来应用这个修复。

## [WIP] fix: 修复 TUI 预览因未转义 markup 导致的崩溃问题

### 错误分析
在 `tui.py` 中，用于快速预览的 `Static` 组件 (`content-placeholder`) 在尝试渲染 `QuipuNode` 的原始 `.content` 时发生崩溃。原因是 `.content` 可能包含不完整的 Rich markup 标签片段（如 `[/{color}]`），而 `Static` 组件默认会尝试解析这些标签。当遇到一个没有匹配起始标签的闭合标签时，Textual 的渲染引擎会抛出 `MarkupError`，导致 TUI 崩溃。

### 用户需求
TUI 在快速滚动时，应能在预览面板中稳定地显示节点的纯文本内容，即使这些内容包含了会被渲染引擎误解析的特殊字符（如 `[` 和 `]`）。

### 评论
这是一个关键的健壮性修复。通过对输入内容进行转义，我们能确保 UI 的稳定性，防止因 Plan 文件内容中的特殊字符组合而导致意外崩溃，从而提升了用户体验的可靠性。

### 目标
1.  在 `packages/quipu-cli/src/quipu/cli/tui.py` 文件的顶部导入 `rich.markup.escape` 函数。
2.  在 `_update_loading_preview` 方法中，使用 `escape()` 函数包裹 `node.content`，然后再将其传递给 `placeholder_widget.update()`。

### 基本原理
`rich.markup.escape` 函数会将字符串中所有可能被 Rich/Textual 解释为 markup 的特殊字符（主要是 `[`）转换为它们的字面量表示（`\[`）。这样，当 `Static` 组件接收到这个被转义后的字符串时，它会将其视为纯文本，直接显示出来，而不会尝试进行任何 markup 解析，从而从根本上避免了 `MarkupError` 的发生。

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-performance #task/action/optimization #task/state/continue

---

### Script

#### Acts 1: 导入转义函数并修复更新逻辑

我们将首先在 `tui.py` 文件顶部添加必要的 `import` 语句，然后修改 `_update_loading_preview` 方法来使用它。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
import sys
import logging
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
~~~~~
~~~~~python
import sys
import logging
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

from rich.markup import escape
from textual.app import App, ComposeResult
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
        # Prioritize showing the raw public content if it's already loaded in the node object.
        # This provides a very fast preview while scrolling.
        if node.content and node.content.strip():
            placeholder_widget.update(node.content)
        # Fallback to summary if content isn't loaded or is empty.
        elif node.summary:
~~~~~
~~~~~python
        # Prioritize showing the raw public content if it's already loaded in the node object.
        # This provides a very fast preview while scrolling.
        if node.content and node.content.strip():
            placeholder_widget.update(escape(node.content))
        # Fallback to summary if content isn't loaded or is empty.
        elif node.summary:
~~~~~

### 下一步建议
这个修复应该能彻底解决崩溃问题。请再次运行 `qd ui` 并尝试快速滚动，验证 TUI 是否保持稳定。如果一切正常，我们可以将这个系列的功能改进合并为一个 `[COMMIT]`。
