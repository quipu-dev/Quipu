## [WIP] fix: 修正 `run --list-acts` 未加载插件的问题

### 错误分析
`quipu run --list-acts` 命令的实现存在缺陷。它在初始化 `Executor` 后仅注册了核心 `act` (`register_core_acts`)，但并未调用 `PluginManager` 来加载项目本地或用户全局的外部插件。这导致 `-l` 的输出不完整，遗漏了所有通过插件机制添加的 `act`。

相比之下，`quipu axon --list-acts` 的实现是正确的，它在列出 `act` 之前会调用 `PluginManager().load_from_sources(executor, work_dir)`。

### 用户需求
修复 `quipu run --list-acts` 命令，使其能够正确地发现并列出所有可用的 `act`，包括核心 `act` 和所有通过插件加载的 `act`。

### 评论
这是一个重要的开发者体验 (DX) 修复。`--list-acts` 是一个关键的自省功能，它的不一致性会给用户带来困惑。统一 `run` 和 `axon` 在此功能上的行为，可以确保工具的可靠性和可预测性。

### 目标
1.  修改 `packages/quipu-cli/src/pyquipu/cli/commands/run.py` 文件。
2.  在 `run_command` 函数处理 `--list-acts` 的逻辑块中，加入对 `PluginManager` 的调用。

### 基本原理
我们将把 `axon.py` 中处理插件加载和列出的逻辑范式，完整地复制到 `run.py` 中。这确保了无论用户通过哪个命令查询可用操作，都能得到一致且完整的结果。

### 标签
#intent/fix #flow/ready #priority/medium #comp/cli #concept/executor #scope/dx #ai/instruct #task/domain/cli #task/object/act-listing #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `run.py` 中的 `list_acts` 逻辑

我们将使用 `patch_file` 来替换 `run.py` 中不完整的逻辑块。

~~~~~act
patch_file
~~~~~
~~~~~path
packages/quipu-cli/src/pyquipu/cli/commands/run.py
~~~~~
~~~~~python
        setup_logging()
        if list_acts:
            executor = Executor(root_dir=Path("."), yolo=True)
            from pyquipu.acts import register_core_acts

            register_core_acts(executor)
            bus.info("run.listActs.ui.header")
            acts = executor.get_registered_acts()
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                bus.info("run.listActs.ui.actItem", name=name)
                bus.data(f"{indented_doc}\n")
            ctx.exit(0)
~~~~~
~~~~~python
        setup_logging()
        if list_acts:
            from pyquipu.acts import register_core_acts
            from ..plugin_manager import PluginManager

            executor = Executor(root_dir=work_dir, yolo=True)
            register_core_acts(executor)
            PluginManager().load_from_sources(executor, work_dir)

            bus.info("run.listActs.ui.header")
            acts = executor.get_registered_acts()
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                bus.info("run.listActs.ui.actItem", name=name)
                bus.data(f"{indented_doc}\n")
            ctx.exit(0)
~~~~~

### 下一步建议
1.  **测试修复**: 在 `dev` 环境 (`qd`) 中运行 `qd run -l`，确认 `bump_version` 和 `set_version` 现在已经出现在列表中。
2.  **提交变更**: 如果测试通过，你可以创建一个 `[COMMIT]` 计划来将这个修复持久化。

---

分析得很好。这是一个非常经典的场景，问题不在于你新创建的插件，而在于**调用它的工具链**。

### 根本原因

`quipu run --list-acts` 命令的实现中存在一个**缺陷**：它在列出 `act` 时，**只加载并显示了核心 `act`，而没有调用插件管理器来加载外部插件**（例如你刚刚创建的 `versioning.py`）。

与此同时，`quipu axon --list-acts` 的实现是**正确**的，它会先加载核心 `act`，然后再加载所有插件，最后再列出完整的 `act` 列表。

### 代码分析

我们可以通过对比两个命令的源代码来清晰地看到这一点：

1.  **有缺陷的实现 (`packages/quipu-cli/src/pyquipu/cli/commands/run.py`)**:
    ```python
    # ... inside run_command ...
    if list_acts:
        executor = Executor(root_dir=Path("."), yolo=True)
        from pyquipu.acts import register_core_acts

        register_core_acts(executor) # <--- 只注册了核心 acts
        bus.info("run.listActs.ui.header")
        acts = executor.get_registered_acts() # <--- 直接获取列表，没有加载插件
        # ... a for loop to print acts ...
        ctx.exit(0)
    ```
    如上所示，这段代码在 `register_core_acts` 之后，直接就去获取和打印 `act` 列表了，完全遗漏了加载插件的步骤。

2.  **正确的实现 (`packages/quipu-cli/src/pyquipu/cli/commands/axon.py`)**:
    ```python
    # ... inside axon_command ...
    executor = Executor(
        root_dir=work_dir,
        yolo=yolo,
        confirmation_handler=confirmation_handler_for_executor,
    )
    register_core_acts(executor)

    # 3. 加载插件
    # PluginManager 会尝试查找 Git 根目录加载项目级插件...
    PluginManager().load_from_sources(executor, work_dir) # <--- 正确地调用了插件管理器

    # 4. 处理 --list-acts
    if list_acts:
        bus.info("axon.listActs.ui.header")
        acts = executor.get_registered_acts() # <--- 在加载插件后获取列表
        # ... a for loop to print acts ...
        ctx.exit(0)
    ```
    `axon` 的实现遵循了正确的“注册核心 -> 加载插件 -> 列出”的顺序。

### 环境验证

这个分析导出了一个可以直接验证的推论：如果你运行 `qs axon -l`，你应该能看到你新创建的 `bump_version` 和 `set_version` 命令。插件加载器 (`PluginManager`) 是根据当前工作目录 (`.`) 来查找 `.quipu/acts` 的，所以即使是 `qs` (稳定版) 也能找到你本地的插件。

请试着运行 `qs axon -l`，它应该会列出所有 `act`。

### 解决方案

我们需要修复 `run.py` 中 `--list-acts` 的逻辑，使其与 `axon.py` 的行为保持一致。

