## [WIP] fix: 恢复 QuipuNode 数据模型中缺失的 `content` 字段

### 错误分析
测试 `TestEngineWithMemoryBackend::test_plan_node_creation` 失败的根本原因是：在将 `pyquipu-interfaces` 重构为 `pyquipu-spec` 的过程中，我从 `QuipuNode` dataclass 的定义中**错误地删除了 `content` 字段**。

`content` 字段在系统中扮演着关键角色：
1.  **直接填充**: 当一个新节点被创建时（例如在 `InMemoryHistoryManager` 或 `SQLiteHistoryWriter` 中），其 `content` 会被立即填充。
2.  **懒加载缓存**: 对于从存储中读取的节点，`content` 字段作为懒加载内容的缓存位置。

`InMemoryHistoryManager` 在其 `create_node` 方法中，依然试图使用 `content` 关键字参数来实例化 `QuipuNode`，而新的、不完整的 `spec` 定义中缺少该字段，这直接导致了 `TypeError`。这是一个典型的因规范与实现不符而导致的集成失败。

### 用户需求
系统必须在重构后保持其核心数据模型的完整性，并通过所有现有的单元和集成测试。

### 评论
这是一个严重的疏忽，但也凸显了拥有像 `TestEngineWithMemoryBackend` 这样能够直接实例化数据模型的集成测试的重要性。它有效地捕获了在编译期或静态分析中可能被忽略的规范定义错误。

### 目标
1.  在 `packages/pyquipu-spec/src/quipu/spec/models/graph.py` 文件中，为 `QuipuNode` dataclass 重新添加 `content: str = ""` 字段。

### 基本原理
恢复 `content` 字段是唯一的正确做法。该字段是 `QuipuNode` 状态的固有组成部分。通过将其添加回 dataclass 定义，我们可以确保所有依赖此字段的组件（无论是生产代码还是测试代码）都能恢复正常工作，从而使类型规范与系统实际行为重新保持一致。

### 标签
#intent/fix #flow/ready #priority/critical
#comp/interfaces #concept/state #scope/core
#ai/instruct
#task/domain/architecture #task/object/spec-package #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 QuipuNode 定义

我们将 `content: str = ""` 字段添加回 `QuipuNode` dataclass 中，紧邻 `summary` 字段之前。

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/models/graph.py
~~~~~
~~~~~python.old
    filename: Path
    node_type: str  # "plan" | "capture"
    summary: str = ""
    owner_id: Optional[str] = None
~~~~~
~~~~~python.new
    filename: Path
    node_type: str  # "plan" | "capture"
    content: str = ""
    summary: str = ""
    owner_id: Optional[str] = None
~~~~~

### 下一步建议

现在，`QuipuNode` 的定义已经恢复正确。请重新运行 `pytest`。我预计之前失败的测试现在应该能够通过。

一旦所有测试都通过，我们就可以安全地继续执行重构路线图的后续步骤，即**收拢 `Renderer` 和 `PlanParser` 的 Protocol 定义**。
