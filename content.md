很好。我们继续沿着这条正确的道路前进。

将 `axon` 的核心逻辑迁移到 `application` 层，将彻底净化 CLI 代码，使其成为一个纯粹的、符合 HFEA 原则的“意图翻译器”。它将不再关心业务流程的“如何做”，只关心“做什么”。

我将生成一个计划，用两个精确的 `patch_file` 操作完成这次重构。

## [WIP] refactor: 将 axon 执行流程迁移到 application 层

### 用户需求

将 `quipu axon` 命令的主执行流程，从 CLI 层（`commands/axon.py`）完整地迁移到一个新的、位于 `application` 层的服务函数 `run_stateless_plan` 中。

### 评论

这是本次重构的核心。通过这次迁移，我们将在 `application` 层建立一个清晰、可独立测试的无状态服务。CLI 层将彻底转变为该服务的瘦客户端 (thin client)，这使得架构边界变得如水晶般清晰，极大地提升了系统的可维护性和可测试性。

### 目标

1.  在 `pyquipu.application.controller` 中创建新的 `run_stateless_plan` 函数。
2.  此函数将完整封装：`Executor` 初始化、插件加载、解析器选择、内容解析、指令执行以及异常处理的全过程。
3.  `run_stateless_plan` 必须返回一个标准的 `QuipuResult` 对象，作为其与调用方（CLI）之间的稳定契约。
4.  重构 `axon` 命令，移除所有业务逻辑，使其仅负责：解析参数、读取输入、调用 `run_stateless_plan`，并根据返回的 `QuipuResult` 渲染最终的用户反馈。

### 基本原理

我们正在应用**命令查询责任分离 (CQRS)** 的一个变体和**应用服务模式**。`run_stateless_plan` 是一个封装了完整业务用例的“命令处理器”。它接收一个命令（包含执行所需的所有数据），并返回一个结果。CLI 层作为表示层，其唯一职责是将用户的交互翻译成这个命令，并将结果呈现出来。这种分离是构建健壮、可演进系统的基石，完全符合 HFEA 的**严格分层与边界**原则。

### 标签

#intent/refine #flow/ready #priority/high #comp/cli #comp/application #scope/core #scope/dx #ai/instruct #task/domain/cli #task/object/axon-command #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 在 `controller.py` 中创建 `run_stateless_plan` 服务

我们将 `axon.py` 中复杂的执行逻辑整体迁移到 `controller.py` 中，并将其封装在一个新的、独立的函数里。这个函数将拥有清晰的输入和输出，不依赖任何 CLI 特定的组件。

~~~~~act
patch_file
packages/pyquipu-application/src/pyquipu/application/controller.py
~~~~~
~~~~~python.old
        # 确保无论成功或失败，引擎资源都被关闭
        if app and hasattr(app, "engine") and app.engine:
            app.engine.close()
~~~~~
~~~~~python.new
        # 确保无论成功或失败，引擎资源都被关闭
        if app and hasattr(app, "engine") and app.engine:
            app.engine.close()


def run_stateless_plan(
    content: str,
    work_dir: Path,
    confirmation_handler: ConfirmationHandler,
    parser_name: str = "auto",
    yolo: bool = False,
) -> QuipuResult:
    """
    Executes a plan in a stateless manner, bypassing the Quipu engine.

    This function sets up a temporary executor, loads plugins, parses the content,
    and executes the statements against the specified working directory.

    Args:
        content: The string content of the plan to execute.
        work_dir: The root directory for the execution.
        confirmation_handler: A callable to handle user confirmations.
        parser_name: The name of the parser to use ('auto' by default).
        yolo: If True, skips all confirmation prompts.

    Returns:
        A QuipuResult object indicating the outcome of the execution.
    """
    try:
        executor = Executor(
            root_dir=work_dir,
            yolo=yolo,
            confirmation_handler=confirmation_handler,
        )
        register_core_acts(executor)
        PluginManager().load_from_sources(executor, work_dir)

        final_parser_name = parser_name
        if parser_name == "auto":
            final_parser_name = detect_best_parser(content)

        parser = get_parser(final_parser_name)
        statements = parser.parse(content)

        if not statements:
            return QuipuResult(
                success=True,
                exit_code=0,
                message="axon.warning.noStatements",
                msg_kwargs={"parser": final_parser_name},
            )

        executor.execute(statements)
        return QuipuResult(success=True, exit_code=0, message="axon.success")

    except CoreExecutionError as e:
        logger.error(f"❌ 操作失败: {e}")
        return QuipuResult(
            success=False, exit_code=1, message="run.error.execution", msg_kwargs={"error": str(e)}, error=e
        )
    except Exception as e:
        logger.error(f"运行时错误: {e}", exc_info=True)
        return QuipuResult(
            success=False, exit_code=1, message="run.error.system", msg_kwargs={"error": str(e)}, error=e
        )
~~~~~

#### Acts 2: 简化 `axon` 命令，使其成为应用服务的客户端

