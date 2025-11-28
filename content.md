你的观察非常敏锐，这确实是一个非常微妙但在高性能 UI 中常见的问题。

**原因分析：**
你看到的“先显示旧内容，再显示新内容”的现象，是因为 `Markdown` 组件的 `update()` 操作是**异步**的。
1.  当防抖定时器触发时，我们调用 `markdown_widget.update(new_content)`。
2.  紧接着，我们设置 `markdown_widget.display = True`。
3.  **关键点**：`Textual` 可能会在 `Markdown` 组件完成新内容的解析和渲染**之前**，就先处理了 `display = True` 的指令。
4.  结果就是：组件变得可见了，但缓冲区里还是**上一次**渲染的内容（旧节点）。一瞬间后，新内容的渲染完成，界面才刷新变成新节点。这就是你看到的“闪烁”或“覆盖”。

**关于“两次渲染开销”：**
如果不处理，确实存在一种认知上的“双重视觉更新”（旧->新）。虽然计算层面上 `update` 只调了一次，但视觉层面上用户被迫处理了两次信息变化，体验不好。

**解决方案：**
在隐藏组件时（即用户开始滚动、离开当前节点时），显式清空 `Markdown` 组件的内容。
这样做有两个好处：
1.  **消除重影**：当组件再次显示时，即使新内容还没渲染好，它也是空白的，而不是显示误导性的旧内容。
2.  **释放内存**：清空大文本有助于 Python 的垃圾回收，特别是当历史记录中包含大文件时。

解析空字符串 `""` 的开销是可以忽略不计的，所以这不会引入性能问题。

## [WIP] fix: TUI 切换节点时的旧内容残留问题 (Ghosting)

### 错误分析
在防抖加载机制中，`Markdown` 组件的 `update(content)` 是异步执行的。当我们在回调中紧接着调用 `display = True` 时，组件可能在内部状态尚未更新完毕的情况下就被渲染到了屏幕上，导致展示了上一次的旧内容（Ghosting）。这给用户造成了视觉干扰和“双重加载”的错觉。

### 用户需求
1.  消除在加载新节点内容时，旧节点内容一闪而过的现象。
2.  确保每次内容视图出现时，要么是新的内容，要么是空白，绝不能是过期的内容。

### 评论
这是一个涉及 UI 渲染时序的细节优化。通过“离开即销毁”的策略，我们可以保证视图状态的纯洁性。

### 目标
在 `on_row_highlighted` 方法中，当我们将 `Markdown` 组件设为 `display = False` (隐藏) 时，立即调用 `markdown_widget.update("")` 将其内容清空。

### 基本原理
利用 `Markdown` 解析器处理空字符串极快的特性，在用户离开节点的瞬间“擦除”旧数据。这样，下一次 `_debounced_update_content_view` 将组件设为可见时，即使存在渲染延迟，用户也只会看到空白背景变为新内容，而不是旧内容变为新内容。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #concept/ui #scope/ux
#ai/brainstorm
#task/domain/ui #task/object/tui-performance #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 在隐藏 Markdown 组件时清空内容

我们将修改 `packages/quipu-cli/src/quipu/cli/tui.py`。

~~~~~act
patch_file
packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
            placeholder_text = "*Loading...*"
            placeholder_widget.update(placeholder_text)
            
            placeholder_widget.display = True
            markdown_widget.display = False

            # Schedule the expensive update
            self.update_timer = self.set_timer(self.debounce_delay_seconds, self._debounced_update_content_view)
~~~~~
~~~~~python
            placeholder_text = "*Loading...*"
            placeholder_widget.update(placeholder_text)
            
            placeholder_widget.display = True
            markdown_widget.display = False
            # Clear old content immediately to prevent "ghosting" when reappearing
            markdown_widget.update("")

            # Schedule the expensive update
            self.update_timer = self.set_timer(self.debounce_delay_seconds, self._debounced_update_content_view)
~~~~~

### 下一步建议
至此，针对 TUI 性能和体验的一系列优化（防抖、静态占位符、消除重影）均已完成。

建议步骤：
1.  验证修改：再次运行 `quipu ui`，快速切换节点，确认“旧内容一闪而过”的现象消失。
2.  **提交代码**：由于我们已经通过多个 WIP 步骤解决了整个问题链，现在可以生成最终的 `[COMMIT]` 计划来合并所有变更。你需要我生成这个 Commit 计划吗？
