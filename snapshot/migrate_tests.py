import shutil
from pathlib import Path

# 定义从 tests/ 子目录到 packages/ 内部的精确映射
# 格式: "source_file_path": "package_name/test_type"
# test_type 必须是 'unit' 或 'integration'
TEST_MAPPING = {
    # Application Tests
    "application/conftest.py": "quipu-application/unit",
    "application/test_controller.py": "quipu-application/unit",
    "application/test_utils.py": "quipu-application/unit",

    # CLI Tests (mostly integration)
    "cli/conftest.py": "quipu-cli/integration",
    "cli/test_cache_commands.py": "quipu-cli/integration",
    "cli/test_cli_interaction.py": "quipu-cli/integration",
    "cli/test_export_command.py": "quipu-cli/integration",
    "cli/test_navigation_commands.py": "quipu-cli/integration",
    "cli/test_query_commands.py": "quipu-cli/integration",
    "cli/test_tui_logic.py": "quipu-cli/unit",
    "cli/test_tui_reachability.py": "quipu-cli/unit",
    "cli/test_unfriendly_paths.py": "quipu-cli/integration",
    "cli/test_view_model.py": "quipu-cli/unit",
    "cli/test_workspace_commands.py": "quipu-cli/integration",

    # Engine Tests
    "engine/sqlite/test_hydrator.py": "quipu-engine/integration/sqlite",
    "engine/sqlite/test_reader.py": "quipu-engine/integration/sqlite",
    "engine/sqlite/test_reader_integrity.py": "quipu-engine/unit/sqlite",
    "engine/sqlite/test_writer.py": "quipu-engine/integration/sqlite",
    "engine/sqlite/test_writer_idempotency.py": "quipu-engine/integration/sqlite",
    "engine/test_branching.py": "quipu-engine/integration",
    "engine/test_checkout_behavior.py": "quipu-engine/integration",
    "engine/test_config.py": "quipu-engine/unit",
    "engine/test_deduplication.py": "quipu-engine/unit",
    "engine/test_engine.py": "quipu-engine/integration",
    "engine/test_engine_memory.py": "quipu-engine/unit",
    "engine/test_git_db.py": "quipu-engine/integration",
    "engine/test_git_reader.py": "quipu-engine/integration",
    "engine/test_git_writer.py": "quipu-engine/integration",
    "engine/test_head_tracking.py": "quipu-engine/integration",
    "engine/test_navigation.py": "quipu-engine/unit",

    # Runtime Tests (mostly unit)
    "runtime/acts/test_check.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_git.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_memory.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_patch_ambiguity.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_read.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_refactor.py": "quipu-runtime/unit/acts",
    "runtime/acts/test_shell.py": "quipu-runtime/unit/acts",
    "runtime/conftest.py": "quipu-runtime/unit",
    "runtime/test_arg_strategy.py": "quipu-runtime/unit",
    "runtime/test_parser_and_basic_acts.py": "quipu-runtime/unit",
    "runtime/test_parser_auto_detect.py": "quipu-runtime/unit",
    "runtime/test_parser_robustness.py": "quipu-runtime/unit",
    "runtime/test_plugin_loader.py": "quipu-runtime/unit",
    "runtime/test_plugin_resilience.py": "quipu-runtime/unit",
}

def main():
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Error: This script must be run from the project root directory.")
        return 1

    source_base = project_root / "tests"
    dest_base = project_root / "packages"

    print("🚀 Starting test file migration...")

    for src_rel_path_str, dest_info in TEST_MAPPING.items():
        src_rel_path = Path(src_rel_path_str)
        src_abs_path = source_base / src_rel_path

        package_name, test_type_path = dest_info.split("/", 1)
        
        # Preserve the original file name
        file_name = src_rel_path.name
        
        # Build the destination path
        dest_dir = dest_base / package_name / "tests" / test_type_path
        dest_abs_path = dest_dir / file_name

        if not src_abs_path.exists():
            print(f"⚠️  Warning: Source file not found, skipping: {src_abs_path}")
            continue

        # Create destination directory if it doesn't exist
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir.parent / "__init__.py").touch(exist_ok=True)
        (dest_dir / "__init__.py").touch(exist_ok=True)

        if dest_abs_path.exists():
            print(f"⚠️  Warning: Destination file already exists, skipping: {dest_abs_path}")
            continue

        print(f"🚚 Moving: {src_rel_path} -> packages/{package_name}/tests/{test_type_path}/")
        shutil.move(str(src_abs_path), str(dest_abs_path))

    print("\n✅ Migration complete.")
    return 0

if __name__ == "__main__":
    exit(main())