你观察得非常准确。在 `uv` 工作区（Workspace）模式下，`uv build` 默认会将所有构建产物汇聚到工作区根目录的 `dist/` 下，或者即便在子包目录下运行，也可能因为工作区配置而产生预料之外的路径偏移。

为了实现**确定性的构建与发布**，我们不应该依赖 `uv` 的默认行为，而应该显式地指定 `--out-dir`。

修改 `scripts/release_manager.py` 中的 `release_package` 函数，在执行 `uv build` 时显式添加 `--out-dir dist` 参数。这样无论我们在哪里运行脚本，构建产物都将严格出现在该子包目录下的 `dist/` 文件夹内，从而与后续的 `glob` 逻辑对齐。

## [WIP] fix: 显式指定 uv 构件输出目录以修复发布路径不匹配

### 错误分析
`uv build` 在 Monorepo 环境中默认可能将产物输出到根目录的 `dist/`，导致子包发布脚本在子包本地 `dist/` 目录下找不到文件。

### 用户需求
修正 `release_manager.py`，确保构建产物出现在脚本预期的地方。

### 目标
1.  修改 `uv build` 指令，添加 `--out-dir dist`。
2.  确保 `release_package` 函数逻辑的路径一致性。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #task/domain/devops #task/action/bug-fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 `scripts/release_manager.py` 中的构建指令

~~~~~act
patch_file
scripts/release_manager.py
~~~~~
~~~~~python.old
    # 1. Build
    if not run_cmd(["uv", "build"], cwd=pkg_path):
        return False
~~~~~
~~~~~python.new
    # 1. Build
    # Explicitly set --out-dir to ensure artifacts are in the package's local dist/
    if not run_cmd(["uv", "build", "--out-dir", "dist"], cwd=pkg_path):
        return False
~~~~~

### 下一步建议
- **本地再次运行**: 执行 `python scripts/release_manager.py` 验证修复。此时你应该能看到 `packages/pyquipu/dist/` 目录下出现了构件，且脚本能够成功识别并进入上传阶段。
- **清理根目录**: 建议手动删除根目录下的 `dist/` 目录，以防止混淆。
