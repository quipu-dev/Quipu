# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/pyquipu/application/controller.json        |  35 ------
 .../src/pyquipu/application/factory.json           |   8 --
 .../src/pyquipu/application/plugin_manager.json    |  10 --
 .../src/pyquipu/application/utils.json             |   8 --
 .../quipu-application/tests/unit/conftest.json     |   3 -
 .../tests/unit/test_controller.json                |  20 ----
 .../quipu-application/tests/unit/test_utils.json   |   7 --
 .../quipu-cli/src/pyquipu/cli/commands/axon.json   |   7 --
 .../quipu-cli/src/pyquipu/cli/commands/cache.json  |  19 ----
 .../quipu-cli/src/pyquipu/cli/commands/export.json |  32 ------
 .../src/pyquipu/cli/commands/helpers.json          |  28 -----
 .../src/pyquipu/cli/commands/navigation.json       |   7 --
 .../quipu-cli/src/pyquipu/cli/commands/query.json  |  11 --
 .../quipu-cli/src/pyquipu/cli/commands/remote.json |  12 --
 .../quipu-cli/src/pyquipu/cli/commands/run.json    |   7 --
 .../quipu-cli/src/pyquipu/cli/commands/show.json   |  12 --
 .../quipu-cli/src/pyquipu/cli/commands/ui.json     |   7 --
 .../src/pyquipu/cli/commands/workspace.json        |   6 -
 .../packages/quipu-cli/src/pyquipu/cli/config.json |  11 --
 .../quipu-cli/src/pyquipu/cli/logger_config.json   |  12 --
 .../packages/quipu-cli/src/pyquipu/cli/main.json   |   3 -
 .../quipu-cli/src/pyquipu/cli/rendering.json       |  48 --------
 .../packages/quipu-cli/src/pyquipu/cli/tui.json    | 122 ---------------------
 .../quipu-cli/src/pyquipu/cli/ui_utils.json        |  12 --
 .../quipu-cli/src/pyquipu/cli/view_model.json      |  79 -------------
 .../quipu-cli/tests/integration/conftest.json      |   3 -
 .../tests/integration/test_cache_commands.json     |  30 -----
 .../tests/integration/test_cli_interaction.json    |   7 --
 .../tests/integration/test_export_command.json     |  54 ---------
 .../integration/test_navigation_commands.json      |  18 ---
 ...
 490 files changed, 15016 insertions(+), 18019 deletions(-)
```