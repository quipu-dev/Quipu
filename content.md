好的，我们已经完成了修复，现在将这些变更作为一个原子提交固化到版本历史中。

## [COMMIT] fix(common): 正确打包国际化语言文件以供分发

### 用户需求
将修复打包问题的相关代码变更提交到版本库，确保 `quipu-common` 包在安装后能够包含并找到其 `locales` 语言文件。

### 评论
这是一个关键的修复，它解决了使 Quipu 成为一个可独立分发应用程序的核心障碍。通过将数据文件与使用它的代码进行绑定，并正确配置打包元数据，我们确保了应用在任何环境下都能自洽地运行。

### 目标
1.  已将 `locales` 目录从项目根目录移动到 `packages/quipu-common/src/quipu/common/` 内部。
2.  已更新 `packages/quipu-common/pyproject.toml` 以包含 `locales` 目录作为 `package_data`。
3.  已重构 `find_locales_dir` 函数以使用可靠的相对路径查找。
4.  将以上所有变更创建一个 Git 提交。

### 基本原理
遵循 Python 打包的最佳实践，我们将非代码的数据文件（`locales/*.json`）置于其所属的包（`quipu.common`）内部，并通过 `pyproject.toml` 中的 `tool.setuptools.package-data` 指令明确声明，以确保 `setuptools` 在构建 `wheel` 文件时将其包含在内。同时，将文件查找逻辑修改为相对路径查找，使其在开发环境和最终用户的安装环境中都能稳定工作。

### 标签
#intent/fix #flow/ready #priority/critical #comp/common #comp/build #concept/config #scope/core #ai/instruct #task/domain/build #task/object/packaging #task/action/bug-fix #task/state/end #task/status/completed

---

### Script

#### Acts 1: 提交打包修复

我们将把所有相关的修改（文件移动、`toml` 配置更新、代码重构）添加到 Git 暂存区，并创建一个内容详尽的提交。

~~~~~act
git_add
locales
packages/quipu-common/pyproject.toml
packages/quipu-common/src/quipu/common/messaging/messages.py
packages/quipu-common/src/quipu/common/locales
~~~~~

~~~~~act
git_commit
~~~~~
~~~~~text
fix(common): correctly package localization files for distribution

Moves the `locales` directory from the project root into the `quipu.common` package source and updates the build configuration to include it as package data. This resolves a critical issue where the installed application could not find its language files.

The fix involves three key changes:
1.  **File Structure**: The `locales` directory is now located at `packages/quipu-common/src/quipu/common/locales`, making it part of the package itself.
2.  **Packaging**: `packages/quipu-common/pyproject.toml` is updated with `[tool.setuptools.package-data]` to ensure the `locales/**/*.json` files are included in the built wheel.
3.  **Lookup Logic**: The `find_locales_dir` function in `messages.py` is refactored to use a robust, relative path lookup, which works correctly in both development (editable install) and production (site-packages) environments.
~~~~~

### 下一步建议
现在修复已经提交，你可以运行 `qpromote` 命令来用最新的、已修复的代码重建你的稳定版 `qs` 环境。之后，你可以再次运行 `qs ui` 来最终确认问题已在稳定版中得到解决。
