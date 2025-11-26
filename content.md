# chore: 提交已完成的 ViewModel 阶段

### 用户需求
根据 `Quipu UI 性能优化与功能增强执行方案`，我们已经完成了数据层 (`HistoryReader`) 和逻辑层 (`GraphViewModel`) 的准备工作。

下一步是执行 **阶段三：前端 UI 适配 (View Layer)**，将 `quipu-cli/src/quipu/cli/tui.py` 中的 `QuipuUiApp` 与新创建的 `GraphViewModel` 对接，以实现按需加载和性能提升。

### 评论
这是整个重构任务的核心部分。通过这次改造，`QuipuUiApp` 将从一个简单的、展示静态列表的组件，转变为一个响应式的、能处理动态数据流的视图控制器。这将从根本上解决 UI 的性能瓶颈，并为展示私有数据等新功能铺平道路。

### 目标
此计划的目标是对 `tui.py` 进行一系列精确的修改，使其完全依赖 `GraphViewModel` 来获取数据和状态，具体包括：

1.  **修改 `QuipuUiApp` 的构造函数**：不再接收节点列表，而是接收 `GraphViewModel` 实例。
2.  **实现无限滚动**：在 `on_mount` 时加载第一页数据，并在用户滚动到底部时异步加载后续页面。
3.  **适配渲染逻辑**：使用 `ViewModel` 提供的方法来判断节点是否可达 (`is_reachable`) 以及获取节点的详细内容 (`get_content_bundle`)。

### 基本原理
我们将把所有与数据状态和加载逻辑相关的代码从 `tui.py` 中移除，并替换为对 `GraphViewModel` 实例的方法调用。UI 组件 (`QuipuUiApp`) 将变得更“轻”，只负责响应用户输入（滚动、高亮）和渲染 `ViewModel` 提供的数据。这种关注点分离的模式将使 UI 代码更易于理解和维护。

### 标签
#intent/refactor #flow/ready #priority/high
#comp/cli #concept/ui #scope/ux
#ai/instruct
#task/domain/ui #task/object/performance #task/action/refactor
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 提交已完成的 ViewModel 阶段

此操作将把 `GraphViewModel` 及其测试文件提交到版本控制中，为下一阶段的工作创建一个干净的起点。

~~~~~act
git_add packages/quipu-cli/src/quipu/cli/view_model.py tests/test_view_model.py
~~~~~
~~~~~act
git_commit
~~~~~
~~~~~text
refactor(cli): Introduce GraphViewModel to decouple UI and data layers

This commit introduces the `GraphViewModel` class, which serves as a crucial intermediate layer between the `HistoryReader` (Model) and the `QuipuUiApp` (View).

Key responsibilities of the ViewModel:
- Encapsulates pagination logic (`load_next_page`).
- Manages total item count and loading state (`initialize`, `has_more_data`).
- Caches reachability information (`ancestor_set`) by leveraging backend queries, avoiding the need to load the entire graph in the UI.
- Consolidates public and private content fetching (`get_content_bundle`).

This architectural change is the cornerstone of the UI performance optimization effort, enabling "infinite scroll" and lazy loading of data. Corresponding unit tests have been added to ensure the ViewModel's logic is robust before UI integration.
~~~~~
