## [WIP] fix: 修复 Integration 测试中的 NameError 并启动引擎层净化 (第三阶段)

### 用户需求
1.  **修复错误**: `tests/integration/test_cli_workflow.py` 中使用了 `ANY` 但未导入，导致 `NameError`。
2.  **执行第三阶段**: 净化引擎层测试，移除对应用层 (`run_quipu`) 的不当依赖。

### 目标
1.  在 `tests/integration/test_cli_workflow.py` 中导入 `ANY`。
2.  重构 `tests/engine/sqlite/test_writer.py`，使用 `Engine` API 替代 `run_quipu`。
3.  将 `tests/integration/test_idempotent_node.py` 迁移至 `tests/engine/test_deduplication.py` 并重写。

### 基本原理
测试代码必须是自包含且合法的 Python 代码。`ANY` 是 `unittest.mock` 的一部分，必须显式导入。
引擎层的单元测试不应依赖整个应用栈的启动（`run_quipu`），这违反了测试分层原则。通过直接调用 `Writer` 或 `Engine` 的方法，我们可以更精确、更快速地测试底层逻辑。

### 标签
#intent/fix #intent/refine #flow/ready #priority/high #comp/tests #comp/engine #ai/instruct #task/domain/testing #task/object/test-suite #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修复 `test_cli_workflow.py` 的导入错误

添加缺失的 `ANY` 导入。

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
import logging

import pytest
from pyquipu.application.controller import run_quipu
~~~~~
~~~~~python
import logging
from unittest.mock import ANY

import pytest
from pyquipu.application.controller import run_quipu
~~~~~

#### Acts 2: 重构 `tests/engine/sqlite/test_writer.py`

这个测试当前使用 `run_quipu` 来生成数据，这是“杀鸡用牛刀”。我们将改用 `SQLiteHistoryWriter` 直接写入数据。我们需要模拟 GitDB 的状态来配合 Writer。

~~~~~act
read_file tests/engine/sqlite/test_writer.py
~~~~~

#### Acts 3: 迁移 `test_idempotent_node.py`

读取原文件内容，以便在迁移时参考。

~~~~~act
read_file tests/integration/test_idempotent_node.py
~~~~~

### 下一步建议
读取文件后，我将立即生成重构后的测试代码。重构重点是：
1.  在 `test_writer.py` 中，手动创建 Git Tree Hash，然后调用 `sqlite_writer.create_node`。
2.  在 `test_deduplication.py` 中，使用 `engine.create_plan_node` 并验证 `input_tree == output_tree` 的情况。
