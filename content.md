## [WIP] refactor: 修复测试套件的导入路径与函数调用

### 用户需求
在重构核心逻辑并移动到 `pyquipu-application` 包后，集成测试、引擎测试和运行时测试因引用了旧的 `pyquipu.cli.*` 路径而崩溃。此外，`run_quipu` 函数签名的变更（新增 `confirmation_handler` 参数）也需要同步更新到测试调用中。

### 目标
1.  将所有测试文件中对 `pyquipu.cli.controller`, `pyquipu.cli.utils`, `pyquipu.cli.factory` 的引用更新为 `pyquipu.application.*`。
2.  更新所有 `run_quipu` 的调用，传入一个自动确认的 `confirmation_handler`。

### 基本原理
测试必须反映代码库的真实架构。通过修正导入路径和适配新的 API 签名，我们将恢复 CI/CD 的绿色状态，确保重构没有破坏核心功能。

### 标签
#intent/refine #flow/ready #priority/high #comp/tests #scope/core #ai/refine #task/domain/testing #task/object/test-suite #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 修复 `tests/engine/sqlite/test_writer.py`

~~~~~act
patch_file tests/engine/sqlite/test_writer.py
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest
from pyquipu.cli.controller import run_quipu
from pyquipu.engine.sqlite_db import DatabaseManager

PLAN_A = """
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest
from pyquipu.application.controller import run_quipu
from pyquipu.engine.sqlite_db import DatabaseManager

PLAN_A = """
~~~~~

~~~~~act
patch_file tests/engine/sqlite/test_writer.py
~~~~~
~~~~~python
        # --- Action 1: Create first node ---
        result_a = run_quipu(PLAN_A, work_dir=sqlite_workspace, yolo=True)
        assert result_a.success, f"run_quipu failed on Plan A: {result_a.message}"

        # Get the state after the first run
~~~~~
~~~~~python
        # --- Action 1: Create first node ---
        result_a = run_quipu(
            PLAN_A, work_dir=sqlite_workspace, yolo=True, confirmation_handler=lambda *a: True
        )
        assert result_a.success, f"run_quipu failed on Plan A: {result_a.message}"

        # Get the state after the first run
~~~~~

~~~~~act
patch_file tests/engine/sqlite/test_writer.py
~~~~~
~~~~~python
        commit_hash_a = heads_after_a.pop()

        # --- Action 2: Create second node, which should be a child of the first ---
        result_b = run_quipu(PLAN_B, work_dir=sqlite_workspace, yolo=True)
        assert result_b.success, f"run_quipu failed on Plan B: {result_b.message}"

        # Get the state after the second run and find the new commit
~~~~~
~~~~~python
        commit_hash_a = heads_after_a.pop()

        # --- Action 2: Create second node, which should be a child of the first ---
        result_b = run_quipu(
            PLAN_B, work_dir=sqlite_workspace, yolo=True, confirmation_handler=lambda *a: True
        )
        assert result_b.success, f"run_quipu failed on Plan B: {result_b.message}"

        # Get the state after the second run and find the new commit
~~~~~

#### Acts 2: 修复 `tests/engine/test_head_tracking.py`

~~~~~act
patch_file tests/engine/test_head_tracking.py
~~~~~
~~~~~python
import pytest
from pyquipu.cli.utils import find_git_repository_root
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine
~~~~~
~~~~~python
import pytest
from pyquipu.application.utils import find_git_repository_root
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine
~~~~~

#### Acts 3: 修复 `tests/integration/test_cli_workflow.py`

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
import logging

import pytest
from pyquipu.cli.controller import run_quipu
from pyquipu.cli.main import app
from pyquipu.interfaces.exceptions import ExecutionError
from typer.testing import CliRunner
~~~~~
~~~~~python
import logging

import pytest
from pyquipu.application.controller import run_quipu
from pyquipu.cli.main import app
from pyquipu.interfaces.exceptions import ExecutionError
from typer.testing import CliRunner
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
class TestController:
    def test_run_quipu_success(self, workspace):
        """测试正常执行流程"""
        from pyquipu.cli.factory import create_engine

        plan = """
```act
~~~~~
~~~~~python
class TestController:
    def test_run_quipu_success(self, workspace):
        """测试正常执行流程"""
        from pyquipu.application.factory import create_engine

        plan = """
