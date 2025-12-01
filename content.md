好的，我们已经完成了代码的修改和验证。现在，我将创建一个 `[COMMIT]` 计划，将这些改进作为一个原子单元提交到版本历史中。

## [COMMIT] feat(cli): 改进 TUI 交互，支持空格检出和纯内容输出

### 用户需求
1.  **快捷键对齐**：将 `quipu ui` 中“检出节点”的快捷键从 `c` 更改为 `space`，以符合 `lazygit` 等工具的通用习惯。
2.  **内容提取优化**：修改“输出内容” (`p` 键) 的功能，使其仅输出选中节点的公共 `content.md` 内容，提供一种干净的“cherry-pick”能力。

### 评论
这个提交通过两个小的用户体验改进，显著提升了 TUI 的可用性和直观性。快捷键的统一降低了用户在不同工具间切换的心智负担，而纯净的内容提取功能则为复用历史计划提供了极大的便利。

### 目标
1.  已将 `pyquipu/cli/tui.py` 中的检出快捷键绑定从 `c` 更改为 `space`。
2.  已在 `pyquipu/cli/view_model.py` 中添加了 `get_public_content` 方法，用于专门提取公共内容。
3.  已更新 `pyquipu/cli/tui.py` 中的 `action_dump_content` 以使用新方法。
4.  将上述变更作为一个完整的特性提交到版本控制。

### 基本原理
通过 `git add` 将相关的两个文件 (`tui.py` 和 `view_model.py`) 添加到暂存区，然后使用 `git commit` 创建一个符合 Conventional Commits 规范的提交，清晰地记录这次功能增强的目的和范围。

### 标签
#intent/build #flow/ready #priority/medium #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-keybindings #task/action/refinement #task/state/end #task/status/completed

---

### Script

#### Acts 1: 暂存并提交变更

我们将把已修改的文件添加到 Git 暂存区，并创建一个内容详尽的提交。

~~~~~act
git_add
packages/quipu-cli/src/pyquipu/cli/tui.py
packages/quipu-cli/src/pyquipu/cli/view_model.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): improve TUI with space-to-checkout and clean content dump

This commit introduces two quality-of-life improvements to the TUI:

1.  **Aligns Checkout Keybinding**: The keybinding for checking out a node in the history viewer (`quipu ui`) is changed from 'c' to 'space'. This aligns with the user experience of popular tools like `lazygit`, reducing friction for users familiar with that ecosystem.

2.  **Refines Content Dump**: The 'dump content' action (triggered by 'p') now only outputs the public plan content (`content.md`) of the selected node. This removes developer-specific metadata (like intent) from the output, providing a clean "cherry-pick" mechanism for reusing historical plans in new contexts or scripts.
~~~~~

### 下一步建议
我们已经成功地改进了 TUI 的交互性。接下来，我们可以考虑以下方向：
*   **TUI 搜索功能**：在 `quipu ui` 中增加一个 `/` 快捷键，允许用户直接在 TUI 内部实时过滤历史节点，而不是退出后使用 `quipu find`。
*   **全面的快捷键审查**：系统地审查 TUI 的所有快捷键，确保它们与 `lazygit`、`tig` 等成熟的 TUI 工具保持最大程度的一致性。
