# fix: 修复内存测试后端未实现 find_nodes 接口导致的 TypeError

## 用户需求
在修复了上一个导入错误后，再次运行 `pytest`，大部分测试通过了，但 `tests/test_engine_memory.py` 中的所有测试都失败了，并抛出 `TypeError: Can't instantiate abstract class InMemoryHistoryManager without an implementation for abstract method 'find_nodes'`。

这是因为我们向 `HistoryReader` 抽象基类添加了 `find_nodes` 方法，但用于测试的内存模拟实现 `InMemoryHistoryManager`（位于 `tests/helpers.py`）没有相应地更新，导致它不再满足接口契约。

## 评论
这个错误是接口驱动开发中的一个典型且健康的信号。它表明我们的抽象层正在按预期工作，强制所有实现（包括测试替身）保持一致。修复这个问题只需要在我们的测试辅助类中补全缺失的方法实现即可。

## 目标
1.  在 `tests/helpers.py` 文件的 `InMemoryHistoryManager` 类中，实现 `find_nodes` 方法。
2.  该方法的实现将模仿 `GitObjectHistoryReader` 中的内存过滤逻辑，以确保其行为与非数据库后端一致。
3.  修复后，所有测试用例应能成功通过。

## 基本原理
当一个类继承自一个包含抽象方法 (`@abstractmethod`) 的抽象基类 (ABC) 时，该子类必须实现所有这些抽象方法，否则在实例化时就会抛出 `TypeError`。我们的 `InMemoryHistoryManager` 同时继承了 `HistoryReader` 和 `HistoryWriter`，因此必须实现 `find_nodes`。

我们将添加一个内存过滤版本的 `find_nodes`，它会加载所有内存中的节点，然后依次应用 `node_type` 和 `summary_regex` 过滤器，最后排序并返回结果。

## 标签
#intent/fix #flow/ready #priority/critical
#comp/tests #scope/dx
#ai/instruct
#task/domain/storage #task/object/sqlite-backend #task/action/integration
#task/state/continue #task/status/active

---

## Script

### Acts 1: 在测试辅助类中实现 `find_nodes`

我们将在 `tests/helpers.py` 中为 `InMemoryHistoryManager` 类添加 `find_nodes` 方法的实现，并补充必要的 `re` 模块导入。

~~~~~act
replace tests/helpers.py
~~~~~
~~~~~python
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader, HistoryWriter
~~~~~
~~~~~python
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader, HistoryWriter
~~~~~

~~~~~act
replace tests/helpers.py
~~~~~
~~~~~python
        if input_tree in self.db.nodes:
            parent_node = self.db.nodes[input_tree]
            node.parent = parent_node
            parent_node.children.append(node)

        self.db.nodes[output_tree] = node
        return node
~~~~~
~~~~~python
        if input_tree in self.db.nodes:
            parent_node = self.db.nodes[input_tree]
            node.parent = parent_node
            parent_node.children.append(node)

        self.db.nodes[output_tree] = node
        return node

    def find_nodes(
        self,
        summary_regex: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[QuipuNode]:
        """
        内存后端的节点查找实现，通过在内存中过滤所有节点来工作。
        """
        candidates = self.load_all_nodes()

        if summary_regex:
            try:
                pattern = re.compile(summary_regex, re.IGNORECASE)
                candidates = [node for node in candidates if pattern.search(node.summary)]
            except re.error:
                return []  # 在测试中，无效的正则表达式直接返回空列表

        if node_type:
            candidates = [node for node in candidates if node.node_type == node_type]

        # 按时间戳降序排序
        candidates.sort(key=lambda n: n.timestamp, reverse=True)

        return candidates[:limit]
~~~~~
