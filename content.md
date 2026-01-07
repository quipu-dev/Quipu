# 📸 Snapshot Capture

检测到工作区发生变更。

### 📝 变更文件摘要:
```
packages/__init__.py                               |   0
 packages/quipu-application/__init__.py             |   0
 packages/quipu-application/tests/__init__.py       |   0
 packages/quipu-application/tests/conftest.py       |  37 ---
 .../tests/unit/test_controller.py                  | 109 ---------
 .../quipu-application/tests/unit/test_utils.py     |  26 ---
 packages/quipu-cli/__init__.py                     |   0
 packages/quipu-cli/tests/__init__.py               |   0
 packages/quipu-cli/tests/conftest.py               |  18 --
 packages/quipu-cli/tests/integration/__init__.py   |   0
 packages/quipu-cli/tests/integration/conftest.py   |  38 ---
 packages/quipu-cli/tests/integration/helpers.py    |   8 -
 .../tests/integration/test_cache_commands.py       | 129 -----------
 .../tests/integration/test_cli_interaction.py      |  34 ---
 .../tests/integration/test_cli_workflow.py         | 240 -------------------
 .../tests/integration/test_export_command.py       | 255 ---------------------
 .../tests/integration/test_navigation_commands.py  |  80 -------
 .../tests/integration/test_query_commands.py       | 164 -------------
 .../tests/integration/test_storage_selection.py    | 189 ---------------
 .../quipu-cli/tests/integration/test_sync_modes.py | 170 --------------
 .../tests/integration/test_sync_workflow.py        | 206 -----------------
 .../tests/integration/test_unfriendly_paths.py     | 181 ---------------
 .../tests/integration/test_workspace_commands.py   |  60 -----
 .../tests/integration/test_workspace_invariance.py |  77 -------
 .../tests/integration/test_workspace_isolation.py  |  76 ------
 packages/quipu-cli/tests/unit/test_tui_logic.py    |  74 ------
 .../quipu-cli/tests/unit/test_tui_reachability.py  |  78 -------
 packages/quipu-cli/tests/unit/test_view_model.py   | 204 -----------------
 packages/quipu-common/__init__.py                  |   0
 packages/quipu-engine/__init__.py                  |   0
 ...
 136 files changed, 6057 insertions(+), 5895 deletions(-)
```