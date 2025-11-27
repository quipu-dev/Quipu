好的，分析完成。

你的判断是正确的。这个问题暴露了系统内部一个更深层次的、系统性的风险：**标识符模糊 (Identifier Ambiguity)**。直接修复 `get_ancestor_hashes` 只是治标，我们需要一次小规模的重构来治本，以消除这种模糊性，增强系统的长期可维护性。

以下是为执行此重构而制定的非代码计划。

---

### 计划：消除 Quipu 核心标识符的模糊性

#### 用户需求
我们发现 `output_tree` 哈希和 `commit_hash` 在系统不同层级之间被混用，导致了数据查询失败和 UI 显示错误。根本原因在于 API 契约不明确，变量命名不统一，以及数据模型存在历史遗留的“便利性设计”。本次重构的目标是彻底消除这种模糊性。

#### 评论
这是一个关键的架构健康度任务。消除模糊的 API 契约将显著降低未来开发的认知负荷和出错概率，是系统从原型走向成熟的必经之路。

#### 目标
1.  在整个代码库中，对 `commit_hash` 和 `output_tree_hash` 进行严格区分和显式命名。
2.  更新核心数据模型 `QuipuNode`，使其包含所有必要的标识符，消除对 `.filename` 字段的依赖。
3.  重构数据访问层 (`HistoryReader`) 的 API，使其契约清晰无误。
4.  确保上层逻辑 (ViewModel, UI) 使用正确的标识符进行调用。

#### 基本原理
我们将遵循“自下而上”的重构策略，从最核心的数据模型开始，逐层向上修复，确保每一步的变更都有稳定的底层支持。

1.  **数据模型是唯一事实源**: `QuipuNode` 对象必须携带自身完整的身份信息。
2.  **API 契约神圣**: 函数的参数名和返回值文档必须精确反映其处理的数据类型。
3.  **封装转换逻辑**: 标识符之间的转换应在数据访问层的边界内完成，不应泄露给上层调用者。

#### 标签
#intent/refactor #flow/ready #priority/high
#comp/engine #comp/cli #comp/interfaces #concept/history #scope/core #scope/api
#ai/brainstorm
#task/domain/storage #task/object/api-contract #task/action/refactor
#task/state/begin #task/status/active

---

### 其他模糊点分析

在制定具体计划前，我们先识别出所有相关的模糊点，以便一并处理：

1.  **`QuipuNode.filename` 的滥用**: 这是当前最大的问题。`filename` 字段被用作一个便利的容器来存储 `commit_hash` (`Path(f".quipu/git_objects/{commit_hash}")`)。这是一种隐式契约，非常脆弱且不直观。
2.  **`Engine.history_graph` 的键**: 这个字典的键是 `output_tree`，但代码中没有明确说明。这导致在遍历或访问该图时，开发者需要去猜测键的类型。
3.  **通用的 `hash` 变量名**: 在 `main.py` 的 `checkout` 命令、`tui.py` 的状态变量、`view_model.py` 的`current_hash` 等多处，都使用了 `hash`、`target_hash`、`current_hash` 这样模糊的命名，无法一眼看出其类型。
4.  **`HistoryReader` 接口的不精确性**: 如我们所发现的，`get_ancestor_hashes(commit_hash: str)` 的参数名与其实际接收的数据类型不匹配，这在多个接口方法中都可能存在。

### 执行计划

#### 阶段一：基础重构 - 强化数据模型

**目标**：让 `QuipuNode` 成为一个自包含的、信息完整的实体。

1.  **修改 `quipu-interfaces`**:
    *   **文件**: `packages/quipu-interfaces/src/quipu/core/models.py`
    *   **动作**:
        *   在 `QuipuNode` 数据类中，添加一个新的、非可选的字段：`commit_hash: str`。
        *   添加文档字符串，明确 `commit_hash` 代表历史事件，`output_tree` 代表文件系统状态。
        *   明确 `filename` 字段的用途仅为指向物理存储位置的“指针”，不应再被用于提取 `commit_hash`。

#### 阶段二：数据访问层重构 - 明确 API 契约

**目标**：修复 `HistoryReader` 及其实现，使其接口清晰，并封装转换逻辑。

