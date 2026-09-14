# 📸 Snapshot Capture

### 💬 备注:
stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/quipu/application/factory.py               |   8 -
 .../src/quipu/application/factory.stitcher.yaml    |   8 +-
 packages/pyquipu-application/stitcher.lock         |  14 +-
 packages/pyquipu-cli/src/quipu/cli/main.py         |   4 +-
 .../pyquipu-cli/src/quipu/cli/main.stitcher.yaml   |   2 +
 packages/pyquipu-cli/stitcher.lock                 | 113 ++---
 .../pyquipu-engine/src/quipu/engine/git_storage.py |   7 -
 .../src/quipu/engine/git_storage.stitcher.yaml     |   9 +
 .../src/quipu/engine/memory_index.py               |   4 -
 .../src/quipu/engine/memory_index.stitcher.yaml    |   4 +
 .../pyquipu-engine/src/quipu/engine/projector.py   |   5 -
 .../src/quipu/engine/projector.stitcher.yaml       |   6 +
 .../src/quipu/engine/sqlite_index.py               |   6 -
 .../src/quipu/engine/sqlite_index.stitcher.yaml    |   7 +
 .../src/quipu/engine/state_machine.py              |   6 -
 .../src/quipu/engine/state_machine.stitcher.yaml   |   9 +-
 packages/pyquipu-engine/stitcher.lock              | 460 +++++++++++++++++----
 .../tests/unit/test_engine_decoupling.py           |   4 -
 .../unit/test_engine_decoupling.stitcher.yaml      |   8 +
 packages/pyquipu-runtime/stitcher.lock             | 112 ++---
 .../src/quipu/spec/protocols/storage.py            |  10 -
 .../src/quipu/spec/protocols/storage.stitcher.yaml |  10 +
 packages/pyquipu-spec/stitcher.lock                | 130 ++++--
 packages/pyquipu-test-utils/stitcher.lock          |  60 +--
 24 files changed, 684 insertions(+), 322 deletions(-)
```