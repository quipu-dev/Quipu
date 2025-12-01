好的，这是一个很好的用户体验改进建议。将常用操作的快捷键与 `lazygit` 等工具对齐，并提供更具针对性的内容提取功能，可以显著提升 TUI 的实用性。

我将生成一个计划来实现这两项改动。

## [WIP] feat(cli): 改进 TUI 交互，支持空格检出和纯内容输出

### 用户需求
1.  **修改 TUI 快捷键**：将历史记录 TUI (`quipu ui`) 中“检出节点” (checkout) 的快捷键从 `c` 改为 `space` (空格键)，以符合 `lazygit` 等常用 TUI 工具的用户习惯。
2.  **优化内容输出功能**：修改“输出内容” (`p` 键) 的行为，使其仅输出选中节点的公共计划内容 (`content.md`)，而不是包含开发者意图等信息的完整内容包。这提供了一种“cherry-pick”单个计划内容的能力。

### 评论
这是一个有价值的微调。统一的快捷键可以降低用户的学习成本和心智负担，而更纯粹的内容输出功能则为从历史中提取可复用计划提供了便利，增强了 Quipu 作为知识库和代码片段管理器的潜力。

### 目标
1.  在 `pyquipu/cli/tui.py` 中，更新 `BINDINGS` 列表，将 `c` 键的绑定修改为 `space`。
2.  在 `pyquipu/cli/view_model.py` 中，添加一个新方法 `get_public_content`，专门用于获取节点的 `content.md` 内容。
3.  在 `pyquipu/cli/tui.py` 中，修改 `action_dump_content` 方法，使其调用新的 `get_public_content` 方法。

### 基本原理
我们将在 TUI 的绑定定义中直接修改快捷键。对于内容输出，为了保持良好的分层架构（视图不直接与数据读取器交互），我们将在 `GraphViewModel` 中添加一个新方法来封装获取纯公共内容的逻辑。TUI 层将调用这个新方法，从而实现所需的功能，同时保持代码的清晰和可维护性。

### 标签
#intent/build #flow/ready #priority/medium #comp/cli #concept/ui #scope/ux #ai/instruct #task/domain/ui #task/object/tui-keybindings #task/action/refinement #task/state/begin

---

### Script

#### Acts 1: 更新 TUI 快捷键和动作

我们将修改 `tui.py` 文件，首先更新按键绑定，然后调整 `action_dump_content` 的实现。

~~~~~act
patch_file
packages/quipu-cli/src/pyquipu/cli/tui.py
~~~~~
~~~~~python
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("v", "toggle_view", "切换内容视图"),
~~~~~
~~~~~python
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("space", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("v", "toggle_view", "切换内容视图"),
~~~~~

~~~~~act
patch_file
packages/quipu-cli/src/pyquipu/cli/tui.py
~~~~~
~~~~~python
    def action_dump_content(self) -> None:
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            content = self.view_model.get_content_bundle(selected_node)
            self.exit(result=("dump", content))
~~~~~
~~~~~python
    def action_dump_content(self) -> None:
        selected_node = self.view_model.get_selected_node()
        if selected_node:
            content = self.view_model.get_public_content(selected_node)
            self.exit(result=("dump", content))
~~~~~

#### Acts 2: 在 ViewModel 中添加新的内容获取方法

现在，我们在 `view_model.py` 中添加 `get_public_content` 方法，为 TUI 提供所需的数据接口。

~~~~~act
patch_file
packages/quipu-cli/src/pyquipu/cli/view_model.py
~~~~~
~~~~~python
    def get_selected_node(self) -> Optional[QuipuNode]:
        return self.current_selected_node

    def previous_page(self) -> List[QuipuNode]:
~~~~~
~~~~~python
    def get_selected_node(self) -> Optional[QuipuNode]:
        return self.current_selected_node

    def get_public_content(self, node: QuipuNode) -> str:
        """
        仅获取节点的公共内容 (content.md)。
        """
        return self.reader.get_node_content(node) or ""

    def previous_page(self) -> List[QuipuNode]:
~~~~~

### 下一步建议
代码修改已完成。建议运行 `qd ui` 进入开发环境的 TUI，亲自验证以下行为：
1.  在历史图谱中，按下空格键是否能触发“检出节点”的退出行为。
2.  选中一个有内容的节点，按下 `p` 键退出后，检查终端的标准输出是否只包含了该节点的 `content.md` 内容，不再有“开发者意图”等额外信息。
