You are absolutely right. My apologies. That is a classic, embarrassing mistake on my part. The `NameError` traceback is definitive proof: I introduced the `List` type hint in the function signature but neglected to import it from the `typing` module.

Thank you for catching that. I will generate a plan to fix this immediately.

## [WIP] fix(cli): 修复 show 命令因缺少 List 类型导入而崩溃的问题

### 错误分析
在上一轮重构 `show` 命令以支持多个 `--extract` 参数时，我将 `extract` 参数的类型注解修改为 `Optional[List[str]]`。然而，我忘记在 `packages/quipu-cli/src/quipu/cli/commands/show.py` 文件的顶部添加相应的 `from typing import List` 导入语句。这导致 Python 解释器在解析该函数签名时无法找到 `List` 的定义，从而抛出 `NameError`，导致命令在执行前就崩溃了。

### 用户需求
修复 `show.py` 文件中的 `NameError`，确保 `quipu show` 命令能够正常运行。

### 评论
这是一个简单的编码疏忽，但它完全阻断了命令的执行，属于高优先级修复。感谢你的精确报错，这使得定位和修复问题变得非常直接。

### 目标
1.  在 `packages/quipu-cli/src/quipu/cli/commands/show.py` 的文件头部，将 `List` 添加到 `typing` 模块的导入列表中。

### 基本原理
通过在脚本顶部添加 `from typing import List`，我们为 Python 解释器提供了 `List` 类型注解的定义，从而解决 `NameError`。

### 标签
#intent/fix #flow/ready #priority/critical #comp/cli #scope/dx #ai/instruct #task/domain/cli #task/object/command-show #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 添加缺失的类型导入

我们将修改 `show.py` 文件顶部的导入语句，以包含 `List`。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/commands/show.py
~~~~~
~~~~~python
import json
import logging
from pathlib import Path
from typing import Annotated, Optional, Dict

import typer
~~~~~
~~~~~python
import json
import logging
from pathlib import Path
from typing import Annotated, Optional, Dict, List

import typer
~~~~~

### 下一步建议
在应用这个补丁后，`show` 命令应该就能正常工作了。

我们现在已经连续进行了三次修复 (`行号` -> `截断` -> `崩溃`)，它们共同完善了 `show` 命令的功能。现在是时候将这些工作成果合并到一个原子性的提交中了。

如果你同意，我将为你生成一个 `[COMMIT]` 计划，总结这三次修复，并将其正式记录到版本历史中。
