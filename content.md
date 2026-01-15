# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
packages/pyquipu-bus/src/pyquipu/__init__.py       |   2 +-
 packages/pyquipu-bus/src/pyquipu/bus/__init__.py   |   2 +-
 packages/pyquipu-bus/src/pyquipu/bus/bus.py        |   2 +-
 packages/pyquipu-bus/src/pyquipu/bus/messages.py   |  11 +-
 .../pyquipu-bus/src/pyquipu/locales/zh/acts.json   |  65 +++++++++++
 .../pyquipu-bus/src/pyquipu/locales/zh/cli.json    | 121 +++++++++++++++++++++
 .../pyquipu-bus/src/pyquipu/locales/zh/engine.json |  60 ++++++++++
 .../src/pyquipu/locales/zh/runtime.json            |  15 +++
 .../pyquipu-cli/src/pyquipu/cli/commands/axon.py   |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/cache.py  |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/export.py |   2 +-
 .../src/pyquipu/cli/commands/helpers.py            |   2 +-
 .../src/pyquipu/cli/commands/navigation.py         |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/query.py  |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/remote.py |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/run.py    |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/show.py   |   2 +-
 .../pyquipu-cli/src/pyquipu/cli/commands/ui.py     |   2 +-
 .../src/pyquipu/cli/commands/workspace.py          |   2 +-
 packages/pyquipu-cli/src/pyquipu/cli/main.py       |   2 +-
 packages/pyquipu-cli/src/pyquipu/cli/ui_utils.py   |   2 +-
 .../src/pyquipu/common/locales/zh/acts.json        |  65 -----------
 .../src/pyquipu/common/locales/zh/cli.json         | 121 ---------------------
 .../src/pyquipu/common/locales/zh/engine.json      |  60 ----------
 .../src/pyquipu/common/locales/zh/runtime.json     |  15 ---
 .../pyquipu-engine/src/pyquipu/engine/config.py    |   2 +-
 .../pyquipu-engine/src/pyquipu/engine/git_db.py    |   2 +-
 packages/pyquipu-runtime/src/pyquipu/acts/basic.py |   2 +-
 packages/pyquipu-runtime/src/pyquipu/acts/check.py |   2 +-
 packages/pyquipu-runtime/src/pyquipu/acts/git.py   |   2 +-
 ...
 37 files changed, 295 insertions(+), 296 deletions(-)
```