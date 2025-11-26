# fix: 修正 ruff 命令并完善开发环境脚本

## 用户需求
用户根据上一个计划的指示，在更新了开发环境后尝试运行 `qd format .` 和 `qd check .`，但收到了 `No such command` 错误。这表明 `format` 和 `check` 并非 `quipu` CLI 的子命令。

## 评论
这是一个由上一个计划中错误的指令导致的直接问题。`ruff` 是一个独立的工具，它被安装到了开发环境中，但不应该通过 `quipu` 的别名 (`qd`) 来调用。正确的调用方式是直接使用 `ruff` 命令。

为了从根本上解决这个问题并优化开发者体验，本次修复将不仅提供正确的命令，还会自动化创建别名设置脚本 (`dev_setup.sh` 和 `dev_setup.fish`)，并将 `ruff` 的别名也包含进去，确保环境设置的一致性和便捷性。

## 目标
1.  创建标准的 `dev_setup.sh` 和 `dev_setup.fish` 文件，用于设置 `qs`、`qd` 和 `ruff` 命令的别名。
2.  修改 `bootstrap.py` 脚本，使其在 `init` 或 `promote` 过程中自动生成上述的 `dev_setup` 文件。
3.  更新 `bootstrap.py` 中的使用说明，以反映新的 `ruff` 别名。
4.  提供给用户最终的、正确的操作指令。

## 基本原理
通过让 `bootstrap.py` 脚本负责生成 shell 别名配置文件，我们消除了开发者手动创建和维护这些文件的需要，从而减少了因环境不一致或配置错误导致的问题。将 `ruff` 命令也纳入别名管理，使得格式化和代码检查的操作与 `quipu` 命令的调用方式保持一致，提升了整体的开发流程体验。

## 标签
#comp/build #scope/dx #fix

---

## Script

### Acts 1: 创建标准的别名设置脚本

我们将创建 `dev_setup.sh` (用于 bash/zsh) 和 `dev_setup.fish` (用于 fish shell)，这两个文件将包含所有必要的别名。

~~~~~act
write_file dev_setup.sh
~~~~~
~~~~~bash
#!/bin/bash
# shellcheck disable=SC2034

# Fhrsk (AyeL's private stack)
# Quipu Development Environment Setup for bash/zsh

# Get the absolute path of the script's directory
# This ensures that the script can be sourced from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define aliases
alias qs="$DIR/.envs/stable/bin/quipu"
alias qd="$DIR/.envs/dev/bin/quipu"
alias ruff="$DIR/.envs/dev/bin/ruff"

echo "✅ Quipu & Ruff aliases activated for the current session:"
echo "   qs   -> Stable Quipu (.envs/stable)"
echo "   qd   -> Dev Quipu    (.envs/dev)"
echo "   ruff -> Dev Ruff     (.envs/dev)"
~~~~~

~~~~~act
write_file dev_setup.fish
~~~~~
~~~~~fish
# Fhrsk (AyeL's private stack)
# Quipu Development Environment Setup for Fish Shell

# Get the absolute path of the script's directory
# This ensures that the script can be sourced from anywhere
set SCRIPT_PATH (status --current-filename)
set DIR (dirname "$SCRIPT_PATH")

# Define aliases
alias qs "$DIR/.envs/stable/bin/quipu"
alias qd "$DIR/.envs/dev/bin/quipu"
alias ruff "$DIR/.envs/dev/bin/ruff"

echo "✅ Quipu & Ruff aliases activated for the current session:"
echo "   qs   -> Stable Quipu (.envs/stable)"
echo "   qd   -> Dev Quipu    (.envs/dev)"
echo "   ruff -> Dev Ruff     (.envs/dev)"
~~~~~

### Acts 2: 更新 bootstrap.py 以自动生成脚本

现在，我们将修改 `bootstrap.py`，让它在执行时自动创建或覆盖上述两个文件，并更新使用说明。

~~~~~act
replace bootstrap.py
~~~~~
~~~~~python
def install_packages(env_path: Path, editable: bool):
    """安装包到指定环境"""
