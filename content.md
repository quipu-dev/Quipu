# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/pyquipu/application/controller.json        |  29 +++++
 .../src/pyquipu/application/factory.json           |   7 ++
 .../src/pyquipu/application/plugin_manager.json    |  10 ++
 .../src/pyquipu/application/utils.json             |   7 ++
 .../quipu-cli/src/pyquipu/cli/commands/axon.json   |   6 +
 .../quipu-cli/src/pyquipu/cli/commands/cache.json  |  17 +++
 .../quipu-cli/src/pyquipu/cli/commands/export.json |  31 +++++
 .../src/pyquipu/cli/commands/helpers.json          |  27 +++++
 .../src/pyquipu/cli/commands/navigation.json       |   6 +
 .../quipu-cli/src/pyquipu/cli/commands/query.json  |  11 ++
 .../quipu-cli/src/pyquipu/cli/commands/remote.json |   6 +
 .../quipu-cli/src/pyquipu/cli/commands/run.json    |   6 +
 .../quipu-cli/src/pyquipu/cli/commands/show.json   |  11 ++
 .../quipu-cli/src/pyquipu/cli/commands/ui.json     |   6 +
 .../src/pyquipu/cli/commands/workspace.json        |   6 +
 .../packages/quipu-cli/src/pyquipu/cli/config.json |   7 ++
 .../quipu-cli/src/pyquipu/cli/logger_config.json   |  12 ++
 .../quipu-cli/src/pyquipu/cli/rendering.json       |  48 ++++++++
 .../packages/quipu-cli/src/pyquipu/cli/tui.json    | 105 ++++++++++++++++
 .../quipu-cli/src/pyquipu/cli/ui_utils.json        |  12 ++
 .../quipu-cli/src/pyquipu/cli/view_model.json      |  68 +++++++++++
 .../quipu-common/src/pyquipu/common/identity.json  |   7 ++
 .../src/pyquipu/common/messaging/bus.json          |  82 +++++++++++++
 .../src/pyquipu/common/messaging/messages.json     |   7 ++
 .../quipu-engine/src/pyquipu/engine/config.json    |  34 ++++++
 .../quipu-engine/src/pyquipu/engine/git_db.json    | 134 +++++++++++++++++++++
 .../src/pyquipu/engine/git_object_storage.json     |  95 +++++++++++++++
 .../quipu-engine/src/pyquipu/engine/hydrator.json  |  24 ++++
 .../quipu-engine/src/pyquipu/engine/sqlite_db.json |  49 ++++++++
 .../src/pyquipu/engine/sqlite_storage.json         |  70 +++++++++++
 ...
 136 files changed, 2007 insertions(+), 689 deletions(-)
```