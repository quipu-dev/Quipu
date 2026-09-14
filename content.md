好的，我们已经完成了所有的重构与测试验证工作。现在我们将本次“存储与索引层解耦”架构重构的所有变更作为一个完整的逻辑单元提交到 Git 仓库。

## [COMMIT] refactor(engine): 解耦物理快照存储与逻辑图谱索引

### 用户需求
将本次完成的 Quipu Engine 存储与索引层解耦重构、CI/CD 纯内存模式实现、测试矩阵及版本号升级变更有序提交至 Git 仓库。

### 评论
这是一次关键的架构正骨，彻底消除了将 Git 物理快照与 SQLite 缓存当作同级存储的“虚假对等抽象”，建立了以 Git Plumbing 为物理真相（Source of Truth）、以 SQLite/内存为读模型投影（Graph Index）的 CQRS 分层结构。不仅极大提升了系统的扩展性，还为 CI/CD 场景提供了零额外 IO 的纯内存瞬时执行能力。

### 目标
1. 将所有涉及 Spec、Engine、Application、CLI、测试套件以及配置与依赖更新的文件暂存。
2. 创建结构清晰、详尽记录架构演进背景与实现细节的 Git 提交。

### 基本原理
- 遵循单一交付单元原则，在确保全量测试 100% 绿灯通过的前提下，将协议定义、组件提炼、中枢改造、测试闭环与版本对齐作为一个完整的原子提交入库。

### 标签
#intent/refine #flow/done #priority/high #comp/engine #comp/spec #comp/application #comp/cli #concept/state #scope/core #scope/api #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交变更

~~~~~act
git_add
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor(engine): decouple snapshot storage from graph index

- Define pure SnapshotStorage and GraphIndex protocols in pyquipu-spec, abolishing the false equivalence between Git and SQLite
- Extract GitSnapshotStorage as the sole source of truth for physical workspace snapshots, completely independent of SQLite
- Extract SQLiteGraphIndex as a pure query accelerator and topological metadata index
- Introduce InMemoryGraphIndex for zero-IO, ephemeral execution in CI/CD environments
- Refactor Hydrator into CacheProjector, formalizing unidirectional read-model projection from Git to SQLite
- Update Engine facade and create_engine factory to support use_cache=False
- Add decoupling test suite covering zero-IO CI mode and cache rebuild from scratch
- Bump pyquipu-spec to 0.2.0, pyquipu-engine/cli/application/meta-package to 0.4.0
~~~~~

### 下一步建议
- **CI/CD 工作流配置**: 可在项目 CI 流程脚本中直接调用 `create_engine(..., use_cache=False)`，体验极速无缓存运行。
- **文档同步**: 建议在架构文档中更新此分层结构图（物理快照存储 vs 逻辑图谱索引与读模型投影），以便后续协作者快速理解架构意图。
