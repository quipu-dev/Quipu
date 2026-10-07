import logging
import subprocess

from quipu.spec.protocols.runtime import ActContext
from quipu.spec.protocols.runtime import ExecutorProtocol as Executor

logger = logging.getLogger(__name__)


def register(executor: Executor):
    executor.register("run_command", _run_command, arg_mode="exclusive")


def _run_command(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("run_command 需要至少 1 个参数: [command_string]")

    command = "\n".join(args)

    warning_msg = f"⚠️  即将执行系统命令:\n  $ {command}\n  (CWD: {ctx.root_dir})"
    ctx.request_confirmation(ctx.root_dir, "System State", warning_msg)

    logger.debug(f"正在执行: {command}")

    try:
        result = subprocess.run(command, cwd=ctx.root_dir, shell=True, capture_output=True, text=True)
    except Exception as e:
        ctx.fail(f"Shell 执行异常: {e}")
        return

    if result.stdout:
        ctx.data(result.stdout.strip())
    if result.stderr:
        logger.warning(f"Shell 命令输出到 stderr:\n{result.stderr.strip()}")

    if result.returncode != 0:
        ctx.fail(f"命令执行失败 (Code {result.returncode})")
