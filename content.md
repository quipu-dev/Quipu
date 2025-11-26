# chore: 提交核心解耦重构

## 用户需求
用户确认了之前的重构方案已完成并通过测试，需要将这些变更提交到版本控制中。

## 评论
这次提交固化了重要的架构改进，将 `cli`, `engine`, 和 `runtime` 之间的强耦合关系解除了，为未来的扩展和维护提供了更好的基础。

## 目标
将所有已修改和新增的文件暂存，并创建一个符合 `Conventional Commits` 规范的提交，以记录本次重构。

## 基本原理
使用 `git_add` 指令暂存所有变更，然后使用 `git_commit` 指令创建一个带有明确信息的提交。提交类型为 `refactor`，因为它主要是为了改善内部结构，并未添加新功能或修复外部可见的 bug。

## 标签
#intent/tooling #flow/ready #priority/high
#comp/cli #comp/engine #comp/runtime
#scope/core
#ai/instruct

---

## Script

### Acts 1: 提交变更

现在，我们将暂存所有文件变更，并创建一个描述本次重构的 Git 提交。

~~~~~act
git_add .
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~
refactor: Decouple CLI from Engine and Runtime internals

本次重构解决了 CLI 层与核心模块之间的强耦合问题，提升了系统的模块化、可测试性和可扩展性。

主要变更包括：
-   **配置驱动的工厂**: `factory.py` 中的 `create_engine` 现在根据配置选择存储后端，移除了对 `GitObjectHistory` 的硬编码依赖。
-   **插件管理器**: 插件加载逻辑被封装到新的 `PluginManager` 类中，使 `controller` 的职责更单一。
-   **应用层封装**: 核心业务流程从过程式的 `run_quipu` 函数重构为面向对象的 `QuipuApplication` 类，更好地封装了“感知-行动-记录”的循环。
-   **通用工具**: 提取了通用的 `find_project_root` 函数，减少了代码重复。
~~~~~
