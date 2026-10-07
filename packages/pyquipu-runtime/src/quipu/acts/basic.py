import logging

from quipu.spec.protocols.runtime import ActContext
from quipu.spec.protocols.runtime import ExecutorProtocol as Executor

logger = logging.getLogger(__name__)


def register(executor: Executor):
    executor.register("write_file", _write_file, arg_mode="hybrid", summarizer=_summarize_write)
    executor.register("patch_file", _patch_file, arg_mode="hybrid", summarizer=_summarize_patch_file)
    executor.register("append_file", _append_file, arg_mode="hybrid", summarizer=_summarize_append)
    executor.register("end", _end, arg_mode="hybrid")
    executor.register("echo", _echo, arg_mode="hybrid")


def _summarize_write(args: list[str], contexts: list[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"Write: {path}"


def _summarize_patch_file(args: list[str], contexts: list[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"patch_file in: {path}"


def _summarize_append(args: list[str], contexts: list[str]) -> str:
    path = args[0] if args else (contexts[0] if contexts else "???")
    return f"Append to: {path}"


def _end(ctx: ActContext, args: list[str]):
    pass


def _echo(ctx: ActContext, args: list[str]):
    if len(args) < 1:
        ctx.fail("echo 需要至少 1 个参数: [content]")

    ctx.data(args[0])


def _write_file(ctx: ActContext, args: list[str]):
    if len(args) < 2:
        ctx.fail("write_file 需要至少 2 个参数: [path, content]")

    raw_path = args[0]
    content = args[1]

    target_path = ctx.resolve_path(raw_path)

    old_content = ""
    if target_path.exists():
        try:
            old_content = target_path.read_text(encoding="utf-8")
        except Exception:
            old_content = "[Binary or Unreadable]"

    ctx.request_confirmation(target_path, old_content, content)

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
    except PermissionError:
        ctx.fail(f"写入文件失败: 对 '{raw_path}' 的访问权限不足。")
    except Exception as e:
        ctx.fail(f"写入文件时发生未知错误: {e}")


def _patch_file(ctx: ActContext, args: list[str]):
    if len(args) < 3:
        ctx.fail("patch_file 需要至少 3 个参数: [path, old_string, new_string]")

    raw_path, old_str, new_str = args[0], args[1], args[2]
    target_path = ctx.resolve_path(raw_path)

    if not target_path.exists():
        ctx.fail(f"文件未找到: {raw_path}")

    try:
        content = target_path.read_text(encoding="utf-8")
    except Exception as e:
        ctx.fail(f"读取文件 {raw_path} 失败: {e}")

    match_count = content.count(old_str)
    if match_count == 0:
        ctx.fail(f"在文件 {raw_path} 中未找到指定的旧文本。\n请确保 Markdown 块中的空格和换行完全匹配。")
    elif match_count > 1:
        ctx.fail(f"在文件 {raw_path} 中找到 {match_count} 个匹配项，无法确定要替换哪一个。")

    new_content = content.replace(old_str, new_str, 1)

    ctx.request_confirmation(target_path, content, new_content)

    try:
        target_path.write_text(new_content, encoding="utf-8")
    except PermissionError:
        ctx.fail(f"替换文件内容失败: 对 '{raw_path}' 的访问权限不足。")
    except Exception as e:
        ctx.fail(f"更新文件时发生未知错误: {e}")


def _append_file(ctx: ActContext, args: list[str]):
    if len(args) < 2:
        ctx.fail("append_file 需要至少 2 个参数: [path, content]")

    raw_path, content_to_append = args[0], args[1]
    target_path = ctx.resolve_path(raw_path)

    if not target_path.exists():
        ctx.fail(f"文件未找到: {raw_path}")

    old_content = ""
    try:
        old_content = target_path.read_text(encoding="utf-8")
    except Exception:
        old_content = "[Binary or Unreadable]"

    new_content = old_content + content_to_append

    ctx.request_confirmation(target_path, old_content, new_content)

    try:
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content_to_append)
    except PermissionError:
        ctx.fail(f"追加文件内容失败: 对 '{raw_path}' 的访问权限不足。")
    except Exception as e:
        ctx.fail(f"追加文件时发生未知错误: {e}")
