import shutil
from pathlib import Path

# Explicit mapping of old test file paths to their new locations.
# This acts as the Single Source of Truth for the refactoring.
FILE_MAP = {
    # Application tests
    "tests/application/conftest.py": "packages/quipu-application/tests/conftest.py",
    "tests/application/test_controller.py": "packages/quipu-application/tests/unit/test_controller.py",
    "tests/application/test_utils.py": "packages/quipu-application/tests/unit/test_utils.py",
    # CLI tests
    "tests/cli/conftest.py": "packages/quipu-cli/tests/conftest.py",
    "tests/cli/test_cache_commands.py": "packages/quipu-cli/tests/integration/test_cache_commands.py",
    "tests/cli/test_cli_interaction.py": "packages/quipu-cli/tests/integration/test_cli_interaction.py",
    "tests/cli/test_export_command.py": "packages/quipu-cli/tests/integration/test_export_command.py",
    "tests/cli/test_navigation_commands.py": "packages/quipu-cli/tests/integration/test_navigation_commands.py",
    "tests/cli/test_query_commands.py": "packages/quipu-cli/tests/integration/test_query_commands.py",
    "tests/cli/test_unfriendly_paths.py": "packages/quipu-cli/tests/integration/test_unfriendly_paths.py",
    "tests/cli/test_workspace_commands.py": "packages/quipu-cli/tests/integration/test_workspace_commands.py",
    "tests/cli/test_tui_logic.py": "packages/quipu-cli/tests/unit/tui/test_logic.py",
    "tests/cli/test_tui_reachability.py": "packages/quipu-cli/tests/unit/tui/test_reachability.py",
    "tests/cli/test_view_model.py": "packages/quipu-cli/tests/unit/tui/test_view_model.py",
    # Engine tests
    "tests/engine/test_branching.py": "packages/quipu-engine/tests/integration/test_branching.py",
    "tests/engine/test_checkout_behavior.py": "packages/quipu-engine/tests/integration/test_checkout_behavior.py",
    "tests/engine/test_config.py": "packages/quipu-engine/tests/unit/test_config.py",
    "tests/engine/test_deduplication.py": "packages/quipu-engine/tests/integration/test_deduplication.py",
    "tests/engine/test_engine.py": "packages/quipu-engine/tests/integration/test_engine.py",
    "tests/engine/test_engine_memory.py": "packages/quipu-engine/tests/unit/test_engine_memory.py",
    "tests/engine/test_git_db.py": "packages/quipu-engine/tests/integration/test_git_db.py",
    "tests/engine/test_git_reader.py": "packages/quipu-engine/tests/integration/test_git_reader.py",
    "tests/engine/test_git_writer.py": "packages/quipu-engine/tests/integration/test_git_writer.py",
    "tests/engine/test_head_tracking.py": "packages/quipu-engine/tests/integration/test_head_tracking.py",
    "tests/engine/test_navigation.py": "packages/quipu-engine/tests/integration/test_navigation.py",
    "tests/engine/sqlite/test_hydrator.py": "packages/quipu-engine/tests/integration/sqlite/test_hydrator.py",
    "tests/engine/sqlite/test_reader.py": "packages/quipu-engine/tests/integration/sqlite/test_reader.py",
    "tests/engine/sqlite/test_reader_integrity.py": "packages/quipu-engine/tests/integration/sqlite/test_reader_integrity.py",
    "tests/engine/sqlite/test_writer.py": "packages/quipu-engine/tests/integration/sqlite/test_writer.py",
    "tests/engine/sqlite/test_writer_idempotency.py": "packages/quipu-engine/tests/integration/sqlite/test_writer_idempotency.py",
    # Runtime tests
    "tests/runtime/conftest.py": "packages/quipu-runtime/tests/conftest.py",
    "tests/runtime/test_arg_strategy.py": "packages/quipu-runtime/tests/unit/test_arg_strategy.py",
    "tests/runtime/test_parser_and_basic_acts.py": "packages/quipu-runtime/tests/unit/test_parser_and_basic_acts.py",
    "tests/runtime/test_parser_auto_detect.py": "packages/quipu-runtime/tests/unit/test_parser_auto_detect.py",
    "tests/runtime/test_parser_robustness.py": "packages/quipu-runtime/tests/unit/test_parser_robustness.py",
    "tests/runtime/test_plugin_loader.py": "packages/quipu-runtime/tests/unit/test_plugin_loader.py",
    "tests/runtime/test_plugin_resilience.py": "packages/quipu-runtime/tests/unit/test_plugin_resilience.py",
    "tests/runtime/acts/test_check.py": "packages/quipu-runtime/tests/unit/acts/test_check.py",
    "tests/runtime/acts/test_git.py": "packages/quipu-runtime/tests/integration/acts/test_git.py",
    "tests/runtime/acts/test_memory.py": "packages/quipu-runtime/tests/unit/acts/test_memory.py",
    "tests/runtime/acts/test_patch_ambiguity.py": "packages/quipu-runtime/tests/unit/acts/test_patch_ambiguity.py",
    "tests/runtime/acts/test_read.py": "packages/quipu-runtime/tests/unit/acts/test_read.py",
    "tests/runtime/acts/test_refactor.py": "packages/quipu-runtime/tests/unit/acts/test_refactor.py",
    "tests/runtime/acts/test_shell.py": "packages/quipu-runtime/tests/integration/acts/test_shell.py",
    # Cross-package integration tests -> moved to CLI as they are CLI-driven
    "tests/integration/conftest.py": "packages/quipu-cli/tests/integration/sync/conftest.py",
    "tests/integration/test_cli_workflow.py": "packages/quipu-cli/tests/integration/test_cli_workflow.py",
    "tests/integration/test_storage_selection.py": "packages/quipu-cli/tests/integration/test_storage_selection.py",
    "tests/integration/test_sync_modes.py": "packages/quipu-cli/tests/integration/sync/test_modes.py",
    "tests/integration/test_sync_workflow.py": "packages/quipu-cli/tests/integration/sync/test_workflow.py",
    "tests/integration/test_workspace_invariance.py": "packages/quipu-cli/tests/integration/test_workspace_invariance.py",
    "tests/integration/test_workspace_isolation.py": "packages/quipu-cli/tests/integration/test_workspace_isolation.py",
    # Root conftest needs to be split and moved
    "tests/conftest.py": "packages/quipu-engine/tests/conftest.py",
}

