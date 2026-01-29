检测到“确定性缺失”违例。由于我在上一步重构中删除了 `BaseParser` 但未同步更新 `get_parser` 函数的类型注解，导致了代码引用失效。

我将生成一个修复计划来纠正这一错误。

## [WIP] fix: 修复 parser.py 中的 BaseParser 引用错误

### 错误分析
在执行“阶段四：统一与收敛”时，我移除了 `pyquipu-runtime/src/quipu/runtime/parser.py` 中的 `BaseParser` 定义。然而，该文件底部的工厂函数 `get_parser` 仍然将 `BaseParser` 作为其返回类型的注解，导致了 `NameError`。

### 用户需求
修正 `parser.py` 中的类型注解，使其指向 `spec` 包中新定义的 `PlanParser` 协议。

### 目标
1.  在 `parser.py` 中导入 `PlanParser`。
2.  更新 `get_parser` 函数的返回类型注解。

### 基本原理
为了保持重构后的一致性，所有原本指向 `BaseParser` 的地方现在都应指向 `quipu.spec.protocols.parser.PlanParser` 协议。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #scope/api #ai/instruct #task/domain/architecture #task/object/parser #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修正 `parser.py` 中的类型导入与注解

我们将导入 `PlanParser` 协议，并更新工厂函数的返回类型。

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
from typing import List, Optional

from quipu.spec.protocols.runtime import Statement
# PlanParser protocol is now defined in quipu.spec.protocols.parser
# and implemented implicitly by classes here.
~~~~~
~~~~~python.new
from typing import List, Optional

from quipu.spec.protocols.runtime import Statement
from quipu.spec.protocols.parser import PlanParser
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
def get_parser(name: str) -> BaseParser:
~~~~~
~~~~~python.new
def get_parser(name: str) -> PlanParser:
~~~~~

### 下一步建议
修复此错误后，建议再次运行测试。如果通过，我们将继续执行阶段四的剩余任务，包括：
1.  在 `spec` 中提取 `QuipuEngine` 协议。
2.  将 `EMPTY_TREE_HASH` 常量迁移到 `spec.constants`。
