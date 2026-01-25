好的，我们开始。

根据我们的共识，第一步是将重复的 `--list-acts` 逻辑提取到 `application` 层，以解决 DRY 违规和分层不清的问题。这将是我们后续更深层次重构的基石。

我将生成一个计划，通过三个原子化的 `patch` 操作，精确地完成这次重构。

## [WIP] refactor: 将 'list-acts' 逻辑集中到 application 层

### 用户需求

根据代码审核结果，将 `run` 和 `axon` 命令中重复的 `--list-acts` 功能逻辑提取并集中到 `application` 层，以消除代码重复并改善架构分层。

### 评论

这是一个非常好的起点。这个重构不仅能解决明显的 DRY 违规，还能为 `application` 层建立一个清晰的“无状态服务”模式，为后续将更多业务逻辑从 `cli` 层迁移出来铺平道路。

### 目标

1.  在 `pyquipu.application.controller` 模块中创建一个新的、独立的、无状态的函数 `get_available_acts(work_dir: Path)`。
2.  将初始化 `Executor`、注册核心 `acts`、以及加载插件以发现所有可用 `acts` 的逻辑完全封装在此新函数中。
3.  重构 `quipu run --list-acts` 命令，使其调用这个新的应用层服务函数来获取数据，自身只负责渲染。
4.  重构 `quipu axon --list-acts` 命令，同样调用新的服务函数，并确保此逻辑在命令的顶层，以便能快速执行并退出。

### 基本原理

我们将在 `application` 层创建一个新的公共服务函数，作为“发现可用操作”的唯一真实来源 (Single Source of Truth)。`cli` 层的两个命令将不再关心如何发现 `acts`，它们只作为此服务的客户端，负责调用并展示结果。这严格遵循了 HFEA 协议中的**严格分层**和**真理单一来源 (SSoT)** 原则，是迈向架构**不可腐蚀性**的关键一步。

### 标签

#intent/refine #flow/ready #priority/high #comp/cli #comp/application #scope/dx #ai/instruct #task/domain/cli #task/object/list-acts #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 在 application 层创建服务函数

首先，我们在 `controller.py` 中添加 `get_available_acts` 函数。我将把它放在模块的顶部，并添加所有必要的导入，使其成为一个独立的、可重用的服务。

~~~~~act
patch_file
packages/pyquipu-application/src/pyquipu/application/controller.py
~~~~~
~~~~~python.old
import logging
import re
from pathlib import Path
from typing import Callable, List

from pyquipu.acts import register_core_acts
from pyquipu.engine.state_machine import Engine
from pyquipu.interfaces.exceptions import ExecutionError as CoreExecutionError
from pyquipu.interfaces.exceptions import OperationCancelledError
from pyquipu.interfaces.result import QuipuResult
from pyquipu.runtime.executor import Executor
from pyquipu.runtime.parser import detect_best_parser, get_parser

from .factory import create_engine
from .plugin_manager import PluginManager

logger = logging.getLogger(__name__)
~~~~~
~~~~~python.new
import logging
import re
from pathlib import Path
from typing import Callable, Dict, List

from pyquipu.acts import register_core_acts
from pyquipu.engine.state_machine import Engine
from pyquipu.interfaces.exceptions import ExecutionError as CoreExecutionError
from pyquipu.interfaces.exceptions import OperationCancelledError
from pyquipu.interfaces.result import QuipuResult
from pyquipu.runtime.executor import Executor
from pyquipu.runtime.parser import detect_best_parser, get_parser

from .factory import create_engine
from .plugin_manager import PluginManager

logger = logging.getLogger(__name__)


def get_available_acts(work_dir: Path) -> Dict[str, str]:
    """
    Statelessly discovers and returns all available acts.

    This function initializes a temporary, stateless executor to discover
    core acts and acts from plugins found relative to the working directory.

    Args:
        work_dir: The directory from which to discover project-level plugins.

    Returns:
        A dictionary mapping act names to their docstrings.
    """
    # A dummy confirmation handler is used as it's not required for listing.
    # Yolo=True ensures no interactive prompts can be triggered.
    executor = Executor(
        root_dir=work_dir,
        yolo=True,
        confirmation_handler=lambda diff, prompt: True,
    )
    register_core_acts(executor)
    PluginManager().load_from_sources(executor, work_dir)
    return executor.get_registered_acts()
~~~~~

#### Acts 2: 重构 `run` 命令

现在，我们更新 `run.py`，移除其内部的 `Executor` 初始化逻辑，转而调用我们刚刚创建的 `get_available_acts` 服务。

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/run.py
~~~~~
~~~~~python.old
        setup_logging()
        if list_acts:
            from pyquipu.acts import register_core_acts
            from pyquipu.application.plugin_manager import PluginManager

            executor = Executor(root_dir=work_dir, yolo=True)
            register_core_acts(executor)
            PluginManager().load_from_sources(executor, work_dir)

            bus.info("run.listActs.ui.header")
            acts = executor.get_registered_acts()
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("run.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)
~~~~~
~~~~~python.new
        setup_logging()
        if list_acts:
            from pyquipu.application.controller import get_available_acts

            bus.info("run.listActs.ui.header")
            acts = get_available_acts(work_dir)
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("run.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)
~~~~~

#### Acts 3: 重构 `axon` 命令

最后，我们用同样的方式重构 `axon.py`。我将 `--list-acts` 的处理逻辑移到函数顶部，这样它就可以作为一个独立的查询功能立即返回，而不会干扰后面为实际执行准备 `Executor` 的主流程。

~~~~~act
patch_file
packages/pyquipu-cli/src/pyquipu/cli/commands/axon.py
~~~~~
~~~~~python.old
    ):
        setup_logging()
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

        # 4. 处理 --list-acts
        if list_acts:
            bus.info("axon.listActs.ui.header")
            acts = executor.get_registered_acts()
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("axon.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)

        # 5. 获取输入内容 (文件 或 STDIN 或 默认文件)
~~~~~
~~~~~python.new
    ):
        setup_logging()

        # --list-acts 是一个独立的查询操作，应尽早处理并退出
        if list_acts:
            from pyquipu.application.controller import get_available_acts

            bus.info("axon.listActs.ui.header")
            acts = get_available_acts(work_dir)
            for name in sorted(acts.keys()):
                doc = acts[name]
                clean_doc = inspect.cleandoc(doc) if doc else "暂无说明"
                indented_doc = "\n".join(f"   {line}" for line in clean_doc.splitlines())
                item_header = bus.get("axon.listActs.ui.actItem", name=name)
                bus.data(f"{item_header}\n{indented_doc}\n")
            ctx.exit(0)

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
~~~~~

### 下一步建议

我们已经成功地将第一个关注点从 CLI 层剥离到了 Application 层。现在，`--list-acts` 功能既健壮又符合架构原则。

下一步，我建议我们继续这个势头，将 `axon` 命令的主执行流程也迁移到 `application` 层的一个新服务函数中（例如 `run_stateless_plan`）。这将彻底净化 `axon.py`，使其成为一个纯粹的“意图翻译器”，符合我们追求的**高保真工程**标准。
