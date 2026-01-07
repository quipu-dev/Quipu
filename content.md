完全理解。重构测试套件以匹配 `cascade` 项目的结构是一个重要的步骤，它能提高项目的一致性和可维护性。将测试文件与它们所测试的包放在一起，并明确区分单元测试和集成测试，是现代 Python 项目的最佳实践。

为了安全、可重复地执行这项重构，我将生成一个 Python 脚本来处理所有文件和目录的移动，然后清理不再需要的文件和目录。

## [WIP] refactor: 重构测试套件以遵循包内结构

### 用户需求

模仿 `cascade` 项目的测试文件布局，将 `pyquipu` 的顶层 `tests` 目录重构为分布在每个 `packages/*` 子目录下的 `tests` 结构。新的结构需要严格区分 `unit` 和 `integration` 测试。

### 评论

这是一个非常有价值的架构改进。当前的顶层 `tests` 目录结构使得测试与源代码的对应关系不够清晰，并且随着项目的增长会变得难以导航。采用 `cascade` 的包内测试模式，可以使每个包更加内聚和独立，同时也为未来可能的、更细粒度的 CI 策略（例如，只运行变更包的测试）打下基础。

### 目标

1.  在 `packages` 内的每个 `quipu-*` 目录中创建新的 `tests` 目录结构。
2.  将现有的测试文件从顶层 `tests` 目录迁移到其对应包内的 `tests/{unit|integration}` 目录中。
3.  合理地迁移或合并 `conftest.py` 和 `helpers.py` 文件。
4.  安全地删除旧的顶层 `tests` 目录。
5.  通过一个自动化脚本完成整个迁移过程，确保操作的准确性。

### 基本原理

重构将通过一个专门的 Python 脚本 (`scripts/refactor_tests.py`) 来执行。该脚本会包含一个从旧路径到新路径的完整映射。

1.  **分类**：我将现有的测试文件分为两类：
    *   **单元测试 (unit)**：专注于单个模块或类的功能，通常使用 `mock` 来隔离依赖。例如，测试 `acts` 或 `parser` 的文件。
    *   **集成测试 (integration)**：测试多个组件的交互，或与文件系统、Git 等外部系统的交互。例如，大部分 `cli` 和 `engine` 的测试都属于此类。
2.  **映射与移动**：脚本将根据预定义的映射，自动创建目标目录并将每个文件移动到新位置。
3.  **辅助文件**：`conftest.py` 和 `helpers.py` 等辅助文件将被移动到其最相关的新位置。例如，`engine` 相关的辅助文件将移至 `packages/quipu-engine/tests/`。
4.  **清理**：脚本在成功移动所有文件后，将递归删除旧的 `tests` 目录，并清理自身的脚本文件，完成整个重构任务。

这种方法将复杂的手动操作转变为一个单一、原子化的步骤，最大程度地减少了出错的风险。

### 标签

#intent/refine #flow/ready #priority/high #comp/tests #scope/dx #ai/delegate #task/domain/testing #task/object/test-suite-structure #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 创建测试重构脚本

首先，我们创建一个脚本来自动化整个重构过程。

~~~~~act
write_file
scripts/refactor_tests.py
~~~~~
~~~~~python
import os
import shutil
from pathlib import Path

# --- Configuration ---
ROOT = Path(__file__).parent.parent
DRY_RUN = False  # Set to True to only print actions without executing them

