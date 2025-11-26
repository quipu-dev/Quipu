# chore: 创建提交以固化 SQLite 读取路径功能

## 用户需求
在实现 SQLite 读取路径并为其补充了单元测试后，所有测试均已通过。现在需要将这些变更创建一个 Git 提交，以正式将其纳入版本历史。

## 评论
这是一个标准的开发流程。创建一个原子性的、描述清晰的提交，有助于代码的追溯和维护。该提交将标志着“SQLite 后端集成”这一宏观任务的完成。

## 目标
使用 `git` 指令，将所有已修改和新增的文件（包括 `SQLiteHistoryReader` 的实现、工厂函数的更新以及新的测试文件）暂存并提交。

## 基本原理
我们将使用 `git_add` 指令来暂存所有变更，然后使用 `git_commit` 指令附带一个详细的、遵循约定式提交规范的提交信息来创建提交。该提交信息将全面总结本次系列变更的目的、实现方式和影响。

## 标签
#intent/tooling #flow/done
#comp/engine #comp/cli #comp/tests
#scope/core
#ai/instruct
#task/domain/storage
#task/object/sqlite-backend
#task/action/integration
#task/state/end
#task/status/completed

---

## Script

### Acts 1: 提交代码

此操作将暂存所有当前变更，并创建一个包含详细说明的 Git 提交。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
feat(engine): 激活 SQLite 读取路径以提升性能

本次提交完成了 SQLite 升级计划的核心部分，将系统的历史记录读取逻辑切换到了 SQLite 后端，旨在解决 UI 和 CLI 查询的性能瓶颈。

主要变更包括：

1.  **实现 `SQLiteHistoryReader`**:
    - 在 `quipu-engine` 中新增了 `SQLiteHistoryReader`，它直接从数据库的 `nodes` 和 `edges` 表中加载图谱元数据，极大地提升了 `quipu ui` 和 `quipu log` 的启动速度。
    - 实现了“通读缓存 (Read-Through Cache)”策略。节点内容按需从 Git 加载，并自动回填到数据库的 `plan_md_cache` 字段，确保后续访问的高性能。

2.  **工厂函数集成**:
    - 更新了 `quipu-cli` 中的 `create_engine` 工厂函数。当检测到 `storage.type` 配置为 `sqlite` 时，系统将自动实例化并使用新的 `SQLiteHistoryReader`。

3.  **补充单元测试**:
    - 新增 `tests/test_sqlite_reader.py`，为 `SQLiteHistoryReader` 添加了专门的单元测试，确保其图谱构建逻辑和通读缓存机制的正确性。
~~~~~
