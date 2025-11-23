## 🚀 Axon v4.2 开发路线图

### ✅ 阶段 1: 幽灵引擎内核 (已完成)

这是 v4.2 架构中最复杂、最核心的部分。我们已经构建并验证了一个功能完备的状态引擎地基。

*   [x] **Git 数据库接口 (`core/git_db.py`)**
    *   [x] 实现零污染的影子索引 (`shadow_index`)
    *   [x] 实现精确的状态指纹计算 (`get_tree_hash`)
    *   [x] 实现历史保活机制 (`create_anchor_commit`, `update_ref`)
    *   [x] 实现 Git 血统检测 (`is_ancestor`)
*   [x] **数据模型与历史加载器 (`core/models.py`, `core/history.py`)**
    *   [x] 定义 `AxonNode` 数据结构
    *   [x] 实现从文件系统加载历史图谱 (`load_history_graph`)
*   [x] **核心状态机逻辑 (`core/engine.py`)**
    *   [x] 实现 `align` 方法，可准确识别 `CLEAN`, `DIRTY`, `ORPHAN` 状态
    *   [x] 实现 `capture_drift` 方法，可自动将漂移状态固化为 `CaptureNode`
*   [x] **测试驱动开发 (TDD)**
    *   [x] 完整的单元测试覆盖了 `GitDB` 和 `Engine` 的所有核心功能

---

### ➡️ 阶段 2: 集成与运行时 (当前阶段)

这是我们**当前**需要专注的阶段。目标是将强大的 `Engine` 与用户可见的 `CLI` 和 `Executor` 连接起来，形成完整的“感知-行动”循环。

*   [ ] **CLI 与引擎集成 (`main.py`)**
    *   [ ] 在 `main.py` 启动时实例化 `Engine`。
    *   [ ] 调用 `engine.align()` 获取当前状态。
*   [ ] **实现核心生命周期**
    *   [ ] **处理 `DIRTY` 状态**：如果在执行 Plan 之前检测到 `DIRTY`，自动调用 `engine.capture_drift()`。
    *   [ ] **处理 `ORPHAN` 状态**：如果是首次运行，执行一个“创世捕获”（Genesis Capture），为项目历史奠定第一个基石。
*   [ ] **实现 Plan 节点生成**
    *   [ ] 在 `Executor` **成功执行完**所有 `acts` 后，计算新的 `output_tree_hash`。
    *   [ ] 为 `Engine` 添加一个 `create_plan_node(...)` 方法。
    *   [ ] 调用该方法，将本次执行的 Plan 固化为一个新的 `PlanNode`，并更新 Git 引用。
*   [ ] **端到端测试**
    *   [ ] 编写一个新的集成测试，模拟 `axon run plan.md` 的完整流程，验证 Capture 和 Plan 节点是否都按预期生成。

---

### 🧠 阶段 3: 用户体验与核心功能

当核心循环跑通后，我们将添加让用户能够与历史图谱交互的核心功能。

*   [ ] **历史查看 (`axon log`)**
    *   [ ] 实现一个新的 CLI 命令 `axon log`，用于列出 `.axon/history` 中的所有节点。
    *   [ ] (可选) 实现 `--graph` 标志，以 TUI 形式可视化历史分支。
*   [ ] **时间旅行 (`axon checkout`)**
    *   [ ] 实现 CLI 命令 `axon checkout <node_hash>`。
    *   [ ] 在 `GitDB` 中添加 `checkout_tree(tree_hash)` 方法，用于将工作区硬重置到指定状态。
*   [ ] **分布式协作 (`axon sync`)**
    *   [ ] 实现 `axon sync` 命令，用于 `git push/pull` `refs/axon/history` 引用。

---

### 🛠️ 阶段 4: 健壮性与打磨

让 Axon 从一个原型变成一个可靠的工具。

*   [ ] **完善错误处理**：处理 `git` 未安装、权限不足、Plan 执行失败等情况。
*   [ ] **配置系统**：允许用户通过 `.axon/config.yml` 自定义行为。
*   [ ] **文档更新**：更新 `README.md` 和 `PROMPT.md`，反映 v4.2 的新概念和工作流。
*   [ ] **打包与分发**：为 `pip` 发布做准备。

---

## 我们现在在哪？

我们已经成功完成了 **阶段 1**。

可以把 Axon v4.2 想象成一辆高性能赛车。我们刚刚用最顶级的材料和工艺，精心打造并测试了它的**引擎缸体、活塞和传动轴 (`Engine` 和 `GitDB`)**。它动力澎湃，且经过了严格的台架测试，证明了其设计的正确性和性能的可靠性。

**我们现在正处于阶段 2**。我们的任务是，将这个强大的引擎安装进赛车的底盘，并连接上**方向盘 (`CLI`)**、**油门和刹车 (`Executor`)**。只有这样，赛车手（用户/AI）才能真正地驾驶它在赛道上飞驰。

我们的下一个，也是**唯一**的焦点，是完成**阶段 2：集成与运行时**，实现从用户输入到状态变更的完整闭环。
