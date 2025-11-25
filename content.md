# feat: 为 TUI 添加 j/k 导航键

## 用户需求
用户希望在 TUI 界面中，除了使用上下方向键外，也能够使用 `j` 和 `k` 键来上下移动光标，以符合 Vim 等工具的用户习惯。

## 评论
这是一个常见的 TUI 增强需求，可以显著提升习惯使用 Vim 键位用户的操作效率。实现起来非常简单，只需要在 `tui.py` 中添加两个按键绑定即可。

## 目标
*   在 `QuipuUiApp` 的按键绑定中，将 `j` 键映射到 `cursor_down` 动作。
*   在 `QuipuUiApp` 的按键绑定中，将 `k` 键映射到 `cursor_up` 动作。
*   这些新的绑定不应显示在 Footer 中，以保持界面简洁。

## 基本原理
Textual 框架通过 `BINDINGS` 类属性来定义按键与动作 (action) 之间的映射。我们只需要向这个列表中添加新的 `Binding` 对象，将 `j` 和 `k` 键分别关联到 Textual `DataTable` 小部件内置的 `cursor_down` 和 `cursor_up` 动作即可。设置 `show=False` 可以防止它们出现在应用的页脚提示中。

## 标签
 #feat #tui #ux

---

## Script

### Act 1: 更新 TUI 按键绑定

将 `j` 和 `k` 键添加到 `QuipuUiApp` 的 `BINDINGS` 列表中，分别用于下移和上移光标。

~~~~~act
replace
~~~~~

~~~~~path
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~

~~~~~python
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("h", "toggle_hidden", "显隐非关联分支"),
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
    ]
~~~~~

~~~~~python
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("h", "toggle_hidden", "显隐非关联分支"),
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
        Binding("k", "cursor_up", "上移", show=False),
        Binding("j", "cursor_down", "下移", show=False),
    ]
~~~~~