import logging
import os
import subprocess

from quipu.spec.protocols.runtime import ActContext
from quipu.spec.protocols.runtime import ExecutorProtocol as Executor

logger = logging.getLogger(__name__)


def register(executor: Executor):
    executor.register("git_init", _git_init, arg_mode="exclusive")
    executor.register("git_add", _git_add, arg_mode="exclusive")
    executor.register("git_commit", _git_commit, arg_mode="block_only", summarizer=_summarize_commit)
    executor.register("git_status", _git_status, arg_mode="exclusive")


def _summarize_commit(args: list[str], contexts: list[str]) -> str:
    msg = contexts[0] if contexts else "No message"
    summary = (msg[:50] + "...") if len(msg) > 50 else msg
    return f"Git Commit: {summary}"


def _run_git_cmd(ctx: ActContext, cmd_args: list[str]) -> str:
    env = os.environ.copy()
    env["LC_ALL"] = "C"

    try:
        result = subprocess.run(
            ["git"] + cmd_args, cwd=ctx.root_dir, capture_output=True, text=True, check=True, env=env
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip()
        ctx.fail(f"Git 命令执行失败: git {' '.join(cmd_args)}\n错误信息: {error_msg}")
    except FileNotFoundError:
        ctx.fail("未找到 git 命令，请确保系统已安装 Git。")
    return ""


def _git_init(ctx: ActContext, args: list[str]):
    if (ctx.root_dir / ".git").exists():
        logger.debug("Git 仓库已存在，跳过初始化。")
        return
    _run_git_cmd(ctx, ["init"])


def _git_add(ctx: ActContext, args: list[str]):
    targets = []
    if not args:
        targets = ["."]
    else:
        for arg in args:
            targets.extend(arg.split())
    if not targets:
        targets = ["."]
    _run_git_cmd(ctx, ["add"] + targets)


def _git_commit(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("git_commit 需要至少 1 个参数: [message]")

    message = args[0]

    status = _run_git_cmd(ctx, ["status", "--porcelain"])
    if not status:
        logger.debug("没有暂存的更改，跳过提交。")
        return

    ctx.request_confirmation(ctx.root_dir / ".git", "Staged Changes", f"Commit Message: {message}")

    _run_git_cmd(ctx, ["commit", "-m", message])


def _git_status(ctx: ActContext, args: list[str]):
    status = _run_git_cmd(ctx, ["status"])
    ctx.data(status)
