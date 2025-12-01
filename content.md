好的，这是一个符合你要求的重构计划。

我们将在 `bootstrap.py` 脚本中进行以下三项核心修改：

1.  **移除别名脚本的自动生成**：`dev_setup.sh` 和 `dev_setup.fish` 将不再被创建，以便你自行管理 shell 环境。
2.  **新增 `dev` 命令**：提供一个仅用于更新开发环境 (`dev`) 的快速命令，它不会触碰稳定环境 (`stable`)，非常适合在添加新包后更新链接。
3.  **包的自动发现**：脚本将自动扫描 `packages/` 目录，不再需要手动维护 `PACKAGES` 列表。

以下是修改后的 `bootstrap.py` 脚本。

## [WIP] feat(build): 改进 bootstrap 脚本以支持 dev 更新和包自动发现

### 用户需求
当前的 `bootstrap.py` 脚本存在一些不便之处：
1.  它会自动生成 shell 别名脚本 (`dev_setup.fish`, `dev_setup.sh`)，这对于希望自行管理环境的用户来说不够灵活。
2.  当添加一个新的本地包时，必须运行 `init` 命令来完全重建两个环境，这很耗时且可能中断 `stable` 环境的可用性。需要一个只更新 `dev` 环境的命令。
3.  `PACKAGES` 列表是硬编码的，每次添加新包都需要手动修改脚本。

### 评论
这是一次对开发者体验 (DX) 的重要改进。通过实现包的自动发现、提供独立的 `dev` 环境更新命令以及移除对用户 shell 配置的侵入，`bootstrap.py` 脚本将变得更加健壮、灵活和易于维护，能更好地适应项目未来的扩展。

### 目标
1.  移除 `create_setup_scripts` 函数及其所有调用。
2.  实现一个新的 `find_packages` 函数，用于动态扫描 `packages/` 目录并生成包列表。
3.  在 `argparse` 中添加一个新的 `dev` 子命令，其功能是仅重新安装 `dev` 环境中的包。
4.  更新 `print_usage` 函数以反映这些变化。

### 基本原理
我们将利用 `pathlib` 来遍历 `packages` 目录下的子目录，并通过检查是否存在 `pyproject.toml` 文件来识别一个目录是否为有效的 Python 包。然后，我们将这个动态列表用于所有安装操作。同时，通过添加一个新的 `dev` 命令并为其绑定一个仅调用 `install_packages(DEV_DIR, editable=True)` 的函数，我们可以在不影响 `stable` 环境的前提下，快速更新开发环境以反映项目结构的变化。

### 标签
#intent/refine #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/tooling #task/object/bootstrap-script #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重写 bootstrap.py

我们将使用 `write_file` 一次性更新整个 `bootstrap.py` 文件以应用所有修改。

~~~~~act
write_file
bootstrap.py
~~~~~
~~~~~python
#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

# 配置
ROOT_DIR = Path(__file__).parent
ENVS_DIR = ROOT_DIR / ".envs"
STABLE_DIR = ENVS_DIR / "stable"
DEV_DIR = ENVS_DIR / "dev"


def find_packages(root: Path) -> List[Path]:
    """自动发现 packages 目录下的所有包"""
    packages_dir = root / "packages"
    found = []
    if not packages_dir.is_dir():
        return []
    for pkg_path in packages_dir.iterdir():
        if pkg_path.is_dir() and (pkg_path / "pyproject.toml").exists():
            found.append(pkg_path)
    print(f"🔍 自动发现 {len(found)} 个包: {[p.name for p in found]}")
    return found


PACKAGES = find_packages(ROOT_DIR)


