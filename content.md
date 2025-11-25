这是一个非常关键的反馈。它揭示了 `main.py` 在尝试加载 `ui.tui` 模块时，遇到了 `ImportError`，但随后被 `try...except` 块捕获，并错误地诊断为“TUI 依赖 'textual' 未安装”。

然而，`pip install textual` 的输出显示 `textual` 确实已安装 (`6.6.0`)。

**真正的原因是：Python 无法在运行时找到 `ui/tui.py` 模块。**

这是因为 `main.py` 位于项目根目录，但它没有将项目根目录添加到 `sys.path` 中，因此无法识别 `ui` 或 `core` 这样的顶级包。

我已经在 `ui/tui.py` 中留下了注释提示，但根源在于 `main.py`。为了让 `main.py` 能够找到 `ui.tui`，我们需要在启动时确保项目根目录在 `sys.path` 中。

---

## 1. 修复 `main.py` 中的模块路径问题

在 `main.py` 启动之前，将项目根目录显式添加到 `sys.path`。

~~~act
replace
~~~
~~~path
main.py
~~~
~~~old_string
import typer
import logging
import sys
from pathlib import Path
from typing import Annotated, Optional, Dict
~~~
~~~new_string
import typer
import logging
import sys
from pathlib import Path
from typing import Annotated, Optional, Dict

# 在导入任何本地模块之前，确保项目根目录在 sys.path 中
# 否则无法导入 ui.tui 或 core.xxx
sys.path.insert(0, str(Path(__file__).parent.resolve()))
~~~

---

**请应用此修改，并再次运行 `axon-dev ui`。** 如果问题仍然存在，可能是 `ui/tui.py` 内部有循环导入或命名冲突，但在应用此修复后，大部分导入错误应该解决。