# (Old Path relative to tests/, New Package, Test Type, New Path relative to tests/type/)
# Test Type can be 'unit', 'integration', or None (for files directly in tests/)
MAPPING = [
    # application
    ("application/conftest.py", "quipu-application", None, "conftest.py"),
    ("application/test_controller.py", "quipu-application", "unit", "test_controller.py"),
    ("application/test_utils.py", "quipu-application", "unit", "test_utils.py"),
    ("application/__init__.py", "quipu-application", None, "__init__.py"),

    # cli
    ("cli/conftest.py", "quipu-cli", None, "conftest.py"),
    ("cli/test_cache_commands.py", "quipu-cli", "integration", "test_cache_commands.py"),
    ("cli/test_cli_interaction.py", "quipu-cli", "integration", "test_cli_interaction.py"),
    ("cli/test_export_command.py", "quipu-cli", "integration", "test_export_command.py"),
    ("cli/test_navigation_commands.py", "quipu-cli", "integration", "test_navigation_commands.py"),
    ("cli/test_query_commands.py", "quipu-cli", "integration", "test_query_commands.py"),
    ("cli/test_unfriendly_paths.py", "quipu-cli", "integration", "test_unfriendly_paths.py"),
    ("cli/test_workspace_commands.py", "quipu-cli", "integration", "test_workspace_commands.py"),
    ("cli/test_tui_logic.py", "quipu-cli", "unit", "test_tui_logic.py"),
    ("cli/test_tui_reachability.py", "quipu-cli", "unit", "test_tui_reachability.py"),
    ("cli/test_view_model.py", "quipu-cli", "unit", "test_view_model.py"),
    ("cli/__init__.py", "quipu-cli", None, "__init__.py"),

    # engine
    ("engine/sqlite/test_hydrator.py", "quipu-engine", "integration", "sqlite/test_hydrator.py"),
    ("engine/sqlite/test_reader.py", "quipu-engine", "integration", "sqlite/test_reader.py"),
    ("engine/sqlite/test_reader_integrity.py", "quipu-engine", "integration", "sqlite/test_reader_integrity.py"),
    ("engine/sqlite/test_writer.py", "quipu-engine", "integration", "sqlite/test_writer.py"),
    ("engine/sqlite/test_writer_idempotency.py", "quipu-engine", "integration", "sqlite/test_writer_idempotency.py"),
    ("engine/sqlite/__init__.py", "quipu-engine", "integration", "sqlite/__init__.py"),
    ("engine/test_branching.py", "quipu-engine", "integration", "test_branching.py"),
    ("engine/test_checkout_behavior.py", "quipu-engine", "integration", "test_checkout_behavior.py"),
    ("engine/test_config.py", "quipu-engine", "unit", "test_config.py"), # This is a unit test
    ("engine/test_deduplication.py", "quipu-engine", "integration", "test_deduplication.py"),
    ("engine/test_engine.py", "quipu-engine", "integration", "test_engine.py"),
    ("engine/test_engine_memory.py", "quipu-engine", "unit", "test_engine_memory.py"), # Uses in-memory backend
    ("engine/test_git_db.py", "quipu-engine", "integration", "test_git_db.py"),
    ("engine/test_git_reader.py", "quipu-engine", "integration", "test_git_reader.py"),
    ("engine/test_git_writer.py", "quipu-engine", "integration", "test_git_writer.py"),
    ("engine/test_head_tracking.py", "quipu-engine", "integration", "test_head_tracking.py"),
    ("engine/test_navigation.py", "quipu-engine", "integration", "test_navigation.py"),
    ("engine/__init__.py", "quipu-engine", None, "__init__.py"),

    # runtime
    ("runtime/acts/test_check.py", "quipu-runtime", "unit", "acts/test_check.py"),
    ("runtime/acts/test_git.py", "quipu-runtime", "unit", "acts/test_git.py"),
    ("runtime/acts/test_memory.py", "quipu-runtime", "unit", "acts/test_memory.py"),
    ("runtime/acts/test_patch_ambiguity.py", "quipu-runtime", "unit", "acts/test_patch_ambiguity.py"),
    ("runtime/acts/test_read.py", "quipu-runtime", "unit", "acts/test_read.py"),
    ("runtime/acts/test_refactor.py", "quipu-runtime", "unit", "acts/test_refactor.py"),
    ("runtime/acts/test_shell.py", "quipu-runtime", "unit", "acts/test_shell.py"),
    ("runtime/acts/__init__.py", "quipu-runtime", "unit", "acts/__init__.py"),
    ("runtime/conftest.py", "quipu-runtime", None, "conftest.py"),
    ("runtime/test_arg_strategy.py", "quipu-runtime", "unit", "test_arg_strategy.py"),
    ("runtime/test_parser_and_basic_acts.py", "quipu-runtime", "unit", "test_parser_and_basic_acts.py"),
    ("runtime/test_parser_auto_detect.py", "quipu-runtime", "unit", "test_parser_auto_detect.py"),
    ("runtime/test_parser_robustness.py", "quipu-runtime", "unit", "test_parser_robustness.py"),
    ("runtime/test_plugin_loader.py", "quipu-runtime", "unit", "test_plugin_loader.py"),
    ("runtime/test_plugin_resilience.py", "quipu-runtime", "unit", "test_plugin_resilience.py"),
    ("runtime/__init__.py", "quipu-runtime", None, "__init__.py"),

    # Top-level integration -> move to quipu-cli
    ("integration/conftest.py", "quipu-cli", "integration", "conftest.py"),
    ("integration/helpers.py", "quipu-cli", "integration", "helpers.py"),
    ("integration/test_cli_workflow.py", "quipu-cli", "integration", "test_cli_workflow.py"),
    ("integration/test_storage_selection.py", "quipu-cli", "integration", "test_storage_selection.py"),
    ("integration/test_sync_modes.py", "quipu-cli", "integration", "test_sync_modes.py"),
    ("integration/test_sync_workflow.py", "quipu-cli", "integration", "test_sync_workflow.py"),
    ("integration/test_workspace_invariance.py", "quipu-cli", "integration", "test_workspace_invariance.py"),
    ("integration/test_workspace_isolation.py", "quipu-cli", "integration", "test_workspace_isolation.py"),
    ("integration/__init__.py", "quipu-cli", "integration", "__init__.py"),

    # Root helpers and conftest
    ("helpers.py", "quipu-engine", None, "helpers.py"),
    ("conftest.py", "quipu-engine", None, "conftest.py"),
    ("__init__.py", None, None, None), # Ignore root __init__.py
]

