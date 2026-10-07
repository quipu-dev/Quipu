import difflib
import logging
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quipu.spec.exceptions import ExecutionError, OperationCancelledError
from quipu.spec.protocols.runtime import ActContext, ActFunction, Statement

logger = logging.getLogger(__name__)


# 定义确认处理器的签名: (diff_lines: List[str], prompt_message: str) -> bool
ConfirmationHandler = Callable[[list[str], str], bool]
DataHandler = Callable[[str], None]


class Executor:
    def __init__(
        self,
        root_dir: Path,
        yolo: bool = False,
        confirmation_handler: ConfirmationHandler | None = None,
        data_handler: DataHandler | None = None,
    ):
        self.root_dir = root_dir.resolve()
        self.yolo = yolo
        self.confirmation_handler = confirmation_handler
        self.data_handler = data_handler
        # Map: name -> (func, arg_mode, summarizer)
        self._acts: dict[str, tuple[ActFunction, str, Any]] = {}

        if not self.root_dir.exists():
            try:
                self.root_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.warning(f"无法创建根目录 {self.root_dir}: {e}")

    def output_data(self, data_string: str) -> None:
        if self.data_handler:
            self.data_handler(data_string)
        else:
            sys.stdout.write(data_string + ("\n" if not data_string.endswith("\n") else ""))

    def register(self, name: str, func: ActFunction, arg_mode: str = "hybrid", summarizer: Any = None):
        valid_modes = {"hybrid", "exclusive", "block_only"}
        if arg_mode not in valid_modes:
            raise ValueError(f"Invalid arg_mode: {arg_mode}. Must be one of {valid_modes}")

        self._acts[name] = (func, arg_mode, summarizer)
        logger.debug(f"注册 Act: {name} (Mode: {arg_mode})")

    def get_registered_acts(self) -> dict[str, str]:
        return {name: data[0].__doc__ or "No documentation." for name, data in self._acts.items()}

    def summarize_statement(self, stmt: Statement) -> str | None:
        raw_act_line = stmt["act"]
        try:
            tokens = shlex.split(raw_act_line)
        except ValueError:
            return None

        if not tokens:
            return None

        act_name = tokens[0]
        inline_args = tokens[1:]
        contexts = stmt["contexts"]

        if act_name not in self._acts:
            return None

        _, _, summarizer = self._acts[act_name]

        if not summarizer:
            return None

        try:
            return summarizer(inline_args, contexts)
        except Exception as e:
            # Summarizer 失败不应影响主流程，仅记录日志
            logger.warning(f"Summarizer for '{act_name}' failed: {e}")
            return None

    def resolve_path(self, rel_path: str) -> Path:
        clean_rel = rel_path.strip()
        abs_path = (self.root_dir / clean_rel).resolve()

        if not str(abs_path).startswith(str(self.root_dir)):
            raise ExecutionError(f"安全警告：路径 '{clean_rel}' 试图访问工作区外部: {abs_path}")

        return abs_path

    def request_confirmation(self, file_path: Path, old_content: str, new_content: str):
        if self.yolo:
            return

        diff = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{file_path.name}",
                tofile=f"b/{file_path.name}",
            )
        )

        if not diff:
            logger.debug(f"文件内容无变化，跳过修改: {file_path.name}")
            return

        if not self.confirmation_handler:
            logger.warning(f"缺少确认处理器，跳过需确认的操作: {file_path.name}")
            raise OperationCancelledError("未配置确认处理器。")

        prompt = f"❓ 是否对 {file_path.name} 执行上述修改?"
        self.confirmation_handler(diff, prompt)

    def execute(self, statements: list[Statement]):
        logger.debug(f"正在开始执行 {len(statements)} 个操作...")

        ctx = ActContext(self)

        for i, stmt in enumerate(statements):
            raw_act_line = stmt["act"]
            block_contexts = stmt["contexts"]

            try:
                tokens = shlex.split(raw_act_line)
            except ValueError as e:
                raise ExecutionError(f"解析 Act 命令行出错: {raw_act_line} ({e})")

            if not tokens:
                logger.warning(f"跳过空指令 [{i + 1}/{len(statements)}]")
                continue

            act_name = tokens[0]
            inline_args = tokens[1:]

            if act_name not in self._acts:
                logger.warning(f"跳过未知操作 [{i + 1}/{len(statements)}]: {act_name}")
                continue

            func, arg_mode, _ = self._acts[act_name]

            final_args = []
            if arg_mode == "hybrid":
                final_args = inline_args + block_contexts
            elif arg_mode == "exclusive":
                if inline_args:
                    final_args = inline_args
                    if block_contexts:
                        logger.debug(f"[{act_name} - Exclusive] 检测到行内参数，忽略后续 {len(block_contexts)} 个块。")
                else:
                    final_args = block_contexts
            elif arg_mode == "block_only":
                if inline_args:
                    logger.warning(f"[{act_name}] 模式为 block_only，已忽略行内参数: {inline_args}")
                final_args = block_contexts

            try:
                logger.debug(
                    f"正在执行 [{i + 1}/{len(statements)}]: {act_name} (模式: {arg_mode}, 参数数: {len(final_args)})"
                )
                func(ctx, final_args)
            except OperationCancelledError:
                raise
            except ExecutionError:
                raise
            except Exception as e:
                logger.error(f"执行 '{act_name}' 时发生异常: {e}")
                raise ExecutionError(f"执行 '{act_name}' 时出错: {e}") from e
