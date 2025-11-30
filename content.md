抱歉，这是一个不可原谅的低级错误。在引入 `MessageBus` 的重构过程中，我为了简化代码结构，错误地删除了作为 Act 在线帮助文档的 Docstrings。这直接导致了 `quipu run --list-acts` 无法获取指令说明。

我将立即把所有 Act 的文档字符串恢复原位。

## [WIP] fix: 恢复被误删的 Act 文档字符串

### 错误分析
集成测试 `test_cli_list_acts` 失败，输出显示为大量的“暂无说明”。
这是因为 `quipu run --list-acts` 功能通过反射读取 Act 函数的 `__doc__` 属性来生成帮助信息。
在最近的 MessageBus 重构中，为了代码“整洁”，所有 Act 实现函数（如 `_write_file`）的文档字符串被一并删除。

### 目标
逐一恢复 `quipu-runtime` 下所有 Act 模块中实现函数的 Docstrings，确保 CLI 能够正确显示帮助文档。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #task/domain/testing #task/object/acts #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 恢复 Basic Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/basic.py
~~~~~
~~~~~python
def _end(ctx: ActContext, args: List[str]):
    pass


def _echo(ctx: ActContext, args: List[str]):
    if len(args) < 1:
~~~~~
~~~~~python
def _end(ctx: ActContext, args: List[str]):
    """
    Act: end
    Args: [ignored_contexts...]
    说明: 这是一个空操作。
    它的作用是显式结束上一个指令的参数收集。
    解析器会将后续的 block 视为 end 的参数，而 end 函数会忽略它们。
    """
    pass


def _echo(ctx: ActContext, args: List[str]):
    """
    Act: echo
    Args: [content]
    """
    if len(args) < 1:
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/basic.py
~~~~~
~~~~~python
def _write_file(ctx: ActContext, args: List[str]):
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="write_file", count=2, signature="[path, content]"))
~~~~~
~~~~~python
def _write_file(ctx: ActContext, args: List[str]):
    """
    Act: write_file
    Args: [path, content]
    """
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="write_file", count=2, signature="[path, content]"))
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/basic.py
~~~~~
~~~~~python
def _patch_file(ctx: ActContext, args: List[str]):
    if len(args) < 3:
        ctx.fail(
            bus.get("acts.error.missingArgs", act_name="patch_file", count=3, signature="[path, old_string, new_string]")
        )
~~~~~
~~~~~python
def _patch_file(ctx: ActContext, args: List[str]):
    """
    Act: patch_file
    Args: [path, old_string, new_string]
    """
    if len(args) < 3:
        ctx.fail(
            bus.get("acts.error.missingArgs", act_name="patch_file", count=3, signature="[path, old_string, new_string]")
        )
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/basic.py
~~~~~
~~~~~python
def _append_file(ctx: ActContext, args: List[str]):
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="append_file", count=2, signature="[path, content]"))
~~~~~
~~~~~python
def _append_file(ctx: ActContext, args: List[str]):
    """
    Act: append_file
    Args: [path, content]
    """
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="append_file", count=2, signature="[path, content]"))
~~~~~

#### Acts 2: 恢复 Check Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/check.py
~~~~~
~~~~~python
def _check_files_exist(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="check_files_exist", count=1, signature="[file_list_string]"))
~~~~~
~~~~~python
def _check_files_exist(ctx: ActContext, args: List[str]):
    """
    Act: check_files_exist
    Args: [file_list_string]
    说明: 检查当前工作区内是否存在指定的文件。文件名通过换行符分隔。
    """
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="check_files_exist", count=1, signature="[file_list_string]"))
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/check.py
~~~~~
~~~~~python
def _check_cwd_match(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(
            bus.get("acts.error.missingArgs", act_name="check_cwd_match", count=1, signature="[expected_absolute_path]")
        )
~~~~~
~~~~~python
def _check_cwd_match(ctx: ActContext, args: List[str]):
    """
    Act: check_cwd_match
    Args: [expected_absolute_path]
    说明: 检查当前运行的工作区根目录是否与预期的绝对路径匹配。
    """
    if len(args) < 1:
        ctx.fail(
            bus.get("acts.error.missingArgs", act_name="check_cwd_match", count=1, signature="[expected_absolute_path]")
        )
~~~~~

#### Acts 3: 恢复 Git Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/git.py
~~~~~
~~~~~python
def _git_init(ctx: ActContext, args: List[str]):
    if (ctx.root_dir / ".git").exists():
        bus.warning("acts.git.warning.repoExists")
~~~~~
~~~~~python
def _git_init(ctx: ActContext, args: List[str]):
    """
    Act: git_init
    Args: []
    """
    if (ctx.root_dir / ".git").exists():
        bus.warning("acts.git.warning.repoExists")
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/git.py
~~~~~
~~~~~python
def _git_add(ctx: ActContext, args: List[str]):
    targets = []
    if not args:
~~~~~
~~~~~python
def _git_add(ctx: ActContext, args: List[str]):
    """
    Act: git_add
    Args: [files]
    """
    targets = []
    if not args:
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/git.py
~~~~~
~~~~~python
def _git_commit(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="git_commit", count=1, signature="[message]"))
~~~~~
~~~~~python
def _git_commit(ctx: ActContext, args: List[str]):
    """
    Act: git_commit
    Args: [message]
    """
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="git_commit", count=1, signature="[message]"))
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/git.py
~~~~~
~~~~~python
def _git_status(ctx: ActContext, args: List[str]):
    status = _run_git_cmd(ctx, ["status"])
    bus.data(status)