def check_uv():
    """检查 uv 是否安装"""
    if not shutil.which("uv"):
        print("❌ 错误: 未找到 'uv'。请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)


def create_venv(path: Path):
    """创建虚拟环境"""
    if path.exists():
        print(f"🔄 清理旧环境: {path}")
        shutil.rmtree(path)

    print(f"🔨 创建虚拟环境: {path}")
    subprocess.run(["uv", "venv", str(path)], check=True, capture_output=True)


def install_packages(env_path: Path, editable: bool):
    """安装包到指定环境"""
    if not PACKAGES:
        print("⚠️  警告: 未在 packages/ 目录下发现任何包，跳过安装。")
        return

    # 1.如果是 Dev 环境：使用 -e 链接模式安装
    if editable:
        print(f"📦 [Dev] 正在以可编辑模式(-e)安装到 {env_path.name}...")
        pip_cmd = ["uv", "pip", "install", "-p", str(env_path), "pytest", "pytest-cov", "ruff", "pytest-timeout"]

        pkg_args = []
        for pkg_path in PACKAGES:
            pkg_args.extend(["-e", str(pkg_path)])

        subprocess.run(pip_cmd + pkg_args, check=True)

    # 2.如果是 Stable 环境：先构建 Wheel，再安装 Wheel
    else:
        print(f"📦 [Stable] 正在构建 Wheel 并安装到 {env_path.name} (完全隔离)...")

        # 创建临时目录存放构建好的 .whl 文件
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # 第一步：构建所有包的 Wheel
            for pkg_src in PACKAGES:
                print(f"   ⚙️  编译: {pkg_src.name} -> .whl")
                subprocess.run(
                    ["uv", "pip", "wheel", str(pkg_src), "--wheel-dir", str(tmp_path)],
                    check=True,
                    capture_output=True,
                )

            wheels = list(tmp_path.glob("*.whl"))
            if not wheels:
                print("❌ 错误: 未能生成 Wheel 文件")
                sys.exit(1)

            print(f"   📥 安装 {len(wheels)} 个 Wheel 文件...")

            # 第二步：安装 Wheel
            install_cmd = ["uv", "pip", "install", "-p", str(env_path)] + [str(w) for w in wheels]
            subprocess.run(install_cmd, check=True, capture_output=True)


def setup():
    """初始化双环境"""
    ENVS_DIR.mkdir(exist_ok=True)

    # 1. Setup Stable (编译版)
    create_venv(STABLE_DIR)
    install_packages(STABLE_DIR, editable=False)

    # 2. Setup Dev (链接版)
    create_venv(DEV_DIR)
    install_packages(DEV_DIR, editable=True)

    print("\n✅ 环境初始化完成！")
    print_usage()


def promote():
    """将当前源码晋升为 Stable 工具"""
    print("🚀 正在晋升 Dev 代码到 Stable 环境...")

    # 重建 Stable
    create_venv(STABLE_DIR)
    install_packages(STABLE_DIR, editable=False)

    print("\n✅ 晋升完成！现在的 'qs' 是当前代码的完全独立快照。")


def update_dev_env():
    """仅更新开发环境"""
    print("🔄 正在更新 Dev 环境...")
    if not DEV_DIR.exists():
        print(f"   -> Dev 环境不存在，将创建一个新环境。")
        create_venv(DEV_DIR)
    install_packages(DEV_DIR, editable=True)
    print("\n✅ Dev 环境更新完成。")


def print_usage():
    print("-" * 50)
    print("环境已就绪。请根据你的 shell 配置别名，例如:")
    print("  alias qs='$PWD/.envs/stable/bin/quipu'")
    print("  alias qd='$PWD/.envs/dev/bin/quipu'")
    print("  alias qtest='$PWD/.envs/dev/bin/pytest'")
    print("  alias ruff='$PWD/.envs/dev/bin/ruff'")
    print("-" * 50)
    print("命令说明:")
    print("  qs [...]    -> 稳定版 (用于执行)")
    print("  qd [...]    -> 开发版 (用于调试)")
    print("  qtest       -> 运行测试")
    print("  ruff        -> 格式化与检查")
    print("-" * 50)


def main():
    check_uv()
    parser = argparse.ArgumentParser(description="Quipu 开发环境管理脚本")
    subparsers = parser.add_subparsers(dest="command", help="可用的命令")

    subparsers.add_parser("init", help="初始化所有环境 (stable 和 dev)")
    subparsers.add_parser("promote", help="将当前源码快照更新到 stable 环境")
    subparsers.add_parser("dev", help="仅更新 dev 环境 (例如，在添加新包后)")

    args = parser.parse_args()
    if args.command == "init":
        setup()
    elif args.command == "promote":
        promote()
    elif args.command == "dev":
        update_dev_env()
    else:
        if not STABLE_DIR.exists() or not DEV_DIR.exists():
            print("💡 环境尚未初始化，正在执行首次设置...")
            setup()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
~~~~~
