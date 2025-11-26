# refactor: 验证并确认存储层的接口抽象

## 用户需求
根据开发路线图，执行第一步：对存储层进行接口抽象与解耦，为后续引入 SQLite 等新后端做准备。

## 评论
这是一个关键的架构重构步骤。通过将存储的“读”和“写”行为抽象为接口，可以使核心的 `Engine` 模块与具体的存储实现（无论是 Git 对象还是 SQLite 数据库）完全解耦，极大地增强了系统的可扩展性和可测试性。

## 目标
验证并确保 `Quipu` 系统的代码结构已经完成了存储层的解耦。具体表现为：
1.  `quipu-interfaces` 中存在清晰的、抽象的存储接口。
2.  `quipu-engine` 中的 `Engine` 类依赖于这些抽象接口，而非具体的实现类。
3.  `quipu-cli` 中的工厂函数负责创建具体的存储实现实例，并将其注入到 `Engine` 中。
4.  整个系统功能正常，所有测试通过。

## 基本原理
在开始修改代码之前，我首先对当前的代码库进行了详细的分析，以评估其与“第一步”目标的符合程度。

分析结果表明，当前系统架构**已经完全实现了**这一阶段所要求的所有解耦目标。

1.  **接口已定义**: 在 `packages/quipu-interfaces/src/quipu/core/storage.py` 中，已经定义了 `HistoryReader` 和 `HistoryWriter` 两个抽象基类，它们清晰地描述了历史记录的读写契约。
2.  **引擎已解耦 (依赖注入)**: 在 `packages/quipu-engine/src/quipu/core/state_machine.py` 中，`Engine` 类的构造函数 `__init__` 接收 `reader: HistoryReader` 和 `writer: HistoryWriter` 作为参数。这表明 `Engine` 依赖于抽象接口，而不是任何具体的存储实现。
3.  **工厂模式已实现**: 在 `packages/quipu-cli/src/quipu/cli/factory.py` 中，`create_engine` 函数根据配置决定要实例化的具体读写器 (`GitObjectHistoryReader/Writer`)，然后将这些实例注入到 `Engine` 的构造函数中。这正是实现解耦的最佳实践。

综上所述，代码库的当前状态已经提前达到了第一步的完成标准。这是一个非常好的状态，意味着我们可以直接进入后续的 SQLite 实现阶段，而无需进行额外的重构。

因此，本计划不包含任何代码修改 (`act`) 操作，其目的在于**确认和记录**当前架构的健康状态，并正式为下一阶段的工作做好准备。

## 标签
#intent/architect #flow/ready #priority/high
#comp/engine #comp/cli #comp/interfaces #concept/state #concept/history #scope/core #scope/api
#ai/brainstorm
#task/domain/storage #task/object/interface-decoupling #task/action/verification #task/state/begin #task/status/completed

---

## Script

### Acts 1: 确认架构

本次任务的核心是确认当前架构的健康度，无需对代码进行任何修改。现有结构已经为下一步的 SQLite 集成做好了充分准备。

```act
end
```
