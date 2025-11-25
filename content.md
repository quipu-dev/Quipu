# fix: 修复 Acts 插件加载路径和测试用例导入错误

## 目标
修复因项目结构变化导致的两个关键问题：
1.  `PROJECT_ROOT` 指向错误的路径，导致 `acts/` 目录下的插件无法被加载，进而导致绝大多数集成测试失败。
2.  `tests/test_integration_v2.py` 中使用了旧的模块导入方式 (`import main`)，导致 `ModuleNotFoundError`。

## 基本原理
1.  **修正配置根目录**: `packages/quipu-cli/src/quipu/cli/config.py` 中的 `PROJECT_ROOT` 原本通过 `Path(__file__).parent` 获取。在 Monorepo 结构中，我们需要它指向项目的**顶层根目录**（即包含 `acts/` 文件夹的地方）。我们将修改逻辑，使其向上递归查找特定的标记文件（如 `pyproject.toml` 且包含 `[project]`），从而定位到真实的根目录。
2.  **修正测试导入**: `main` 模块现在位于 `quipu.cli` 包中。我们需要更新测试代码以正确导入它。

## 标签
修复路径问题。 #fix #config #tests

---

## Script

### Act 1: 智能定位项目根目录

修改 `quipu-cli` 的配置，使其能够自动探测 Monorepo 的根目录。

~~~~~act
write_file packages/quipu-cli/src/quipu/cli/config.py
~~~~~
~~~~~python
import os
from pathlib import Path

# 全局配置中心

def _find_project_root() -> Path:
    """
    向上递归查找项目根目录。
    依据：存在 'acts' 目录 或 顶层 'pyproject.toml'。
    """
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "acts").exists() and (parent / "packages").exists():
            return parent
        if (parent / "pyproject.toml").exists():
            # 简单的检查，看是否是顶层配置
            try:
                content = (parent / "pyproject.toml").read_text()
                if 'name = "quipu-dev"' in content:
                    return parent
            except Exception:
                pass
    # Fallback: 如果找不到（比如已安装到 site-packages），则指向当前文件所在目录
    # 这种情况下，acts 可能需要以其他方式加载（待定）
    return Path(__file__).parent.resolve()

# 项目根目录（代码所在位置）
PROJECT_ROOT: Path = _find_project_root()

# 默认的工作区根目录，可以通过环境变量覆盖
# 在实际运行时，通常由 CLI 参数指定
DEFAULT_WORK_DIR: Path = Path(os.getenv("AI_FS_WORK_DIR", "."))

# 默认的指令入口文件
# 用户可以在此修改默认值，或通过环境变量 AXON_ENTRY_FILE 覆盖
DEFAULT_ENTRY_FILE: Path = Path(os.getenv("AXON_ENTRY_FILE", "o.md"))

# 日志级别
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
~~~~~

### Act 2: 修复集成测试中的模块导入

将 `import main` 替换为正确的包内导入。

~~~~~act
replace tests/test_integration_v2.py
~~~~~
~~~~~python
    def test_cli_no_input_shows_usage(self, monkeypatch, tmp_path):
        """测试无输入时显示用法"""
        # 1. 临时修改 main 模块中的默认入口文件引用，防止读取当前目录下的 o.md
        # 注意：必须 patch 'main' 模块，而不是 'config' 模块，因为 main 采用了 from import
        import main
        monkeypatch.setattr(main, "DEFAULT_ENTRY_FILE", tmp_path / "non_existent.md")
        
        # 2. 同时确保 STDIN 不是 TTY，也不是管道（模拟纯交互式空运行）
~~~~~
~~~~~python
    def test_cli_no_input_shows_usage(self, monkeypatch, tmp_path):
        """测试无输入时显示用法"""
        # 1. 临时修改 main 模块中的默认入口文件引用，防止读取当前目录下的 o.md
        # 注意：必须 patch 'main' 模块，而不是 'config' 模块，因为 main 采用了 from import
        from quipu.cli import main
        monkeypatch.setattr(main, "DEFAULT_ENTRY_FILE", tmp_path / "non_existent.md")
        
        # 2. 同时确保 STDIN 不是 TTY，也不是管道（模拟纯交互式空运行）
~~~~~