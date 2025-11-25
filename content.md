# 🚀 最终阶段: 文档完善与版本固化

我们已经成功构建了 CLI 导航和 TUI 界面。现在，我们将完成最后两项关键任务：
1.  **更新文档**: 全面更新用户文档，详细介绍新的导航命令和 TUI 功能。
2.  **创建最终提交**: 将本次迭代的所有成果（UI、导航命令、文档）合并到一个清晰、有意义的提交中。

---

### 步骤 1: 更新核心概念文档

为了让用户理解 `prev`/`next` 等命令，我们需要在核心概念中阐明 Axon 历史是一个图（DAG），而不仅仅是一条线。

~~~~~act
replace
~~~~~

~~~~~path
docs/03_user_guide/01_core_concepts.md
~~~~~

~~~~~markdown
## 4. 幽灵状态引擎 (Phantom State Engine)

Axon v4.2 引入了革命性的状态管理机制：

*   **State is Truth**: Axon 不维护额外的数据库来记录“当前在哪”。它通过计算当前工作区的 **Git Tree Hash** 来定位。
*   **Lazy Capture**: 在执行新指令前，如果发现环境与历史记录不一致（比如用户手动改了代码），Axon 会自动生成一个 **Capture Node** 来保存当前状态。这意味着你永远不用担心 Axon 会覆盖你未保存的工作。
~~~~~

~~~~~markdown
## 4. 幽灵状态引擎 (Phantom State Engine)

Axon v4.2 引入了革命性的状态管理机制：

*   **State is Truth**: Axon 不维护额外的数据库来记录“当前在哪”。它通过计算当前工作区的 **Git Tree Hash** 来定位。
*   **Lazy Capture**: 在执行新指令前，如果发现环境与历史记录不一致（比如用户手动改了代码），Axon 会自动生成一个 **Capture Node** 来保存当前状态。这意味着你永远不用担心 Axon 会覆盖你未保存的工作。
*   **历史即图谱 (History as a DAG)**: Axon 的历史记录不是一条直线，而是一个**有向无环图 (DAG)**。当你 `checkout` 到一个旧节点并执行新的 Plan 时，就会创建出一个新的分支。这使得无损实验和多方案探索成为可能，也是 `undo`, `redo`, `prev`, `next` 等导航命令的基础。
~~~~~

---

### 步骤 2: 更新 CLI 参考手册

这是最重要的文档更新。我们将添加一个全新的“导航命令”部分和一个“交互式界面”部分。

~~~~~act
append_file
~~~~~

~~~~~path
docs/03_user_guide/02_cli_reference.md
~~~~~

~~~~~markdown

---
## 🧭 导航命令

当历史记录出现分支时，这些命令允许你像在浏览器中前进/后退一样，在历史图谱中轻松穿梭，而无需手动复制哈希值。

| 命令 | 描述 | 示例 |
| :--- | :--- | :--- |
| `axon undo` | 移动到当前节点的**父节点** (类似 Ctrl+Z)。 | `axon undo -n 2` (向上移动2次) |
| `axon redo` | 移动到当前节点的**子节点** (类似 Ctrl+Y)。 | `axon redo` |
| `axon prev` | 在兄弟分支间，切换到**上一个 (更旧的)** 分支。 | `axon prev` |
| `axon next` | 在兄弟分支间，切换到**下一个 (更新的)** 分支。 | `axon next` |

## 📺 交互式界面

### `ui` - 启动 TUI 历史浏览器

提供一个全屏的、可视化的界面来浏览和操作历史图谱。

```bash
axon ui
```

*   **操作**:
    *   使用 `↑` / `↓` 方向键选择节点。
    *   按 `Enter` 或 `c` 键检出 (checkout) 到选中节点。
    *   按 `q` 键退出。
~~~~~

---

### 步骤 3: 更新项目 TODO 列表

