## [WIP] refactor: 全局替换 Bus 导入路径

### 用户需求
使用 `sed` 将代码库中所有的 `from quipu.bus import bus` 替换为 `from quipu.common.bus import bus`。

### 评论
这是迁移到 `pyneedle-bus` 的第一步代码变更。正如你所预料的，这一步仅仅解决了 `ImportError`，但随之而来将会有大量的 API 兼容性问题暴露出来（即“破坏哪里”）。

最显著的破坏点预计将包括：
1.  **`bus.data()` 缺失**: Needle 的 `FeedbackBus` 没有 `data` 方法，这是 Stitcher/Needle 的设计哲学（数据流 vs 反馈流分离）。Quipu 严重依赖 `bus.data` 输出原始数据（JSON/Diff）。
2.  **`Renderer` 协议不匹配**: `pyquipu-cli/src/quipu/cli/rendering.py` 中的 `TyperRenderer` 实现了旧的接口 (`success`, `info` 等)，而 Needle 期望一个通用的 `render(msg, level, **kwargs)` 方法。
3.  **`bus.get()` 变更**: 旧总线使用 `bus.get(msg_id)` 获取格式化字符串，Needle 使用 `bus.render_to_string(ptr)`。

### 目标
1.  执行批量替换，将指向已删除包 `quipu.bus` 的引用重定向到新位置。
2.  暴露编译/运行时错误，以便后续逐个修复。

### 基本原理
快速失败（Fail Fast）。通过统一替换导入路径，我们可以利用解释器和静态分析工具（或运行测试）迅速定位所有 API 调用不兼容的地方。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #comp/cli #comp/engine #task/domain/ui #task/object/bus #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 执行批量替换

~~~~~act
run_command
~~~~~
~~~~~
grep -rl "from quipu.bus import bus" packages/ | xargs sed -i 's/from quipu.bus import bus/from quipu.common.bus import bus/g'
~~~~~

### 下一步建议

执行完上述操作后，建议立即运行测试或静态检查（如果可用），或者简单地尝试运行 `quipu` 命令。

为了修复即将到来的破坏，我们需要按以下顺序行动：
1.  **重构 Renderer**: 修改 `TyperRenderer` 以适配 Needle 的 `RendererProtocol`。
2.  **实现 `bus.data`**: 由于 `FeedbackBus` 没有 data 通道，我们需要决定是：
    *   (A) 在 `quipu.common.bus` 中子类化 `FeedbackBus` 并添加 `data` 方法（最快路径）。
    *   (B) 遵循 Needle 哲学，分离数据输出通道（例如直接 print 到 stdout 或使用专门的 DataBus）。考虑到 Quipu 的 CLI 性质，方案 A 可能更平滑。
3.  **修复 `bus.get`**: 全局搜索 `bus.get` 并替换为 `bus.render_to_string`。
