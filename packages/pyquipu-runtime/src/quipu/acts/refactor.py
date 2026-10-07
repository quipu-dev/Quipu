import logging
import shutil

from quipu.spec.protocols.runtime import ActContext
from quipu.spec.protocols.runtime import ExecutorProtocol as Executor

logger = logging.getLogger(__name__)


def register(executor: Executor):
    executor.register("move_file", _move_file, arg_mode="hybrid")
    executor.register("delete_file", _delete_file, arg_mode="exclusive")


def _move_file(ctx: ActContext, args: list[str]):
    if len(args) < 2:
        ctx.fail("move_file 需要至少 2 个参数: [src, dest]")

    src_raw, dest_raw = args[0], args[1]
    src_path = ctx.resolve_path(src_raw)
    dest_path = ctx.resolve_path(dest_raw)

    if not src_path.exists():
        ctx.fail(f"源文件不存在: {src_raw}")

    msg = f"Move: {src_raw} -> {dest_raw}"
    ctx.request_confirmation(src_path, "Source Exists", msg)

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dest_path))
    except PermissionError:
        ctx.fail(f"移动/重命名失败: 权限不足。源: '{src_raw}', 目标: '{dest_raw}'")
    except Exception as e:
        ctx.fail(f"移动/重命名时发生未知错误: {e}")


def _delete_file(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("delete_file 需要至少 1 个参数: [path]")

    raw_path = args[0]
    target_path = ctx.resolve_path(raw_path)

    if not target_path.exists():
        logger.debug(f"文件不存在，跳过删除: {raw_path}")
        return

    file_type = "目录 (递归删除!)" if target_path.is_dir() else "文件"
    warning = f"🚨 正在删除{file_type}: {target_path}"

    ctx.request_confirmation(target_path, "EXISTING CONTENT", warning)

    try:
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
    except PermissionError:
        ctx.fail(f"删除失败: 对 '{raw_path}' 的访问权限不足。")
    except Exception as e:
        ctx.fail(f"删除时发生未知错误: {e}")