```act
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
```content
Hello Quipu
```
"""
        result = run_quipu(content=plan, work_dir=workspace, yolo=True)

        assert result.success is True
        assert result.exit_code == 0
~~~~~
~~~~~python
```content
Hello Quipu
```
"""
        result = run_quipu(
            content=plan, work_dir=workspace, yolo=True, confirmation_handler=lambda *a: True
        )

        assert result.success is True
        assert result.exit_code == 0
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
```content
boo
```
"""
        result = run_quipu(content=plan, work_dir=workspace, yolo=True)

        assert result.success is False
        assert result.exit_code == 1
~~~~~
~~~~~python
```content
boo
```
"""
        result = run_quipu(
            content=plan, work_dir=workspace, yolo=True, confirmation_handler=lambda *a: True
        )

        assert result.success is False
        assert result.exit_code == 1
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
    def test_run_quipu_empty_plan(self, workspace):
        """测试无有效指令"""
        plan = "Just some text, no acts."

        result = run_quipu(content=plan, work_dir=workspace, yolo=True)

        assert result.success is True  # No failure, just nothing to do
        assert result.exit_code == 0
~~~~~
~~~~~python
    def test_run_quipu_empty_plan(self, workspace):
        """测试无有效指令"""
        plan = "Just some text, no acts."

        result = run_quipu(
            content=plan, work_dir=workspace, yolo=True, confirmation_handler=lambda *a: True
        )

        assert result.success is True  # No failure, just nothing to do
        assert result.exit_code == 0
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
        # State A: Create a.txt
        plan_a = "```act\nwrite_file a.txt\n```\n```content\nState A\n```"
        run_quipu(content=plan_a, work_dir=workspace, yolo=True)

        engine_after_a = create_engine(workspace)
        nodes_after_a = sorted(engine_after_a.reader.load_all_nodes(), key=lambda n: n.timestamp)
~~~~~
~~~~~python
        # State A: Create a.txt
        plan_a = "```act\nwrite_file a.txt\n```\n```content\nState A\n```"
        run_quipu(
            content=plan_a, work_dir=workspace, yolo=True, confirmation_handler=lambda *a: True
        )

        engine_after_a = create_engine(workspace)
        nodes_after_a = sorted(engine_after_a.reader.load_all_nodes(), key=lambda n: n.timestamp)
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
        # Manually create State B by removing a.txt and adding b.txt
        (workspace / "a.txt").unlink()
        plan_b = "```act\nwrite_file b.txt\n```\n```content\nState B\n```"
        run_quipu(content=plan_b, work_dir=workspace, yolo=True)

        engine_after_b = create_engine(workspace)
        nodes_after_b = sorted(engine_after_b.reader.load_all_nodes(), key=lambda n: n.timestamp)
~~~~~
~~~~~python
        # Manually create State B by removing a.txt and adding b.txt
        (workspace / "a.txt").unlink()
        plan_b = "```act\nwrite_file b.txt\n```\n```content\nState B\n```"
        run_quipu(
            content=plan_b, work_dir=workspace, yolo=True, confirmation_handler=lambda *a: True
        )

        engine_after_b = create_engine(workspace)
        nodes_after_b = sorted(engine_after_b.reader.load_all_nodes(), key=lambda n: n.timestamp)
~~~~~

~~~~~act
patch_file tests/integration/test_cli_workflow.py
~~~~~
~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from pyquipu.cli.factory import create_engine

        workspace, hash_a, hash_b = populated_workspace

        # Make the workspace dirty
~~~~~
~~~~~python
    def test_cli_checkout_with_safety_capture(self, populated_workspace):
        """Test that a dirty state is captured before checkout."""
        from pyquipu.application.factory import create_engine

        workspace, hash_a, hash_b = populated_workspace

        # Make the workspace dirty
~~~~~

#### Acts 4: 修复 `tests/integration/test_idempotent_node.py`

~~~~~act
patch_file tests/integration/test_idempotent_node.py
~~~~~
~~~~~python
from pathlib import Path

from pyquipu.cli.controller import run_quipu


class TestIdempotentNode:
    def test_idempotent_plan_creation(self, tmp_path: Path):
~~~~~
~~~~~python
from pathlib import Path

from pyquipu.application.controller import run_quipu


class TestIdempotentNode:
    def test_idempotent_plan_creation(self, tmp_path: Path):
~~~~~

~~~~~act
patch_file tests/integration/test_idempotent_node.py
~~~~~
~~~~~python
        # 2. 先执行一个会产生变更的操作 (State A)
        plan_1 = "```act\nwrite_file a.txt\n```\n```content\nA\n```"
        run_quipu(plan_1, workspace, yolo=True)

        # 使用正确的 Engine 设置来验证
        from pyquipu.cli.factory import create_engine

        engine1 = create_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
~~~~~
~~~~~python
        # 2. 先执行一个会产生变更的操作 (State A)
        plan_1 = "```act\nwrite_file a.txt\n```\n```content\nA\n```"
        run_quipu(plan_1, workspace, yolo=True, confirmation_handler=lambda *a: True)

        # 使用正确的 Engine 设置来验证
        from pyquipu.application.factory import create_engine

        engine1 = create_engine(workspace)
        nodes1 = engine1.reader.load_all_nodes()
~~~~~

~~~~~act
patch_file tests/integration/test_idempotent_node.py
~~~~~
~~~~~python
        # 3. 执行一个无变更的操作 (State A -> State A)
        plan_2 = "```act\nread_file a.txt\n```"
        result = run_quipu(plan_2, workspace, yolo=True)

        assert result.success is True

        # 4. 验证是否生成了新节点
        engine2 = create_engine(workspace)
~~~~~
~~~~~python
        # 3. 执行一个无变更的操作 (State A -> State A)
        plan_2 = "```act\nread_file a.txt\n```"
        result = run_quipu(plan_2, workspace, yolo=True, confirmation_handler=lambda *a: True)

        assert result.success is True

        # 4. 验证是否生成了新节点
        engine2 = create_engine(workspace)
~~~~~

#### Acts 5: 修复 `tests/integration/test_workspace_invariance.py`

~~~~~act
patch_file tests/integration/test_workspace_invariance.py
~~~~~
~~~~~python
import subprocess

import pytest
from pyquipu.cli.controller import run_quipu


@pytest.fixture
def project_with_subdir(tmp_path):
~~~~~
~~~~~python
import subprocess

import pytest
from pyquipu.application.controller import run_quipu


@pytest.fixture
def project_with_subdir(tmp_path):
~~~~~

~~~~~act
patch_file tests/integration/test_workspace_invariance.py
~~~~~
~~~~~python
        plan_content = (project_root / "plan.md").read_text("utf-8")

        result = run_quipu(
            content=plan_content,
            work_dir=subdir,  # <--- 从子目录运行
            yolo=True,
        )

        # 1. 验证操作的正确性
~~~~~
~~~~~python
        plan_content = (project_root / "plan.md").read_text("utf-8")

        result = run_quipu(
            content=plan_content,
            work_dir=subdir,  # <--- 从子目录运行
            yolo=True,
            confirmation_handler=lambda *a: True,
        )

        # 1. 验证操作的正确性
~~~~~

~~~~~act
patch_file tests/integration/test_workspace_invariance.py
~~~~~
~~~~~python
        assert expected_file.read_text("utf-8") == "Success from subdir"

        # 2. 验证 Engine 状态记录的正确性 (后端无关)
        from pyquipu.cli.factory import create_engine

        engine = create_engine(project_root)
        nodes = engine.reader.load_all_nodes()
~~~~~
~~~~~python
        assert expected_file.read_text("utf-8") == "Success from subdir"

        # 2. 验证 Engine 状态记录的正确性 (后端无关)
        from pyquipu.application.factory import create_engine

        engine = create_engine(project_root)
        nodes = engine.reader.load_all_nodes()
~~~~~

#### Acts 6: 修复 `tests/integration/test_workspace_isolation.py`

~~~~~act
patch_file tests/integration/test_workspace_isolation.py
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest
from pyquipu.cli.controller import run_quipu


@pytest.fixture
def nested_git_project(tmp_path: Path):
~~~~~
~~~~~python
import subprocess
from pathlib import Path

import pytest
from pyquipu.application.controller import run_quipu


@pytest.fixture
def nested_git_project(tmp_path: Path):
~~~~~

~~~~~act
patch_file tests/integration/test_workspace_isolation.py
~~~~~
~~~~~python
```content
isolation test
```
"""

        # 关键：调用 run_quipu，将 work_dir 设置为没有 .git 的子目录
        result = run_quipu(content=plan_content, work_dir=work_dir, yolo=True)

        # --- Assertions ---
~~~~~
~~~~~python
```content
isolation test
```
"""

        # 关键：调用 run_quipu，将 work_dir 设置为没有 .git 的子目录
        result = run_quipu(
            content=plan_content, work_dir=work_dir, yolo=True, confirmation_handler=lambda *a: True
        )

        # --- Assertions ---
~~~~~

#### Acts 7: 修复 `tests/runtime/test_plugin_loader.py`

~~~~~act
patch_file tests/runtime/test_plugin_loader.py
~~~~~
~~~~~python
import sys

import pytest
from pyquipu.cli.utils import find_git_repository_root
from pyquipu.runtime.executor import Executor
from pyquipu.runtime.plugin_loader import load_plugins
~~~~~
~~~~~python
import sys

import pytest
from pyquipu.application.utils import find_git_repository_root
from pyquipu.runtime.executor import Executor
from pyquipu.runtime.plugin_loader import load_plugins
~~~~~

### 下一步建议
现在所有测试引用都已修正。请运行完整的测试套件（`pytest`），确保没有任何回归。如果测试全部通过，说明我们的 Application 包重构是成功的且稳定的。
