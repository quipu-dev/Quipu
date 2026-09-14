## [WIP] fix: 统一 GraphIndex.record_node 签名并支持元数据参数

### 错误分析
- **现象**: 在执行 `test_engine_ci_mode_no_cache_zero_io` 时抛出 `TypeError: InMemoryGraphIndex.record_node() got an unexpected keyword argument 'meta_json'`。
- **根因**: `Engine.capture_drift` 和 `create_plan_node` 在调用 `self.index.record_node(new_node, meta_json=meta_json)` 时传入了 `meta_json` 关键字参数。`SQLiteGraphIndex` 显式支持该参数，但 `InMemoryGraphIndex` 和 `GraphIndex` 协议定义的入参签名中缺少 `meta_json` 及 `**kwargs`，导致纯内存索引在接收到该参数时报错。

### 用户需求
统一 `GraphIndex` 契约及 `InMemoryGraphIndex` 中 `record_node` 的方法签名，支持可选的 `meta_json` 参数，并重新运行全量测试。

### 评论
接口签名的细微差异会在具体多态实现切换时暴露出来。将协议中的 `record_node` 规范化为接受可选的序列化元数据（`meta_json: str | None = None`），既能让持久化索引利用已序列化的快照元数据避免重复计算，也能让轻量/内存索引静默忽略，保证多态调用的一致性。

### 目标
1. 在 `quipu.spec.protocols.storage.GraphIndex` 中将 `record_node` 签名更新为接受 `meta_json: str | None = None, **kwargs: Any`。
2. 在 `quipu.engine.memory_index.InMemoryGraphIndex` 中同步实现该签名。
3. 运行 `pytest` 验证解耦测试及全量测试套件通过。

### 基本原理
- 遵循开放-封闭与里氏替换原则，所有 `GraphIndex` 的子类型必须兼容超类型所要求的所有调用协议。支持 `meta_json: str | None = None, **kwargs: Any` 可以让上层调用方统一投递元数据上下文。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #comp/spec #concept/state #scope/api #ai/instruct #task/domain/storage #task/object/engine-decoupling #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 更新 `GraphIndex` 协议签名

~~~~~act
patch_file
packages/pyquipu-spec/src/quipu/spec/protocols/storage.py
~~~~~
~~~~~python
@runtime_checkable
class GraphIndex(Protocol):
    """定义图谱拓扑与元数据索引层的契约 (Read-Model / Query Cache).

    仅维护 QuipuNode 节点元数据、拓扑父子关系和轻量缓存，
    不负责文件物理实体的落盘。
    """

    def record_node(self, node: QuipuNode) -> None: ...

    def get_node(self, commit_hash: str) -> QuipuNode | None: ...
~~~~~
~~~~~python
@runtime_checkable
class GraphIndex(Protocol):
    """定义图谱拓扑与元数据索引层的契约 (Read-Model / Query Cache).

    仅维护 QuipuNode 节点元数据、拓扑父子关系和轻量缓存，
    不负责文件物理实体的落盘。
    """

    def record_node(self, node: QuipuNode, meta_json: str | None = None, **kwargs: Any) -> None: ...

    def get_node(self, commit_hash: str) -> QuipuNode | None: ...
~~~~~

#### Acts 2: 更新 `InMemoryGraphIndex.record_node` 实现

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/memory_index.py
~~~~~
~~~~~python
    def record_node(self, node: QuipuNode) -> None:
        self._nodes[node.commit_hash] = node
        if node.parent and node.parent.commit_hash in self._nodes:
            parent_in_index = self._nodes[node.parent.commit_hash]
            if node not in parent_in_index.children:
                parent_in_index.children.append(node)
~~~~~
~~~~~python
    def record_node(self, node: QuipuNode, meta_json: str | None = None, **kwargs: Any) -> None:
        self._nodes[node.commit_hash] = node
        if node.parent and node.parent.commit_hash in self._nodes:
            parent_in_index = self._nodes[node.parent.commit_hash]
            if node not in parent_in_index.children:
                parent_in_index.children.append(node)
~~~~~

### 下一步建议
通过更新协议与内存索引方法签名，`InMemoryGraphIndex` 已能够安全处理 Engine 传入的元数据参数。执行 `uv run pytest` 将验证全量测试套件的绿灯通过情况。如果所有测试均通过，即可进行后续的 Git 提交确认。
