好的，我理解了。这是一个非常好的改进，它强制要求计划的编写者（AI）明确其操作目标，消除了歧义，使 `act` 的行为更加健壮和可预测。

我们将修改 `versioning.py` 插件，将可选的 `--package` 标志改为一个强制性的位置参数。我们将使用一个特殊的标识符 `.` 来代表项目根目录。

## [WIP] refactor: 强制 versioning 插件使用位置参数指定目标

### 用户需求
修改 `versioning.py` 插件中的 `bump_version` 和 `set_version` `act`，将原来可选的 `--package` 标志参数改为一个强制性的位置参数。AI 必须明确提供要操作的目标（具体的包名或代表根目录的 `.`），不能有任何默认行为。

### 评论
这是一个关键的健壮性改进。通过移除可选参数和默认值，我们强制 AI 在生成计划时必须显式声明其意图，这大大降低了因上下文理解错误而意外修改了错误 `pyproject.toml` 文件的风险。

### 目标
1.  修改 `bump_version` 和 `set_version` 函数中的 `argparse` 定义，移除 `--package` 标志，并添加一个名为 `package_target` 的位置参数。
2.  更新 `_get_target_path` 辅助函数，使其能够处理新的 `package_target` 参数，并将 `.` 解析为根 `pyproject.toml` 的路径。
3.  更新 `act` 的文档字符串，以反映新的参数签名。

### 基本原理
我们将利用 `argparse` 对位置参数的内置支持。通过将参数定义为没有 `--` 前缀的字符串，`argparse` 会自动将其视为必需的参数。我们将约定 `.` 作为指向项目根目录的特殊值，这在命令行工具中是一种常见且直观的模式。所有其他值都将被视为 `packages/` 目录下的一个子包名。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #concept/executor #scope/dx #ai/instruct #task/domain/tooling #task/object/version-plugin #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `versioning.py` 插件

我们将使用 `write_file` 覆盖现有的插件文件，以确保应用完整的修改。

~~~~~act
write_file
~~~~~
~~~~~path
.quipu/acts/versioning.py
~~~~~
~~~~~python
import argparse
import re
from typing import List

from pyquipu.common.messaging import bus
from pyquipu.interfaces.exceptions import ExecutionError
from pyquipu.interfaces.types import ActContext, Executor


class SafeArgumentParser(argparse.ArgumentParser):
    """覆盖 ArgumentParser 以抛出 ExecutionError。"""

    def error(self, message):
        raise ExecutionError(f"参数解析错误: {message}")

    def exit(self, status=0, message=None):
        if message:
            raise ExecutionError(message)


def register(executor: Executor):
    """注册版本管理相关的操作"""
    executor.register("bump_version", _bump_version, arg_mode="exclusive")
    executor.register("set_version", _set_version, arg_mode="exclusive")


def _get_target_path(ctx: ActContext, package_target: str) -> str:
    """根据目标字符串确定 pyproject.toml 的路径"""
    if package_target == ".":
        return "pyproject.toml"
    return f"packages/{package_target}/pyproject.toml"


def _update_version_in_file(ctx: ActContext, raw_path: str, new_version: str):
    """读取、更新并写回 toml 文件中的版本号"""
    target_path = ctx.resolve_path(raw_path)
    if not target_path.exists():
        ctx.fail(f"文件未找到: {raw_path}")

    try:
        content = target_path.read_text("utf-8")
    except Exception as e:
        ctx.fail(f"读取文件失败: {raw_path} ({e})")

    version_pattern = re.compile(r"^(version\s*=\s*[\"']).*([\"'])$", re.MULTILINE)
    if not version_pattern.search(content):
        ctx.fail(f"在 {raw_path} 中未找到 'version = \"...\"' 行")

    old_version_match = re.search(r'version\s*=\s*["\'](.*)["\']', content, re.MULTILINE)
    old_version = old_version_match.group(1) if old_version_match else "N/A"

    new_content = version_pattern.sub(rf"\g<1>{new_version}\g<2>", content, count=1)

    if new_content == content:
        bus.info(f"版本号已是 {new_version}，无需修改。")
        return

    ctx.request_confirmation(target_path, content, new_content)

    try:
        target_path.write_text(new_content, "utf-8")
        bus.success(f"✅ [版本] {raw_path} 版本已从 {old_version} 更新为: {new_version}")
    except Exception as e:
        ctx.fail(f"写入文件失败: {raw_path} ({e})")


def _bump_version(ctx: ActContext, args: List[str]):
    """
    Act: bump_version
    Args: <part> <package_target>
    说明: 升级 pyproject.toml 的版本号。
    part: 'major', 'minor', 'patch' 之一。
    package_target: 目标包名 (例如 'quipu-cli') 或 '.' (代表根项目)。
    """
    parser = SafeArgumentParser(prog="bump_version", add_help=False)
    parser.add_argument("part", choices=["major", "minor", "patch"], help="要增加的版本部分")
    parser.add_argument("package_target", help="目标包名或 '.' (根项目)")

    try:
        parsed_args = parser.parse_args(args)
    except ExecutionError as e:
        ctx.fail(str(e))

    raw_path = _get_target_path(ctx, parsed_args.package_target)
    target_path = ctx.resolve_path(raw_path)

    if not target_path.exists():
        ctx.fail(f"文件未找到: {raw_path}")

    content = target_path.read_text("utf-8")
    version_pattern = re.compile(r'^version\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', re.MULTILINE)
    match = version_pattern.search(content)

    if not match:
        ctx.fail(f"在 {raw_path} 中未找到有效的 semver 版本号 (例如 version = \"1.2.3\")")

    major, minor, patch = map(int, match.groups())

    if parsed_args.part == "major":
        major += 1
        minor = 0
        patch = 0
    elif parsed_args.part == "minor":
        minor += 1
        patch = 0
    elif parsed_args.part == "patch":
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    _update_version_in_file(ctx, raw_path, new_version)


def _set_version(ctx: ActContext, args: List[str]):
    """
    Act: set_version
    Args: <version> <package_target>
    说明: 直接设置 pyproject.toml 的版本号。
    version: 新的版本号字符串 (例如 '1.2.3')。
    package_target: 目标包名 (例如 'quipu-cli') 或 '.' (代表根项目)。
    """
    parser = SafeArgumentParser(prog="set_version", add_help=False)
    parser.add_argument("version", help="要设置的完整版本号")
    parser.add_argument("package_target", help="目标包名或 '.' (根项目)")
    try:
        parsed_args = parser.parse_args(args)
    except ExecutionError as e:
        ctx.fail(str(e))

    raw_path = _get_target_path(ctx, parsed_args.package_target)
    _update_version_in_file(ctx, raw_path, parsed_args.version)
~~~~~

### 下一步建议
插件已经更新。现在，`act` 的调用方式变得更加严格和清晰。

**新的用法示例**:
````markdown
### 更新项目版本

#### Acts 1: 升级 quipu-cli 的 patch 版本
~~~~~act
bump_version patch quipu-cli
~~~~~

#### Acts 2: 设置根项目的版本为 1.0.0
~~~~~act
set_version 1.0.0 .
~~~~~
````

如果尝试调用 `bump_version patch` 而不提供第二个参数，`act` 将会因参数不足而失败，这完全符合你的要求。
