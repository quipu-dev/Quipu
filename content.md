你说得对，这个便捷方法在之前的重构中被遗漏了。

这是一个很好的补充，它遵循了 MVVM 的最佳实践：将分页状态管理的逻辑（如页码的增减和边界检查）完全保留在 ViewModel 中，而不是让 View (UI) 层来处理。

我现在就添加它们，以完全遵循设计方案，并简化后续 UI 层的调用。

## feat(cli): 为 ViewModel 添加 next/previous_page 便捷方法

### 用户需求
根据 `99_CURRENT_当前任务.md` 的设计方案，`GraphViewModel` 类应包含 `next_page()` 和 `previous_page()` 两个便捷方法，用于封装分页逻辑。当前实现中缺少这两个方法。

### 评论
这是一个小的功能增强，但它将使 `tui.py` 中的调用代码从 `self._load_page(self.view_model.current_page + 1)` 简化为 `self.view_model.next_page()`，提高了代码的可读性和内聚性。

### 目标
1.  在 `GraphViewModel` 类中添加 `next_page()` 方法。
2.  在 `GraphViewModel` 类中添加 `previous_page()` 方法。
3.  确保这两个方法能正确调用 `load_page()` 并返回节点列表。

### 基本原理
将分页导航的逻辑（“下一页是多少”、“上一页是多少”）封装在 ViewModel 内部，是 MVVM 模式的标准实践。这使得 View 层只负责触发动作和渲染结果，而不关心状态管理的具体实现。

### 标签
#intent/build #flow/ready #priority/high
#comp/cli #concept/ui #scope/api
#ai/instruct
#task/state/continue #task-status/active

---

### Script

#### Acts 1: 向 ViewModel 添加便捷方法

我将使用 `patch_file` 在 `get_content_bundle` 方法之前，为 `GraphViewModel` 类添加 `next_page` 和 `previous_page` 方法。

~~~~~act
patch_file
~~~~~
~~~~~path
packages/quipu-cli/src/quipu/cli/view_model.py
~~~~~
~~~~~python
    def get_content_bundle(self, node: QuipuNode) -> str:
        """
        获取节点的公共内容和私有内容，并将它们格式化成一个单一的字符串用于展示。
        """
~~~~~
~~~~~python
    def previous_page(self) -> List[QuipuNode]:
        """加载上一页的数据。"""
        return self.load_page(self.current_page - 1)

    def next_page(self) -> List[QuipuNode]:
        """加载下一页的数据。"""
        return self.load_page(self.current_page + 1)

    def get_content_bundle(self, node: QuipuNode) -> str:
        """
        获取节点的公共内容和私有内容，并将它们格式化成一个单一的字符串用于展示。
        """
~~~~~

### 下一步建议
现在，`GraphViewModel` 的 API 已经完全符合设计方案。我们可以正式开始**阶段三：前端 UI 适配**，修改 `tui.py`。
