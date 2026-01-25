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

# 定义 ConfirmationHandler 类型别名: (diff_lines, prompt) -> bool
# 注意: Executor 期望如果不确认则抛出异常，或者返回 False (取决于 Executor 实现)。
# 为了保持与 CLI 行为一致，调用方传入的 handler 应该在用户拒绝时抛出 OperationCancelledError。
ConfirmationHandler = Callable[[List[str], str], bool]


class QuipuApplication:
    def __init__(self, work_dir: Path, confirmation_handler: ConfirmationHandler, yolo: bool = False):
        self.work_dir = work_dir
        self.confirmation_handler = confirmation_handler
        self.yolo = yolo
        self.engine: Engine = create_engine(work_dir)
        logger.info(f"Operation boundary set to: {self.work_dir}")

    def _prepare_workspace(self) -> str:
        current_hash = self.engine.git_db.get_tree_hash()

        # 1. 正常 Clean: current_node 存在且与当前 hash 一致
        is_node_clean = (self.engine.current_node is not None) and (
            self.engine.current_node.output_tree == current_hash
        )

        # 2. 创世 Clean: 历史为空 且 当前是空树 (即没有任何文件被追踪)
        EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        is_genesis_clean = (not self.engine.history_graph) and (current_hash == EMPTY_TREE_HASH)

        is_clean = is_node_clean or is_genesis_clean

        if not is_clean:
            self.engine.capture_drift(current_hash)

        if self.engine.current_node:
            return self.engine.current_node.output_tree
        else:
            return current_hash

    def _setup_executor(self) -> Executor:
        executor = Executor(
            root_dir=self.work_dir,
            yolo=self.yolo,
            confirmation_handler=self.confirmation_handler,
        )

        # 加载核心 acts
        register_core_acts(executor)

        # 加载外部插件
        plugin_manager = PluginManager()
        plugin_manager.load_from_sources(executor, self.work_dir)

        return executor

    def checkout_by_tree_hash_prefix(self, tree_hash_prefix: str, force: bool = False) -> QuipuResult:
        graph = self.engine.history_graph
        matches = [node for node in graph.values() if node.output_tree.startswith(tree_hash_prefix)]

        if not matches:
            return QuipuResult(
                success=False,
                exit_code=1,
                message="navigation.checkout.error.notFound",
                msg_kwargs={"hash_prefix": tree_hash_prefix},
            )
        if len(matches) > 1:
            return QuipuResult(
                success=False,
                exit_code=1,
                message="navigation.checkout.error.notUnique",
                msg_kwargs={"hash_prefix": tree_hash_prefix, "count": len(matches)},
            )

        target_node = matches[0]
        target_output_tree_hash = target_node.output_tree
        current_hash = self.engine.git_db.get_tree_hash()

        if current_hash == target_output_tree_hash:
            return QuipuResult(
                success=True,
                exit_code=0,
                message="navigation.checkout.info.noAction",
                msg_kwargs={"short_hash": target_node.short_hash},
            )

        is_dirty = self.engine.current_node is None or self.engine.current_node.output_tree != current_hash
        if is_dirty:
            # Here we need a message bus to inform the user.
            # For now, we rely on the CLI to have a bus configured.
            # A better solution would involve passing the bus into the app.
            # bus.warning("navigation.checkout.info.capturingDrift")
            self.engine.capture_drift(current_hash)
            # bus.success("navigation.checkout.success.driftCaptured")
            current_hash = self.engine.git_db.get_tree_hash()

        diff_stat_str = self.engine.git_db.get_diff_stat(current_hash, target_output_tree_hash)

        if not self.yolo and not force:
            # Re-create prompt here as we don't have access to the bus directly yet.
            # This highlights a future improvement area.
            prompt = (
                f"将工作区检出到快照 {target_node.short_hash} ({target_node.timestamp}) "
                f"会覆盖当前未保存的变更。"
            )
            try:
                self.confirmation_handler(diff_stat_str.splitlines(), prompt)
            except OperationCancelledError:
                raise  # Re-raise to be caught by the top-level handler

        self.engine.visit(target_output_tree_hash)
        return QuipuResult(
            success=True,
            exit_code=0,
            message="navigation.success.visit",
            msg_kwargs={"short_hash": target_output_tree_hash[:7]},
        )

    def run(self, content: str, parser_name: str) -> QuipuResult:
        # --- Phase 1 & 2: Perception & Decision (Lazy Capture) ---
        input_tree_hash = self._prepare_workspace()

        # --- Phase 3: Action (Execution) ---
        # 3.1 Parser
        final_parser_name = parser_name
        if parser_name == "auto":
            final_parser_name = detect_best_parser(content)
            if final_parser_name != "backtick":
                logger.info(f"🔍 自动检测到解析器: {final_parser_name}")

        parser = get_parser(final_parser_name)
        statements = parser.parse(content)

        if not statements:
            return QuipuResult(
                success=True,  # No failure, just nothing to do
                exit_code=0,
                message="axon.warning.noStatements",
                msg_kwargs={"parser": final_parser_name},
            )

        # 3.2 Executor Setup
        executor = self._setup_executor()

        # 3.3 Execute
        executor.execute(statements)

        # --- Phase 4: Recording (Plan Crystallization) ---
        final_summary = None
        # 优先级 1: 从 Markdown 内容中提取 # 标题
        title_match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
        if title_match:
            final_summary = title_match.group(1).strip()
        # 优先级 2: 从第一个 act 指令生成摘要
        elif statements:
            final_summary = executor.summarize_statement(statements[0])

        output_tree_hash = self.engine.git_db.get_tree_hash()

        self.engine.create_plan_node(
            input_tree=input_tree_hash,
            output_tree=output_tree_hash,
            plan_content=content,
            summary_override=final_summary,
        )

        return QuipuResult(success=True, exit_code=0, message="run.success")


def run_quipu(
    content: str,
    work_dir: Path,
    confirmation_handler: ConfirmationHandler,
    parser_name: str = "auto",
    yolo: bool = False,
) -> QuipuResult:
    app = None
    try:
        app = QuipuApplication(work_dir=work_dir, confirmation_handler=confirmation_handler, yolo=yolo)
        return app.run(content=content, parser_name=parser_name)

    except OperationCancelledError as e:
        logger.info(f"🚫 操作已取消: {e}")
        return QuipuResult(
            success=False, exit_code=2, message="run.error.cancelled", msg_kwargs={"error": str(e)}, error=e
        )

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
    finally:
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
