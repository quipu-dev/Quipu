# refactor 实施运行时层 (Runtime Definition) 物理隔离

## 目标
将负责指令解析、执行和插件加载的运行时逻辑与核心模块物理隔离。通过重命名文件和更新引用，明确 `core/rt_*` 模块作为无状态执行单元的边界。

## 基本原理
此操作属于 Quipu 重构计划的 **步骤 1.3**。
当前 `executor.py`、`parser.py` 和 `plugin_loader.py` 位于 `core/` 根层级，容易与状态管理逻辑 (`engine`) 混淆。通过增加 `rt_` 前缀，我们在文件系统层面强制实施了“运行时层”的命名空间隔离，并为后续迁移到 `packages/quipu-runtime` 做准备。

## 标签
 #refactor #runtime #core

---

## Script

### Act 1: 重命名运行时核心文件

将 `executor`、`parser` 和 `plugin_loader` 重命名为带有 `rt_` 前缀的版本。

~~~~~act
move_file core/executor.py core/rt_executor.py
~~~~~

~~~~~act
move_file core/parser.py core/rt_parser.py
~~~~~

~~~~~act
move_file core/plugin_loader.py core/rt_plugin_loader.py
~~~~~