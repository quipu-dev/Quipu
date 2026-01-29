# 📸 Snapshot Capture

### 💬 备注:
ruff and stitcher

检测到工作区发生变更。

### 📝 变更文件摘要:
```
.../src/quipu/cli/rendering.stitcher.yaml          |   4 +-
 packages/pyquipu-cli/stitcher.lock                 |   5 -
 packages/pyquipu-engine/stitcher.lock              |  16 +-
 .../src/quipu/runtime/parser.stitcher.yaml         |  15 +-
 packages/pyquipu-runtime/stitcher.lock             |  18 +-
 packages/pyquipu-spec/src/quipu/spec/exceptions.py |   8 -
 .../src/quipu/spec/exceptions.stitcher.yaml        |   8 +
 .../src/quipu/spec/models/execution.py             |   2 -
 .../src/quipu/spec/models/execution.stitcher.yaml  |   2 +
 .../pyquipu-spec/src/quipu/spec/models/graph.py    |   2 -
 .../src/quipu/spec/models/graph.stitcher.yaml      |   2 +
 .../src/quipu/spec/protocols/engine.py             |   2 -
 .../src/quipu/spec/protocols/engine.stitcher.yaml  |   2 +
 .../src/quipu/spec/protocols/messaging.py          |   2 -
 .../quipu/spec/protocols/messaging.stitcher.yaml   |   2 +
 .../src/quipu/spec/protocols/parser.py             |   2 -
 .../src/quipu/spec/protocols/parser.stitcher.yaml  |   2 +
 .../src/quipu/spec/protocols/runtime.py            |   9 -
 .../src/quipu/spec/protocols/runtime.stitcher.yaml |   8 +
 .../src/quipu/spec/protocols/storage.py            |   4 -
 .../src/quipu/spec/protocols/storage.stitcher.yaml |   4 +
 packages/pyquipu-spec/stitcher.lock                | 203 +++++++++++++++++++++
 22 files changed, 251 insertions(+), 71 deletions(-)
```