~~~~~
~~~~~python
def create_setup_scripts():
    """自动生成 dev_setup.sh 和 dev_setup.fish 文件"""
    sh_content = """#!/bin/bash
# shellcheck disable=SC2034

# Fhrsk (AyeL's private stack)
# Quipu Development Environment Setup for bash/zsh

# Get the absolute path of the script's directory
# This ensures that the script can be sourced from anywhere
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define aliases
alias qs="$DIR/.envs/stable/bin/quipu"
alias qd="$DIR/.envs/dev/bin/quipu"
alias ruff="$DIR/.envs/dev/bin/ruff"

echo "✅ Quipu & Ruff aliases activated for the current session:"
echo "   qs   -> Stable Quipu (.envs/stable)"
echo "   qd   -> Dev Quipu    (.envs/dev)"
echo "   ruff -> Dev Ruff     (.envs/dev)"
"""
    
    fish_content = """# Fhrsk (AyeL's private stack)
# Quipu Development Environment Setup for Fish Shell

# Get the absolute path of the script's directory
# This ensures that the script can be sourced from anywhere
set SCRIPT_PATH (status --current-filename)
set DIR (dirname "$SCRIPT_PATH")

# Define aliases
alias qs="$DIR/.envs/stable/bin/quipu"
alias qd="$DIR/.envs/dev/bin/quipu"
alias ruff="$DIR/.envs/dev/bin/ruff"

echo "✅ Quipu & Ruff aliases activated for the current session:"
echo "   qs   -> Stable Quipu (.envs/stable)"
echo "   qd   -> Dev Quipu    (.envs/dev)"
echo "   ruff -> Dev Ruff     (.envs/dev)"
"""
    
    (ROOT_DIR / "dev_setup.sh").write_text(sh_content)
    (ROOT_DIR / "dev_setup.fish").write_text(fish_content)
    print("✨ 已生成/更新别名设置脚本 (dev_setup.sh, dev_setup.fish)")


def install_packages(env_path: Path, editable: bool):
    """安装包到指定环境"""
~~~~~

~~~~~act
replace bootstrap.py
~~~~~
~~~~~python
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
    
    print("\n✅ 晋升完成！现在的 'qs' 是完全独立的二进制快照。")
    print("   (即使删除 packages/ 目录，qs 依然可以运行)")
~~~~~
~~~~~python
def setup():
    """初始化双环境"""
    ENVS_DIR.mkdir(exist_ok=True)
    
    # 1. Setup Stable (编译版)
    create_venv(STABLE_DIR)
    install_packages(STABLE_DIR, editable=False)
    
    # 2. Setup Dev (链接版)
    create_venv(DEV_DIR)
    install_packages(DEV_DIR, editable=True)
    
    create_setup_scripts()
    print("\n✅ 环境初始化完成！")
    print_usage()

def promote():
    """将当前源码晋升为 Stable 工具"""
    print("🚀 正在晋升 Dev 代码到 Stable 环境...")
    
    # 重建 Stable
    create_venv(STABLE_DIR)
    install_packages(STABLE_DIR, editable=False)
    
    # Dev 环境也需要 ruff，所以总是重新安装
    create_venv(DEV_DIR)
    install_packages(DEV_DIR, editable=True)
    
    create_setup_scripts()
    print("\n✅ 晋升完成！现在的 'qs' 是完全独立的二进制快照。")
    print("   (即使删除 packages/ 目录，qs 依然可以运行)")
~~~~~

~~~~~act
replace bootstrap.py
~~~~~
~~~~~python
def print_usage():
    print("-" * 50)
    print("请运行以下命令激活别名:")
    print("  source dev_setup.sh")
    print("-" * 50)
    print("命令说明:")
    print("  qs <args>   -> Stable (独立副本，删除源码不影响)")
    print("  qd <args>   -> Dev    (实时引用，修改源码即刻生效)")
    print("-" * 50)
~~~~~
~~~~~python
def print_usage():
    print("-" * 50)
    print("请运行以下命令激活别名 (根据你的 shell 选择):")
    print("  source dev_setup.sh    # for bash/zsh")
    print("  source dev_setup.fish  # for fish")
    print("-" * 50)
    print("命令说明:")
    print("  qs <args>    -> Stable (独立副本，删除源码不影响)")
    print("  qd <args>    -> Dev    (实时引用，修改源码即刻生效)")
    print("  ruff <args>  -> Dev ruff (用于格式化和检查)")
    print("-" * 50)
~~~~~

### Acts 3: 正确的操作指令

在执行完此计划后，请按照以下步骤操作：

1.  **重新生成环境和脚本**:
    运行 `python bootstrap.py promote`。这会重新构建环境，并创建 `dev_setup.sh` 和 `dev_setup.fish` 文件。

2.  **激活别名**:
    根据你的 shell，运行 `source dev_setup.sh` 或 `source dev_setup.fish`。

3.  **格式化与检查 (正确方式)**:
    现在你可以使用 `ruff` 别名了。在项目根目录运行：
    *   `ruff format .` (格式化所有文件)
    *   `ruff check .` (检查代码问题)
