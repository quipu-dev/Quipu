好的，我们将把刚才的 `chore` 和 `fix` 两个步骤合并为一个原子性的 Git 提交。

## commit: 将默认存储后端切换为 SQLite

### 用户需求
用户要求将 `quipu` 的默认存储后端从 `git_object` 更改为 `sqlite`，因为后者现在已经足够稳定和高效，并提交这些更改。

### 评论
这是一个合理的请求。将默认值更改为 `sqlite` 可以为新用户提供开箱即用的最佳性能。相关的测试用例也已同步更新，以确保代码库的一致性。

### 目标
1.  将 `packages/quipu-engine/src/quipu/core/config.py` 和 `tests/engine/test_config.py` 两个文件的修改添加到 Git 暂存区。
2.  创建一个 Git 提交，清晰地描述本次变更的目的和内容。

### 基本原理
通过 `git_add` 指令将相关文件暂存，然后使用 `git_commit` 指令创建一个包含类型、主题和详细说明的提交。这确保了版本历史的清晰和可追溯性。

### 标签
#intent/tooling #flow/ready #priority/medium #comp/engine #comp/tests #concept/config #scope/dx #ai/instruct

---

### Script

#### Acts 1: 暂存文件并提交

我们将暂存已修改的配置文件和测试文件，并创建一个符合规范的 Git 提交。

~~~~~act
git_add
packages/quipu-engine/src/quipu/core/config.py
tests/engine/test_config.py
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~
chore: Change default storage backend to SQLite

Updates the default configuration to use the `sqlite` backend instead of `git_object`. The SQLite implementation is now stable and offers significantly better performance for history operations, making it a better default choice for new users.

This change also includes updating the corresponding unit test in `test_config.py` to assert the new default value, ensuring the test suite remains consistent with the codebase.
~~~~~

### 下一步建议
代码已提交。我们可以继续进行下一个开发任务。
