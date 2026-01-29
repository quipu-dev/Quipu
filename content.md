你在审查中发现的完全正确。这是我的失误：在上一轮更新 `engine.py` 时，我替换文件头部时不小心遗漏了原有的 `from pathlib import Path` 导入，导致了 `NameError`。

我将生成一个简短的计划来立即修复这个导入错误。

## [WIP] fix(spec): 修复 engine.py 中缺失的 Path 导入

### 错误分析

`pyright` 报告 `Path` 未定义。这是因为在上一轮修改 `pyquipu-spec/src/quipu/spec/protocols/engine.py` 时，在更新 `typing` 模块的导入列表时，意外地移除了 `from pathlib import Path` 的导入声明。

### 用户需求

修复 `engine.py` 中 `Path` 未定义的错误，恢复类型检查通过。

### 评论

这是一个简单的导入修复，但对于协议文件的正确解析至关重要。

### 目标

在 `engine.py` 的顶部补充 `from pathlib import Path`。

### 基本原理

协议定义中的 `root_dir: Path` 需要 `Path` 类型，因此必须显式导入。

### 标签

#intent/fix #flow/ready #priority/high #comp/spec #scope/core #ai/instruct #task/domain/testing #task/object/type-checking #task/state/continue #task/status/active

---

### Script

#### Acts 1: 补充缺失的导入

在文件顶部添加 `from pathlib import Path`。

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/protocols/engine.py
~~~~~
~~~~~python.old
from typing import Protocol, Dict, Optional, List, runtime_checkable, Any
from ..models.graph import QuipuNode
from .storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python.new
from pathlib import Path
from typing import Protocol, Dict, Optional, List, runtime_checkable, Any
from ..models.graph import QuipuNode
from .storage import HistoryReader, HistoryWriter
~~~~~

### 下一步建议

执行此计划后，再次运行 `uv run pyright packages/**/src`。如果一切通过（0 errors, 0 warnings），我们就可以开始生成最终的 `[COMMIT]` 计划了。