~~~~~
~~~~~python
def _git_status(ctx: ActContext, args: List[str]):
    """
    Act: git_status
    Args: []
    """
    status = _run_git_cmd(ctx, ["status"])
    bus.data(status)
~~~~~

#### Acts 4: 恢复 Memory Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/memory.py
~~~~~
~~~~~python
def _log_thought(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.get("acts.memory.error.missingContent"))
~~~~~
~~~~~python
def _log_thought(ctx: ActContext, args: List[str]):
    """
    Act: log_thought
    Args: [content]
    说明: 将思维过程追加到 .quipu/memory.md 文件中，用于长期记忆。
    """
    if len(args) < 1:
        ctx.fail(bus.get("acts.memory.error.missingContent"))
~~~~~

#### Acts 5: 恢复 Read Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/read.py
~~~~~
~~~~~python
def _search_files(ctx: ActContext, args: List[str]):
    parser = SafeArgumentParser(prog="search_files", add_help=False)
    parser.add_argument("pattern", help="搜索内容的正则表达式")
~~~~~
~~~~~python
def _search_files(ctx: ActContext, args: List[str]):
    """
    Act: search_files
    Args: pattern [--path PATH]
    """
    parser = SafeArgumentParser(prog="search_files", add_help=False)
    parser.add_argument("pattern", help="搜索内容的正则表达式")
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/read.py
~~~~~
~~~~~python
def _read_file(ctx: ActContext, args: List[str]):
    if not args:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="read_file", count=1, signature="[path]"))
~~~~~
~~~~~python
def _read_file(ctx: ActContext, args: List[str]):
    """
    Act: read_file
    Args: [path]
    """
    if not args:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="read_file", count=1, signature="[path]"))
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/read.py
~~~~~
~~~~~python
def _list_files(ctx: ActContext, args: List[str]):
    parser = SafeArgumentParser(prog="list_files", add_help=False)
    parser.add_argument("path", nargs="?", default=".", help="目标目录")
~~~~~
~~~~~python
def _list_files(ctx: ActContext, args: List[str]):
    """
    Act: list_files
    Args: [path] [--tree]
    """
    parser = SafeArgumentParser(prog="list_files", add_help=False)
    parser.add_argument("path", nargs="?", default=".", help="目标目录")
~~~~~

#### Acts 6: 恢复 Refactor Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/refactor.py
~~~~~
~~~~~python
def _move_file(ctx: ActContext, args: List[str]):
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="move_file", count=2, signature="[src, dest]"))
~~~~~
~~~~~python
def _move_file(ctx: ActContext, args: List[str]):
    """
    Act: move_file
    Args: [src_path, dest_path]
    """
    if len(args) < 2:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="move_file", count=2, signature="[src, dest]"))
~~~~~

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/refactor.py
~~~~~
~~~~~python
def _delete_file(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="delete_file", count=1, signature="[path]"))
~~~~~
~~~~~python
def _delete_file(ctx: ActContext, args: List[str]):
    """
    Act: delete_file
    Args: [path]
    """
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="delete_file", count=1, signature="[path]"))
~~~~~

#### Acts 7: 恢复 Shell Acts 文档

~~~~~act
patch_file
packages/quipu-runtime/src/pyquipu/acts/shell.py
~~~~~
~~~~~python
def _run_command(ctx: ActContext, args: List[str]):
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="run_command", count=1, signature="[command_string]"))
~~~~~
~~~~~python
def _run_command(ctx: ActContext, args: List[str]):
    """
    Act: run_command
    Args: [command_string]
    """
    if len(args) < 1:
        ctx.fail(bus.get("acts.error.missingArgs", act_name="run_command", count=1, signature="[command_string]"))
~~~~~

### 下一步建议
运行集成测试以确认修复。
