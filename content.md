好的，重构脚本已执行完毕。我们将这些变更作为一个完整的逻辑单元提交到历史记录中。

[COMMIT] 计划将把所有受影响的文件添加到 Git 暂存区并创建提交。

## [COMMIT] refactor: 迁移 bus 消息 ID 至 L 指针

### 用户需求
正式提交将字符串形式的消息 ID 重构为 `needle.pointer.L` 对象的变更。

### 评论
此次提交涉及 `quipu-cli`、`quipu-runtime` 和 `quipu-engine` 等多个组件，是提升系统类型安全性的关键一步。通过 Git 提交，我们锁定了这一架构改进。

### 目标
1.  将所有被脚本修改的 Python 文件添加到 Git 暂存区。
2.  创建一个清晰、描述性的 Git 提交。

### 基本原理
遵循 `d3-constraint-quipu-plan-script-rules`，在独立的文件修改计划之后进行 Git 操作，确保变更被正确验证和记录。使用 `L` 指针不仅是语法糖，它标志着系统向更加严格、自文档化的方向演进。

### 标签
#intent/refine #flow/ready #priority/medium #comp/cli #comp/runtime #comp/engine #concept/ui #scope/dx #ai/instruct #task/domain/tech-debt #task/object/l-pointer #task/action/refactor #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交变更
将所有重构后的文件加入暂存区并创建提交。

~~~~~act
git_add
.
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
refactor: migrate bus message IDs from strings to L pointer

This commit replaces all string-literal message IDs used in 'bus.info', 'bus.error', etc., with 'needle.pointer.L' semantic pointers.

Benefits:
- Enables IDE autocomplete and refactoring support for message IDs.
- Provides a centralized, type-safe way to manage UI messages.
- Removes "magic strings" from business and CLI logic.

Modified files throughout the monorepo to include 'from needle.pointer import L' and updated bus calls accordingly.
~~~~~

### 下一步建议
- **同步测试断言**: 下一步可以考虑将测试用例中的 `mock_bus.info.assert_called_with("string.id")` 也同步重构为 `mock_bus.info.assert_called_with(L.string.id)`，以保持测试代码与生产代码的一致性。
- **ID 发现工具**: 随着 `L` 的引入，我们可以构建一个简单的静态分析工具，自动提取系统中所有使用的 `L` 指针路径，从而自动生成 I18N 资产模板（`.yaml` 文件），确保没有任何 ID 遗漏翻译。