现在 `application` 层已经提供了强大的服务，我们可以将 `axon.py` 大幅简化。它现在只负责处理用户输入和渲染结果，完全不再关心执行的细节。

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/axon.py
~~~~~
~~~~~python.old
        logger.debug(f"axon started with file={file}, work_dir={work_dir}, parser={parser_name}, yolo={yolo}")

        # 1. 初始化无状态 Executor, 复用 controller 中的标准确认处理器
        # 注意：这里不初始化 Engine，因此没有历史记录功能
        executor = Executor(
            root_dir=work_dir,
            yolo=yolo,
            confirmation_handler=confirmation_handler_for_executor,
        )
        register_core_acts(executor)

        # 3. 加载插件
        # PluginManager 会尝试查找 Git 根目录加载项目级插件，如果找不到 Git 根目录则跳过，符合无状态设计
        PluginManager().load_from_sources(executor, work_dir)

        # 5. 获取输入内容 (文件 或 STDIN 或 默认文件)
        content = ""
        source_desc = ""
        if file:
            if not file.exists():
                bus.error("common.error.fileNotFound", path=file)
                ctx.exit(1)
            content = file.read_text(encoding="utf-8")
            source_desc = f"文件 ({file.name})"
        elif not sys.stdin.isatty():
            try:
                stdin_content = sys.stdin.read()
                if stdin_content:
                    content = stdin_content
                    source_desc = "STDIN (管道流)"
            except Exception:
                pass

        # 如果没有指定文件且没有 STDIN，尝试读取当前目录下的默认入口文件 (如 o.md)
        if not content and not file and DEFAULT_ENTRY_FILE.exists():
            content = DEFAULT_ENTRY_FILE.read_text(encoding="utf-8")
            source_desc = f"默认文件 ({DEFAULT_ENTRY_FILE.name})"

        if not content.strip():
            bus.warning("axon.warning.noInput")
            ctx.exit(0)

        logger.info(f"Axon 启动 | 源: {source_desc} | 工作区: {work_dir}")

        # 6. 解析
        final_parser_name = parser_name
        if parser_name == "auto":
            final_parser_name = detect_best_parser(content)

        try:
            parser = get_parser(final_parser_name)
            statements = parser.parse(content)

            if not statements:
                bus.warning("axon.warning.noStatements", parser=final_parser_name)
                ctx.exit(0)

            # 7. 执行
            executor.execute(statements)
            bus.success("axon.success")

        except ExecutionError as e:
            bus.error("axon.error.executionFailed", error=str(e))
            ctx.exit(1)
        except ValueError as e:
            logger.error(f"无效的参数或配置: {e}", exc_info=True)
            bus.error("common.error.invalidConfig", error=str(e))
            ctx.exit(1)
        except Exception as e:
            logger.error(f"未预期的系统错误: {e}", exc_info=True)
            bus.error("common.error.generic", error=str(e))
            ctx.exit(1)
~~~~~
~~~~~python.new
        logger.debug(f"axon started with file={file}, work_dir={work_dir}, parser={parser_name}, yolo={yolo}")

        # --- 1. 输入处理 (CLI 层职责) ---
        content = ""
        source_desc = ""
        if file:
            if not file.exists():
                bus.error("common.error.fileNotFound", path=file)
                ctx.exit(1)
            content = file.read_text(encoding="utf-8")
            source_desc = f"文件 ({file.name})"
        elif not sys.stdin.isatty():
            try:
                stdin_content = sys.stdin.read()
                if stdin_content:
                    content = stdin_content
                    source_desc = "STDIN (管道流)"
            except Exception:
                pass

        if not content and not file and DEFAULT_ENTRY_FILE.exists():
            content = DEFAULT_ENTRY_FILE.read_text(encoding="utf-8")
            source_desc = f"默认文件 ({DEFAULT_ENTRY_FILE.name})"

        if not content.strip():
            bus.warning("axon.warning.noInput")
            ctx.exit(0)

        # --- 2. 委托给应用层服务 (核心重构) ---
        from pyquipu.application.controller import run_stateless_plan

        logger.info(f"Axon 启动 | 源: {source_desc} | 工作区: {work_dir}")

        result = run_stateless_plan(
            content=content,
            work_dir=work_dir,
            parser_name=parser_name,
            yolo=yolo,
            confirmation_handler=confirmation_handler_for_executor,
        )

        # --- 3. 渲染结果 (CLI 层职责) ---
        if result.message:
            kwargs = result.msg_kwargs or {}
            if result.exit_code == 2:
                bus.warning(result.message, **kwargs)
            elif not result.success:
                bus.error(result.message, **kwargs)
            else:
                bus.success(result.message, **kwargs)

        ctx.exit(result.exit_code)
~~~~~

### 下一步建议

我们已经成功地将两个无状态的关注点（`list-acts` 和 `axon` 执行）从 CLI 层完全剥离，并固化为 `application` 层的稳定服务。

现在，架构中最主要的边界模糊问题集中在那些**有状态**的 CLI 命令上（如 `checkout`, `log`, `save`, `discard` 等），它们仍然直接与 `engine` 交互。

我提议，下一步我们将这些命令的逻辑逐一迁移为 `QuipuApplication` 类的方法。例如，创建一个 `QuipuApplication.checkout_node(hash_prefix: str) -> QuipuResult` 方法，并将 `checkout.py` 中的逻辑移入其中。这将是实现完全分层的最后一步。