我们已经完成了第三阶段的所有目标，让我们在 `TODO.md` 中标记它们！

~~~~~act
replace
~~~~~

~~~~~path
TODO.md
~~~~~

~~~~~markdown
### ➡️ 阶段 3: 用户体验与核心功能 (当前阶段)

当核心循环跑通后，我们将添加让用户能够与历史图谱交互的核心功能。

*   [x] **历史查看 (`axon log`)**
    *   [x] 实现一个新的 CLI 命令 `axon log`，用于列出 `.axon/history` 中的所有节点。
    *   [ ] (可选) 实现 `--graph` 标志，以 TUI 形式可视化历史分支。
*   [x] **时间旅行 (`axon checkout`)**
    *   [x] 实现 CLI 命令 `axon checkout <node_hash>`。
    *   [x] 在 `GitDB` 中添加 `checkout_tree(tree_hash)` 方法，用于将工作区硬重置到指定状态。
*   [x] **工作区重置 (`axon discard`)**
    *   [x] 实现 `axon discard` 命令，用于一键恢复到上一个干净状态，清理失败 Plan 留下的变更。
*   [x] **分布式协作 (`axon sync`)**
    *   [x] 实现 `axon sync` 命令，用于 `git push/pull` `refs/axon/history` 引用。
~~~~~

~~~~~markdown
### ✅ 阶段 3: 用户体验与核心功能 (已完成)

当核心循环跑通后，我们将添加让用户能够与历史图谱交互的核心功能。

*   [x] **历史查看 (`axon log`)**
    *   [x] 实现一个新的 CLI 命令 `axon log`，用于列出 `.axon/history` 中的所有节点。
*   [x] **时间旅行 (`axon checkout`)**
    *   [x] 实现 CLI 命令 `axon checkout <node_hash>`。
    *   [x] 在 `GitDB` 中添加 `checkout_tree(tree_hash)` 方法，用于将工作区硬重置到指定状态。
*   [x] **工作区重置 (`axon discard`)**
    *   [x] 实现 `axon discard` 命令，用于一键恢复到上一个干净状态，清理失败 Plan 留下的变更。
*   [x] **分布式协作 (`axon sync`)**
    *   [x] 实现 `axon sync` 命令，用于 `git push/pull` `refs/axon/history` 引用。
*   [x] **CLI 图导航 (`undo`, `redo`, `prev`, `next`)**
    *   [x] 实现快捷命令，允许在历史图谱中进行相对移动。
*   [x] **交互式 TUI (`axon ui`)**
    *   [x] 集成 Textual，提供一个可视化的历史浏览器和检出工具。
~~~~~

---

### 步骤 4: 创建最终提交

所有代码和文档都已就绪。现在，让我们将这一切作为一个完整的特性进行提交。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~

~~~~~text
feat(ui): 实现交互式 TUI 和 CLI 图导航

本次提交为 Axon 带来了完整的历史图谱交互能力，显著提升了用户体验。

主要更新包括：

- **交互式 TUI**: 新增 `axon ui` 命令，启动一个基于 Textual 的
  全屏界面，允许用户可视化地浏览历史图谱，并一键检出到任意节点。

- **CLI 导航**: 新增 `undo`, `redo`, `prev`, `next` 四个命令，
  实现了在历史图谱中的相对导航，极大地简化了时间旅行操作。

- **核心模型升级**: AxonNode 数据模型已升级，完全支持图结构
  （父、子、兄弟节点），为所有导航功能提供了坚实基础。

- **文档完善**: 全面更新了用户文档，详细介绍了图导航的核心概念、
  新的 CLI 命令以及 TUI 的使用方法。
~~~~~

---

## 🎉 里程碑达成！

我们已经成功完成了从核心数据模型重构，到 CLI 功能实现，再到 TUI 界面开发和文档完善的整个闭环。Axon 现在不仅功能强大，而且更加易于使用。

项目已准备好进入下一个开发阶段！