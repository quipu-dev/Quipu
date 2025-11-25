# chore: 创建提交

## 评论
代码修改已完成，现在将其固化到版本历史中。

## 标签
#comp/cli

---

## Script

### Acts 1: 提交 TUI 内容预览功能

~~~~~act
git_add packages/quipu-cli/ tests/
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(cli): Implement TUI content preview and extraction

- Adds a split-view mode to the TUI, toggled with 'v', to display the content of the selected history node.
- The right-hand panel renders the node's Markdown content, providing immediate context without leaving the UI.
- Adds a 'dump' feature, bound to 'p', which prints the selected node's content to stdout, allowing for piping to other tools.
- Refactors the TUI and CLI main entrypoint to support lazy-loading of node content, improving initial UI startup performance.
- Updates UI tests to accommodate the new constructor signature.
- The node info/summary column is now always visible, even in split-view, to maximize information density.
~~~~~

---

### 下一步展望：优化预览性能

你说得对，当前预览的性能在快速导航时确实存在延迟。这是因为每次光标移动，我们都会同步地从磁盘读取文件内容并重新渲染，这会阻塞 UI 的响应。

为了解决这个问题，我建议下一步实施 **“异步加载与内容缓存”** 机制。

**基本原理：**

1.  **异步加载 (Asynchronous Loading)**：当用户选中一个新节点时，我们不再立即阻塞主线程去读文件，而是启动一个后台工作线程 (Worker) 来执行这个 I/O 操作。在加载完成前，预览面板可以显示一个 “Loading...” 的提示。这样即使用户快速滚动，UI 界面本身也能保持流畅。
2.  **内容缓存 (Content Caching)**：在 App 内部维护一个字典，用于缓存已经加载过一次的节点内容。当用户再次选中同一个节点时，我们直接从内存缓存中读取，避免了不必要的磁盘 I/O，实现内容的瞬时加载。

这个优化将显著提升 TUI 的使用体验，使其在浏览大型历史记录时也能保持丝滑流畅。
