# 📸 Snapshot Capture

### 💬 备注:
move pyquipu to quipu

检测到工作区发生变更。

### 📝 变更文件摘要:
```
conftest.py                                        |   2 +-
 install_quipu.py                                   |   8 -
 move_pyquipu_to_quipu.py                           |  10 -
 .../src/pyquipu/application/__init__.py            |   1 -
 .../src/pyquipu/application/controller.py          | 214 ---------------------
 .../pyquipu/application/controller.stitcher.yaml   |  41 ----
 .../src/pyquipu/application/factory.py             |  56 ------
 .../src/pyquipu/application/factory.stitcher.yaml  |  10 -
 .../src/pyquipu/application/plugin_manager.py      |  40 ----
 .../application/plugin_manager.stitcher.yaml       |   5 -
 .../src/pyquipu/application/utils.py               |  16 --
 .../src/pyquipu/application/utils.stitcher.yaml    |   2 -
 packages/pyquipu-application/src/quipu/__init__.py |   3 +
 .../src/quipu/application/__init__.py              |   1 +
 .../src/quipu/application/controller.py            | 214 +++++++++++++++++++++
 .../src/quipu/application/controller.stitcher.yaml |  41 ++++
 .../src/quipu/application/factory.py               |  56 ++++++
 .../src/quipu/application/factory.stitcher.yaml    |  10 +
 .../src/quipu/application/plugin_manager.py        |  40 ++++
 .../quipu/application/plugin_manager.stitcher.yaml |   5 +
 .../src/quipu/application/utils.py                 |  16 ++
 .../src/quipu/application/utils.stitcher.yaml      |   2 +
 packages/pyquipu-application/stitcher.lock         |  24 +--
 .../pyquipu-application/tests/unit/conftest.py     |   2 +-
 .../tests/unit/test_controller.py                  |  16 +-
 .../pyquipu-application/tests/unit/test_utils.py   |   2 +-
 packages/pyquipu-bus/src/pyquipu/__init__.py       |   2 -
 packages/pyquipu-bus/src/pyquipu/bus/__init__.py   |   3 -
 packages/pyquipu-bus/src/pyquipu/bus/bus.py        | 102 ----------
 packages/pyquipu-bus/src/pyquipu/bus/messages.py   |  19 --
 ...
 276 files changed, 7829 insertions(+), 7823 deletions(-)
```