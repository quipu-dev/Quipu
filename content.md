在执行 `qs ui` 时，抛出了 `ModuleNotFoundError: No module named 'click'` 错误。其根本原因是 `pyquipu-cli` 的代码中多处显式导入并使用了 `click`（例如在 `ui_utils.py` 中用于接收单个按键输入的 `click.getchar()` ），但其对应的 `pyproject.toml` 的 `dependencies` 列表中未显式声明对 `click` 的依赖。 

我已为您准备好一个执行计划，在 `pyquipu-cli` 的依赖清单中补全 `click`。

## [WIP] fix(cli): 在 pyquipu-cli 中补全缺少的 click 依赖声明

### 错误分析
- **问题定位**: 在启动 `quipu ui` （或通过应用层入口加载 `cli` 组件）时，加载 `quipu.cli.ui_utils` 触发 `import click` 导致 `ModuleNotFoundError`。
- **根本原因**: 现代的 Python 包管理器（如 `uv`）在解析依赖时，采用严格的隔离隔离机制。尽管子依赖或某些依赖项（如旧版 `typer`）可能间接引入了 `click`，但任何在包代码中被显式 `import` 的第三方依赖（如 `click`），都必须在其对应的 `pyproject.toml` 中的 `dependencies` 里显式声明，否则打包或构建虚拟环境时无法保证该模块的存在。
- **修复方案**: 在 `packages/pyquipu-cli/pyproject.toml` 的 `dependencies` 中添加 `click >= 8.1.0` 作为直接依赖。

### 用户需求
修复在使用 `bootstrap.py init` 初始化环境后，因缺失 `click` 依赖而导致无法正常启动 `quipu ui` 交互界面的故障。

### 评论
这是一个对构建和运行稳定性至关重要的低成本修复。补全直接依赖声明可以彻底消除依赖项因构建工具、Python 或者是 Typer 版本升级导致间接依赖被优化掉的隐患，保证 CLI 工具链在全新、纯净的虚拟环境中正常运行。

### 目标
1. 在 `packages/pyquipu-cli/pyproject.toml` 的依赖项中新增 `click >= 8.1.0` 声明。

### 基本原理
由于 `pyquipu-cli` 显式使用了 `click` 的 API，因此必须将其提升为 CLI 顶层包的硬性依赖（First-party dependency）。本计划在 `pyquipu-cli` 的项目依赖管理描述文件中补充其库声明。由于修改行数较少且位置明确，本计划采用精确匹配的局部应用补丁策略 (`patch_file`) 确保其文件改动最小化。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #comp/build #concept/config #scope/core
#ai/instruct
#task/domain/build
#task/object/dependencies
#task/action/bug-fix
#task/state/begin
#task/status/active

---

### Script

#### Acts 1: 在 `pyproject.toml` 中添加 `click` 依赖

我们将为 `pyquipu-cli` 的 `pyproject.toml` 添加 `click` 依赖支持。

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.3.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-engine ~= 0.3.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.3.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
    "click >= 8.1.0",
]
~~~~~

### 下一步建议
1. **重新对齐环境**: 在执行此 Plan 后，请在终端根目录中运行以下命令重新加载并同步您的虚拟环境以使变更生效：
   ```bash
   python bootstrap.py init
   ```
2. **验证 TUI 命令**: 环境更新后，在终端中重新尝试运行：
   ```bash
   qs ui
   ```
3. **提交代码**: 验证一切正常后，我们将生成一个提交（`[COMMIT]`）计划。