1.  **修改 `HistoryReader` 接口**:
    *   **文件**: `packages/quipu-interfaces/src/quipu/core/storage.py`
    *   **动作**:
        *   审查所有方法签名。将所有模糊的 `hash` 参数重命名为 `commit_hash` 或 `output_tree_hash`。
        *   **特别修改 `get_ancestor_hashes`**: 将其签名改为 `get_ancestor_output_trees(start_output_tree_hash: str) -> Set[str]`。这使得 API 契约变得极其清晰：它接收一个 `output_tree` 哈希，并返回一个 `output_tree` 哈希的集合。

2.  **修改 `SQLiteHistoryReader` 实现**:
    *   **文件**: `packages/quipu-engine/src/quipu/core/sqlite_storage.py`
    *   **动作**:
        *   更新所有 `load` 方法 (`load_all_nodes`, `load_nodes_paginated`)，确保在从数据库读取数据时，将 `commit_hash` 字段正确填充到新的 `QuipuNode.commit_hash` 属性中。
        *   重写 `get_ancestor_hashes` (现在是 `get_ancestor_output_trees`) 的逻辑，实现之前分析的“三步走”策略：
            1.  **查找起点**: 接收 `start_output_tree_hash`，查询 `nodes` 表找到对应的 `start_commit_hash`。
            2.  **递归遍历**: 使用 `start_commit_hash` 作为起点，通过递归 CTE 查询 `edges` 表，获取所有祖先的 `commit_hash` 集合。
            3.  **结果转换**: 将上一步得到的 `commit_hash` 集合，通过 `SELECT output_tree FROM nodes WHERE commit_hash IN (...)` 查询，转换为 `output_tree_hash` 集合并返回。

3.  **修改 `GitObjectHistoryReader` 实现**:
    *   **文件**: `packages/quipu-engine/src/quipu/core/git_object_storage.py`
    *   **动作**:
        *   同样更新 `load_all_nodes` 等方法，确保 `QuipuNode.commit_hash` 被正确填充。
        *   修改 `get_node_content`，使其直接使用 `node.commit_hash`，而不是从 `node.filename.name` 解析。

#### 阶段三：逻辑与表现层适配

**目标**：让上层代码使用新的、清晰的 API 和数据模型。

1.  **修改 `GraphViewModel`**:
    *   **文件**: `packages/quipu-cli/src/quipu/cli/view_model.py`
    *   **动作**:
        *   将 `self.current_hash` 重命名为 `self.current_output_tree_hash`。
        *   更新 `initialize` 方法，调用 `self.reader.get_ancestor_output_trees(self.current_output_tree_hash)`。
        *   更新 `is_reachable`，使其接收 `output_tree_hash` 参数。

2.  **修改 `QuipuUiApp`**:
    *   **文件**: `packages/quipu-cli/src/quipu/cli/tui.py`
    *   **动作**:
        *   将 `on_mount` 中获取的 `current_hash` 变量重命名为 `current_output_tree_hash`。
        *   在所有与 `ViewModel` 交互的地方，确保传递的是 `output_tree_hash`。
        *   更新所有从 `node` 对象获取 `commit_hash` 的地方，使其直接访问 `node.commit_hash` 而不是 `node.filename.name`。

3.  **修改 `main.py` CLI 命令**:
    *   **文件**: `packages/quipu-cli/src/quipu/cli/main.py`
    *   **动作**:
        *   在 `checkout` 等命令中，将 `hash_prefix` 的帮助文本明确为“目标状态节点的哈希前缀 (`output_tree`)”。
        *   在命令实现中，将 `target_hash` 等变量重命名为 `target_output_tree_hash`。

#### 阶段四：清理

**目标**：移除所有历史遗留的实现。

1.  **全局代码审查**:
    *   搜索 `node.filename.name` 的用法，确保除了可能的日志记录外，没有任何逻辑依赖于它来获取 `commit_hash`。
    *   搜索 `.split('/')` 或 `.name` 等对 `Path` 对象的操作，确保它们不是为了提取哈希。

通过执行这个计划，我们将一劳永逸地解决标识符模糊的问题，使代码库的意图更加清晰，未来的开发和维护工作将变得更加简单和安全。

```act
end
```
