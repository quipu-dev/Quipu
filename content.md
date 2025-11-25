# chore-commit 提交核心修复与增强

## 目标
将关于 HEAD 指针同步 (`fix-head-sync`) 和根目录发现 (`fix-core`) 的修复提交到版本控制系统中。

## 基本原理
这些变更是对核心状态管理逻辑的重要修复，确保了 Axon/Quipu 在子目录运行和执行检出操作时的行为正确性。

## 标签
#chore #git

---

## Script

### Act 1: 提交变更

将所有修改过的核心文件和新增的测试文件添加到暂存区并提交。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~

~~~~~message
fix(core): 修复 HEAD 指针同步与根目录发现机制

1. 增强 Root Discovery:
   - 将 `_find_project_root` 提升为 `find_project_root` 公共方法。
   - 在 CLI 入口强制执行根目录解析，支持从子目录运行命令。

2. 修复 HEAD 指针同步:
   - 在 Engine 中引入 `.axon/HEAD` 读写逻辑。
   - 在 `checkout` 和 `discard` 操作中通过 `engine.checkout` 统一更新 HEAD。
   - 修复了捕获漂移 (Capture Drift) 时因缺失 HEAD 导致的历史断连问题。

3. 测试:
   - 新增 `tests/test_head_and_root.py` 覆盖相关场景。
~~~~~