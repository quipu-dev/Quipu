我们现在进入重构路线图的第四阶段：**统一与收敛 (Unification)**。

在这一阶段，我们将把散落在 `bus`、`cli` 和 `runtime` 包中的 `Renderer` 和 `Parser` 协议提取到 `spec` 包中，确立其作为整个 Quipu 生态系统“单一事实来源” (SSoT) 的地位。

## [WIP] refactor: 统一协议定义，确立 spec 包的 SSoT 地位

### 用户需求

实施架构重构路线图第四阶段：
1.  在 `spec` 包中创建 `messaging` 和 `parser` 协议定义。
2.  重构 `bus`、`cli` 和 `runtime` 以使用这些集中的协议定义，并移除本地的重复定义或 ABC。

### 评论

通过集中协议定义，我们消除了代码库中的冗余，并确保了不同组件之间交互契约的绝对一致性。这不仅使得类型检查更加可靠，也为未来引入新的渲染器或解析器提供了标准化的“插槽”。

### 目标

1.  在 `pyquipu-spec` 中创建 `protocols/messaging.py`，定义 `Renderer` 协议。
2.  在 `pyquipu-spec` 中创建 `protocols/parser.py`，定义 `PlanParser` 协议。
3.  重构 `pyquipu-bus` 和 `pyquipu-cli`，使其使用 `spec` 中的 `Renderer`。
4.  重构 `pyquipu-runtime`，移除 `BaseParser` 抽象基类，改用 `spec` 中的 `PlanParser` 契约。

### 基本原理

*   **收敛一致性**: 目前 `Renderer` 协议在 `bus` 和 `cli` 中各有一份拷贝。虽然它们目前一致，但这种冗余增加了维护成本和潜在的冲突风险。将其收归 `spec` 确保了契约的单一性。
*   **结构化解析契约**: 将解析器的基类转换为 `PlanParser` 协议，并放置在 `spec` 中，明确了“任何能将文本转换为 `Statement` 列表的对象都是有效的解析器”这一核心逻辑。

### 标签

#intent/refine #flow/ready #priority/high #comp/spec #comp/bus #comp/cli #comp/runtime #scope/api #ai/instruct #task/domain/architecture #task/object/unification #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 创建集中的消息和解析协议

首先，在 `spec` 包中建立新的协议层。

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/messaging.py
~~~~~
~~~~~python
from typing import Protocol, runtime_checkable


@runtime_checkable
class Renderer(Protocol):
    """定义消息渲染器的行为契约"""

    def success(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def data(self, data_string: str) -> None: ...
~~~~~

~~~~~act
write_file
packages/pyquipu-spec/src/quipu/spec/protocols/parser.py
~~~~~
~~~~~python
from typing import Protocol, List, runtime_checkable
from .runtime import Statement


@runtime_checkable
class PlanParser(Protocol):
    """定义 Plan 文件解析器的行为契约"""

    def parse(self, text: str) -> List[Statement]: ...
~~~~~

#### Acts 2: 重构 Message Bus

将 `bus` 包中的 `Renderer` 替换为对 `spec` 的引用。

~~~~~act
patch_file
packages/pyquipu-bus/src/quipu/bus/bus.py
~~~~~
~~~~~python.old
import json
import logging
from typing import Any, Dict, Optional, Protocol

from .messages import find_locales_dir
~~~~~
~~~~~python.new
import json
import logging
from typing import Any, Dict, Optional

from quipu.spec.protocols.messaging import Renderer

from .messages import find_locales_dir
~~~~~

~~~~~act
patch_file
packages/pyquipu-bus/src/quipu/bus/bus.py
~~~~~
~~~~~python.old
class Renderer(Protocol):
    def success(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def data(self, data_string: str) -> None: ...
~~~~~
~~~~~python.new
# Renderer protocol is now imported from quipu.spec.protocols.messaging
~~~~~

#### Acts 3: 重构 CLI 渲染器

同样地，重构 CLI 层。

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/rendering.py
~~~~~
~~~~~python.old
from typing import Protocol

import typer


class Renderer(Protocol):
    def success(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...
    def data(self, data_string: str) -> None: ...
~~~~~
~~~~~python.new
import typer
from quipu.spec.protocols.messaging import Renderer
~~~~~

#### Acts 4: 重构 Runtime 解析器

移除 `pyquipu-runtime` 中的 `BaseParser` 抽象基类，转而使用结构化协议。

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from quipu.spec.protocols.runtime import Statement


class BaseParser(ABC):
    @abstractmethod
    def parse(self, text: str) -> List[Statement]:
        pass
~~~~~
~~~~~python.new
import re
from typing import List, Optional

from quipu.spec.protocols.runtime import Statement
# PlanParser protocol is now defined in quipu.spec.protocols.parser
# and implemented implicitly by classes here.
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/src/quipu/runtime/parser.py
~~~~~
~~~~~python.old
class StateBlockParser(BaseParser):
~~~~~
~~~~~python.new
class StateBlockParser:
~~~~~

### 下一步建议

我们已经成功地将重复的协议定义收归 `spec`。这标志着 Quipu 的类型系统核心已经达到了高度的收敛。

接下来，我建议：
1.  再次运行 `pytest` 以验证组件间的链接是否依然正确（尤其是 `bus` 与 `cli` 渲染器的绑定）。
2.  完成后，我们可以进入**阶段五：清理与验证 (Cleanup)**。这包括提取 `QuipuEngine` 协议，以及将 `EMPTY_TREE_HASH` 等全局常量统一迁移到 `spec.constants` 中。
