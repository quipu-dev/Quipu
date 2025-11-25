由于您提供了精确的 `ImportError`，我们现在可以确定问题是 `textual` 的 API 结构版本差异。

错误信息 `cannot import name 'Cell' from 'textual.widgets.data_table'` 表明在您当前的 `textual` 版本中，`Cell` 类没有被导出在这个路径下。通常，`textual` 会将常用组件导出到顶层 `textual.widgets` 包中。

我们将修改 `ui/tui.py`，尝试从更通用的路径导入 `Cell`。

## 1. 修复 `ui/tui.py` 中的 `Cell` 导入路径

我将替换 `ui/tui.py` 开头的导入块，将 `Cell` 和 `DataTable` 一起从 `textual.widgets` 导入。同时清理掉未使用的 `Static` 导入。

~~~act
replace
~~~
~~~path
ui/tui.py
~~~
~~~old_string
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.app import ScreenStackError
from textual.binding import Binding
from textual.message import Message
from textual.widgets.data_table import Cell
~~~
~~~new_string
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Cell # 尝试从顶层导入 Cell
from textual.app import ScreenStackError
from textual.binding import Binding
from textual.message import Message
~~~

请应用此修改并重新运行 `axon ui`。如果这次能够成功启动 UI，我们将继续实现您最初的垂直时间轴和分支渲染要求。