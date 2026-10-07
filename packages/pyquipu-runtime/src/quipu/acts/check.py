import logging
import os
from pathlib import Path

from quipu.spec.protocols.runtime import ActContext
from quipu.spec.protocols.runtime import ExecutorProtocol as Executor

logger = logging.getLogger(__name__)


def register(executor: Executor):
    executor.register("check_files_exist", _check_files_exist, arg_mode="exclusive")
    executor.register("check_cwd_match", _check_cwd_match, arg_mode="exclusive")


def _check_files_exist(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("check_files_exist 需要至少 1 个参数: [file_list_string]")

    raw_files = args[0].strip().split("\n")
    missing_files = []

    for raw_path in raw_files:
        clean_path = raw_path.strip()
        if not clean_path:
            continue

        target_path = ctx.resolve_path(clean_path)
        if not target_path.exists():
            missing_files.append(clean_path)

    if missing_files:
        file_list_str = "\n".join(f"  - {f}" for f in missing_files)
        ctx.fail(f"以下文件在工作区中未找到:\n{file_list_str}")


def _check_cwd_match(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("check_cwd_match 需要至少 1 个参数: [expected_absolute_path]")

    expected_path_str = args[0].strip()
    current_root = ctx.root_dir.resolve()
    expected_path = Path(os.path.expanduser(expected_path_str)).resolve()

    if current_root != expected_path:
        ctx.fail(f"工作区目录不匹配!\n  预期: {expected_path}\n  实际: {current_root}")
