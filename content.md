我为你生成一个 `[WIP]` 计划，将 `pyquipu-runtime` 升级至 `0.3.1` 并同步所有引用它的包的依赖声明。

## [WIP] fix(runtime): 提升 pyquipu-runtime 至 0.3.1 并同步更新工作区依赖

### 错误分析
`pyquipu-runtime 0.3.0` 此前已发布到 PyPI，但其内置了错误的依赖约束（`pyquipu-spec ~= 0.1.1`）。由于 PyPI 具有版本不可变性（Immutable Releases），无法直接覆盖原版本，必须通过补丁版本（Patch Version）`0.3.1` 重新发布以纠正依赖关系。

### 用户需求
1. 修复并升级 `pyquipu-runtime` 的版本号至 `0.3.1`。
2. 同步更新依赖了 `pyquipu-runtime` 的所有工作区包（`pyquipu`, `pyquipu-application`, `pyquipu-cli`）。

### 评论
发布包含错误依赖元数据的包属于发布事故中较常见的情况。采用标准语义化版本发布 `0.3.1` 补丁，配合 PyPI 的 Yank 机制，是最标准、最安全的解决方案。

### 目标
1. 将 `packages/pyquipu-runtime/pyproject.toml` 中的 `project.version` 更新为 `0.3.1`。
2. 将各包中对 `pyquipu-runtime` 的依赖声明统一更新为 `~= 0.3.1`。

### 基本原理
遵循 SemVer（语义化版本规范），以补丁级别修复依赖声明。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/config #scope/api #ai/instruct #task/domain/release #task/object/runtime-version #task/action/bump #task/state/continue

---

### Script

#### Acts 1: 提升 `pyquipu-runtime` 版本为 0.3.1

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu-runtime"
version = "0.3.0"
~~~~~
~~~~~toml
[project]
name = "pyquipu-runtime"
version = "0.3.1"
~~~~~

#### Acts 2: 更新 `pyquipu-application` 对 runtime 的依赖约束

~~~~~act
patch_file
packages/pyquipu-application/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.1",
    "pyquipu-common ~= 0.2.0",
]
~~~~~

#### Acts 3: 更新 `pyquipu-cli` 对 runtime 的依赖约束

~~~~~act
patch_file
packages/pyquipu-cli/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.4.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
    "click >= 8.1.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-runtime ~= 0.3.1",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-application ~= 0.4.0",
    "typer >= 0.9.0",
    "textual >= 0.58.0",
    "click >= 8.1.0",
]
~~~~~

#### Acts 4: 更新 `pyquipu` 元包对 runtime 的依赖约束

~~~~~act
patch_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-application ~= 0.4.0",
    "pyquipu-cli ~= 0.4.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-runtime ~= 0.3.0",
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-application ~= 0.4.0",
    "pyquipu-cli ~= 0.4.0",
    "pyquipu-common ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-runtime ~= 0.3.1",
]
~~~~~

### 下一步建议

1. **运行检查脚本验证**：
   ```bash
   python scripts/check_monorepo_deps.py
   ```
2. **重新构建发布 `pyquipu-runtime`**：
   打包并推送 `0.3.1`：
   ```bash
   uv build packages/pyquipu-runtime --out-dir dist
   twine upload dist/pyquipu_runtime-0.3.1*
   ```
3. **前往 PyPI Yank 旧版本**：
   登录 PyPI 后台将 `pyquipu-runtime 0.3.0` 标记为 Yanked。
