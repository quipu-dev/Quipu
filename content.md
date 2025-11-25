# refactor: 完成代码中从 Axon 到 Quipu 的品牌重塑

## 目标
创建一个 Git 提交，正式记录从 `Axon` 到 `Quipu` 的全局品牌重塑、测试环境修复以及 Monorepo 开发工作流的建立。

## 基本原理
这个提交标志着阶段性重构的成功完成。它将所有相关的代码修改、配置调整和测试修复作为一个原子性操作，记录到版本历史中。这为项目后续的开发提供了一个干净、稳定且已更名的基线。

## 标签
#refactor #chore #test #build #rebranding

---

## Script

### Act 1: 暂存所有变更

将所有修改过的文件添加到 Git 暂存区，为提交做准备。

~~~~~act
git_add .
~~~~~

### Act 2: 提交代码

创建 Git 提交，固化本次重构的所有成果。

~~~~~act
git_commit
~~~~~

~~~~~
refactor: 完成从 Axon 到 Quipu 的品牌重塑

- 执行了全局的 `axon` 到 `quipu` 的重命名。
- 修复了因命名空间包配置不当导致的 `pytest` 导入错误。
- 配置了顶层 `pyproject.toml` 以支持 monorepo 开发模式 (`pip install -e .`)，统一了开发与测试环境。
~~~~~