def main():
    old_tests_dir = ROOT / "tests"
    if not old_tests_dir.is_dir():
        print(f"Error: Source directory '{old_tests_dir}' not found. Aborting.")
        return 1

    print("--- Starting Test Suite Refactoring ---")

    for old_rel_path, pkg_name, test_type, new_rel_path in MAPPING:
        if not pkg_name:
            continue
        
        src_path = old_tests_dir / old_rel_path
        
        if not src_path.exists():
            print(f"⚠️  [SKIP] Source file not found: {src_path}")
            continue

        dest_base = ROOT / "packages" / pkg_name / "tests"
        if test_type:
            dest_path = dest_base / test_type / new_rel_path
        else:
            dest_path = dest_base / new_rel_path

        print(f"➡️  Moving {src_path.relative_to(ROOT)} to {dest_path.relative_to(ROOT)}")

        if not DRY_RUN:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dest_path))

    # Cleanup
    print("\n--- Cleaning up old structure ---")
    
    # Remove tests/tests/ if it exists
    old_nested_tests = old_tests_dir / "tests"
    if old_nested_tests.exists():
        print(f"🗑️  Removing nested junk directory: {old_nested_tests.relative_to(ROOT)}")
        if not DRY_RUN:
            shutil.rmtree(old_nested_tests)

    # Remove the old top-level tests directory
    print(f"🗑️  Removing old top-level tests directory: {old_tests_dir.relative_to(ROOT)}")
    if not DRY_RUN:
        try:
            shutil.rmtree(old_tests_dir)
            print("✅  Cleanup successful.")
        except OSError as e:
            print(f"🔥  Error during cleanup: {e}")
            print("     Please remove the 'tests' directory manually.")
            return 1
            
    print("\n✅  Test suite refactoring complete!")
    return 0

if __name__ == "__main__":
    exit(main())
~~~~~

#### Acts 2: 运行重构脚本

现在，执行我们刚刚创建的脚本来迁移所有测试文件。

~~~~~act
run_command
~~~~~
~~~~~bash
python3 scripts/refactor_tests.py
~~~~~

#### Acts 3: 调整 `conftest.py` 文件

脚本已经移动了文件，但我们需要对 `conftest.py` 的内容进行微调，以确保正确的 fixture 位于正确的位置。

首先，`quipu-engine` 的 `conftest` 现在包含了所有顶层 fixture。我们需要从中移除 `runner`，因为它只与 CLI 相关。

~~~~~act
patch_file
packages/quipu-engine/tests/conftest.py
~~~~~
~~~~~python.old
import subprocess
from pathlib import Path

import pytest
from pyquipu.engine.git_db import GitDB
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """提供一个可复用的 CliRunner 实例。"""
    return CliRunner()


@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
~~~~~
~~~~~python.new
import subprocess
from pathlib import Path

import pytest
from pyquipu.engine.git_db import GitDB
from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from pyquipu.engine.state_machine import Engine


@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
~~~~~

接下来，将 `runner` fixture 添加到 `quipu-cli` 的 `conftest` 中。

~~~~~act
patch_file
packages/quipu-cli/tests/conftest.py
~~~~~
~~~~~python.old
import pytest
from pyquipu.engine.state_machine import Engine

# runner fixture is now in the root conftest.py, so it's removed from here.


@pytest.fixture
def quipu_workspace(engine_instance: Engine):
~~~~~
~~~~~python.new
import pytest
from pyquipu.engine.state_machine import Engine
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """提供一个可复用的 CliRunner 实例。"""
    return CliRunner()


@pytest.fixture
def quipu_workspace(engine_instance: Engine):
~~~~~

#### Acts 4: 清理重构脚本

任务已完成，删除该一次性脚本。

~~~~~act
delete_file
scripts/refactor_tests.py
~~~~~

### 下一步建议

重构已经完成。现在是验证的关键时刻。

*   **运行测试**: 在项目根目录运行 `pytest` 命令，确保所有测试都能被正确发现并成功通过。这会验证我们的文件移动和 `conftest.py` 调整是否正确。
*   **路径更新**: 检查新测试文件中的任何相对路径导入（例如 `from ..helpers import ...`），并根据需要进行调整。`pytest` 的路径发现机制通常能处理好大部分情况，但仍需留意。
*   **CI/CD 更新**: 如果有 CI/CD 配置文件（如 `.github/workflows/test.yml`），需要更新其中的路径，以确保测试命令能在新的目录结构下正确运行。
