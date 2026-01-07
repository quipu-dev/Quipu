# 📸 Snapshot Capture

### 💬 备注:
style: ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../quipu-application/tests/unit/conftest.json     |  3 +
 .../tests/unit/test_controller.json                | 20 +++++
 .../quipu-application/tests/unit/test_utils.json   |  7 ++
 .../quipu-cli/tests/integration/conftest.json      |  3 +
 .../tests/integration/test_cache_commands.json     | 30 +++++++
 .../tests/integration/test_cli_interaction.json    |  7 ++
 .../tests/integration/test_export_command.json     | 54 +++++++++++++
 .../integration/test_navigation_commands.json      | 18 +++++
 .../tests/integration/test_query_commands.json     | 36 +++++++++
 .../tests/integration/test_unfriendly_paths.json   | 37 +++++++++
 .../tests/integration/test_workspace_commands.json | 18 +++++
 .../quipu-cli/tests/unit/test_tui_logic.json       | 23 ++++++
 .../tests/unit/test_tui_reachability.json          | 18 +++++
 .../quipu-cli/tests/unit/test_view_model.json      | 94 ++++++++++++++++++++++
 .../tests/integration/sqlite/test_hydrator.json    | 23 ++++++
 .../tests/integration/sqlite/test_reader.json      | 56 +++++++++++++
 .../tests/integration/sqlite/test_writer.json      | 13 +++
 .../sqlite/test_writer_idempotency.json            | 12 +++
 .../tests/integration/test_branching.json          | 11 +++
 .../tests/integration/test_checkout_behavior.json  | 18 +++++
 .../tests/integration/test_engine.json             | 55 +++++++++++++
 .../tests/integration/test_git_db.json             | 88 ++++++++++++++++++++
 .../tests/integration/test_git_reader.json         | 37 +++++++++
 .../tests/integration/test_git_writer.json         | 21 +++++
 .../tests/integration/test_head_tracking.json      | 27 +++++++
 .../tests/unit/sqlite/test_reader_integrity.json   | 17 ++++
 .../quipu-engine/tests/unit/test_config.json       | 32 ++++++++
 .../tests/unit/test_deduplication.json             |  8 ++
 .../tests/unit/test_engine_memory.json             | 23 ++++++
 .../quipu-engine/tests/unit/test_navigation.json   | 24 ++++++
 ...
 125 files changed, 1862 insertions(+), 370 deletions(-)
```