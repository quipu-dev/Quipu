您是对的，`Cell` 并不是 `textual` 公开 API 的一部分（至少在常用版本中不是）。在 `DataTable` 中添加样式化内容的标准方式是使用 `rich.text.Text` 对象。

此外，您的 `textual` 版本（6.6.0）似乎是一个非常新的或者非标准的版本号（通常 textual 版本号为 0.x.y），但在任何情况下，使用 `rich` 对象是兼容性最好的做法。

这里是修复方案：

1.  **移除** 错误的 `Cell` 导入。
2.  **添加** `rich.text.Text` 导入。
3.  **修改** `add_row` 调用，使用 `Text` 对象来应用样式（我将使用 "bold reverse" 来高亮当前节点，这比依赖 CSS 类更直接且兼容）。

~~~act
replace
~~~
~~~path
ui/tui.py
~~~
~~~old_string
from typing import List, Optional, Dict, Tuple
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Cell # 尝试从顶层导入 Cell
from textual.app import ScreenStackError
from textual.binding import Binding
from textual.message import Message
~~~
~~~new_string
from typing import List, Optional, Dict, Tuple
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from textual.app import ScreenStackError
from textual.binding import Binding
from textual.message import Message
from rich.text import Text
~~~

~~~act
replace
~~~
~~~path
ui/tui.py
~~~
~~~old_string
            # 样式
            style_class = ""
            if node.output_tree == self.current_hash:
                style_class = "current"
                current_node_row_index = i
            
            # 将 AxonNode 实例作为行的用户数据 (UserData) 存储
            row_key = table.add_row(
                time_str,
                type_label,
                hash_str,
                Cell(summary_str, style=style_class),
                key=node.output_tree,
                label=node # 存储整个节点对象
            )
~~~
~~~new_string
            # 样式与内容构建
            if node.output_tree == self.current_hash:
                current_node_row_index = i
                # 使用 Rich Text 进行高亮 (bold reverse 通常能适应各种终端主题)
                summary_cell = Text(summary_str, style="bold reverse")
                # 也可以选择高亮其他列，这里高亮摘要列
            else:
                summary_cell = summary_str
            
            # 将 AxonNode 实例作为行的用户数据 (UserData) 存储
            # DataTable.add_row 接受 *cells, label=..., key=...
            # 注意：Textual 的 add_row 不支持直接传递 label 对象作为参数来存储数据，
            # 但它支持 key。我们需要一个方式来找回 node。
            # 最好的方式是维护一个 key -> node 的映射，或者依赖 key 本身。
            # 之前的代码试图用 label=node，这在 Textual API 中可能不支持存储对象。
            # 我们利用 key=node.output_tree 即可，在 action_checkout_node 中我们已经通过 self.flat_nodes 查找了。
            
            row_key = table.add_row(
                time_str,
                type_label,
                hash_str,
                summary_cell,
                key=node.output_tree
            )
~~~

请应用这两个修改。这样应该能彻底解决导入错误，并实现高亮功能。