def main():
    """Executes the test suite refactoring."""
    project_root = Path(__file__).parent.resolve()
    print(f"Project root detected at: {project_root}")

    # Step 1: Split the root conftest.py
    print("\n--- Splitting root conftest.py ---")
    root_conftest_path = project_root / "tests/conftest.py"
    if root_conftest_path.exists():
        content = root_conftest_path.read_text()
        
        # Engine-related fixtures
        engine_fixtures = [
            'import subprocess',
            'from pathlib import Path',
            'import pytest',
            'from pyquipu.engine.git_db import GitDB',
            'from pyquipu.engine.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter',
            'from pyquipu.engine.state_machine import Engine',
        ]
        engine_code = [
            fixture for fixture in content.split('@pytest.fixture')
            if 'engine_instance' in fixture or 'git_workspace' in fixture
        ]
        
        # CLI-related fixtures
        cli_fixtures = [
            'import pytest',
            'from typer.testing import CliRunner'
        ]
        cli_code = [
            fixture for fixture in content.split('@pytest.fixture')
            if 'runner' in fixture
        ]

        if engine_code:
            engine_conftest_target = project_root / "packages/quipu-engine/tests/conftest.py"
            engine_conftest_target.parent.mkdir(parents=True, exist_ok=True)
            full_engine_code = "\n".join(engine_fixtures) + "\n\n" + "\n\n@pytest.fixture".join(engine_code)
            engine_conftest_target.write_text(full_engine_code)
            print(f"Moved engine fixtures to {engine_conftest_target.relative_to(project_root)}")

        if cli_code:
            cli_conftest_target = project_root / "packages/quipu-cli/tests/conftest.py"
            cli_conftest_target.parent.mkdir(parents=True, exist_ok=True)
            full_cli_code = "\n".join(cli_fixtures) + "\n\n" + "\n@pytest.fixture".join(cli_code)
            cli_conftest_target.write_text(full_cli_code)
            print(f"Moved CLI fixtures to {cli_conftest_target.relative_to(project_root)}")
            
        # We handled it, so remove from main map to avoid double-move
        del FILE_MAP["tests/conftest.py"]
    else:
        print("Root conftest.py not found, skipping split.")


    # Step 2: Move all other files according to the map
    print("\n--- Moving test files ---")
    for old_path_str, new_path_str in FILE_MAP.items():
        source_path = project_root / old_path_str
        dest_path = project_root / new_path_str

        if not source_path.exists():
            print(f"🟡 SKIPPED: Source file not found: {source_path.relative_to(project_root)}")
            continue

        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        try:
            source_path.rename(dest_path)
            print(f"✅ MOVED: {source_path.relative_to(project_root)} -> {dest_path.relative_to(project_root)}")
        except Exception as e:
            print(f"🔴 FAILED to move {source_path.relative_to(project_root)}: {e}")

    # Step 3: Clean up old directories
    print("\n--- Cleaning up old directories ---")
    old_test_dirs = [
        project_root / "tests/application",
        project_root / "tests/cli",
        project_root / "tests/engine/sqlite",
        project_root / "tests/engine",
        project_root / "tests/integration",
        project_root / "tests/runtime/acts",
        project_root / "tests/runtime",
    ]

    for dir_path in old_test_dirs:
        if dir_path.exists() and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                print(f"🗑️ REMOVED empty directory: {dir_path.relative_to(project_root)}")
            except OSError as e:
                print(f"🟡 WARN: Could not remove {dir_path.relative_to(project_root)}: {e}")
        elif dir_path.exists():
             print(f"🟡 SKIPPED non-empty directory: {dir_path.relative_to(project_root)}")


    # Create __init__.py files to make sure tests are discoverable
    print("\n--- Ensuring test packages are valid ---")
    for new_path_str in FILE_MAP.values():
        current_path = project_root / new_path_str
        # Iterate up to the 'tests' directory
        while current_path.name != 'tests' and current_path.parent != current_path:
            init_file = current_path.parent / "__init__.py"
            if not init_file.exists():
                print(f"✨ CREATED: {init_file.relative_to(project_root)}")
                init_file.touch()
            current_path = current_path.parent


    print("\nRefactoring complete. Please run 'pytest' to verify the changes.")

if __name__ == "__main__":
    main()