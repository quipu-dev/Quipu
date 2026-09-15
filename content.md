好的，基于检查结果和当前环境的精确版本清单（`pip list` 结果），我将生成一个 `[WIP]` 计划，对根目录 `pyproject.toml` 中的裸依赖补全版本约束，同时微调 `scripts/check_monorepo_deps.py` 对 workspace 内部包引用的豁免逻辑。

## [WIP] fix(deps): 补齐根目录开发依赖约束并完善检查脚本对工作区内部包的豁免

### 错误分析
运行 `scripts/check_monorepo_deps.py` 时报错：
1. **开发工具裸依赖**：根目录 `pyproject.toml` 的 `optional-dependencies.dev` 中，`pytest`, `pytest-cov`, `pytest-timeout`, `ruff`, `pre-commit` 没有指定任何版本约束。虽然生产依赖有锁定，但为了保证 CI 环境与本地开发环境的构建确定性（Reproducibility），开发工具依赖应当加上清晰的版本下限。
2. **工作区内部包裸依赖报错**：根目录 `pyproject.toml` 作为 workspace root，通过 `[tool.uv.sources]` 将 `pyquipu` 和 `pyquipu-test-utils` 映射到了本地源码目录（`workspace = true`）。但在检查脚本规则三中，仅排除了 `pyquipu`，未排除 `pyquipu-test-utils`（或任意属于该 workspace 自身的内部包），导致将其当作裸外部依赖报错。

### 用户需求
1. 为根目录 `dev` 组中的所有外部开发依赖补充明确的版本约束（参考当前环境安装的实际版本）。
2. 让 `pyquipu-test-utils` 与内部包规范保持一致，或者在检查脚本中正确识别 workspace 内部包。

### 评论
为根目录的开发依赖定义最低兼容版本是工程化规范的最佳实践，能防止开发者环境由于安装过旧版本的 `pytest` 或 `ruff` 导致本地与 CI 行为不一致；同时将检查脚本调整为：凡是声明在 `[tool.uv.sources]` 或 `packages/*` 内的内部 workspace 包，当由根目录引用时应被识别为 workspace 本地包。对于声明规范，根目录引用自身 workspace 内部测试工具可以直接声明为 `"pyquipu-test-utils ~= 0.4.0"`。

### 目标
1. 在根目录 `pyproject.toml` 中，为 `pytest`, `pytest-cov`, `pytest-timeout`, `ruff`, `pre-commit` 添加合适的版本约束（参考当前环境中的大版本下限）。
2. 将 `pyquipu-test-utils` 在根目录中声明为当前版本 `"pyquipu-test-utils ~= 0.4.0"`。
3. 增强 `scripts/check_monorepo_deps.py`，使“裸依赖检查”能够自动识别并豁免 workspace root 引用内部成员包的情形。

### 基本原理
根据当前虚拟环境的实际版本：
- `pytest==9.0.2` -> `>= 8.0.0`
- `pytest-cov==7.0.0` -> `>= 5.0.0`
- `pytest-timeout==2.4.0` -> `>= 2.2.0`
- `ruff==0.16.7` -> `>= 0.4.0`
- `pre-commit==4.5.1` -> `>= 3.5.0`
- `pyquipu-test-utils` -> `~= 0.4.0` (其自身实际版本为 0.4.0)

通过 `patch_file` 更新配置并增强脚本逻辑。

### 标签
#intent/fix #flow/ready #priority/high #comp/build #concept/config #scope/dx #ai/instruct #task/domain/tooling #task/object/monorepo-deps #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 规范化根目录 `pyproject.toml` 中的开发依赖

我们将所有外部工具添加版本下限约束，并将内部包 `pyquipu-test-utils` 指定为当前实际对应的 `~= 0.4.0`。

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml
[project.optional-dependencies]
dev = [
    "pyquipu",
    "pyquipu-test-utils",
    "pytest",
    "pytest-cov",
    "pytest-timeout",
    "ruff",
    "pre-commit",
    "pyneedle-pointer ~= 0.2.1",
]
~~~~~
~~~~~toml
[project.optional-dependencies]
dev = [
    "pyquipu",
    "pyquipu-test-utils ~= 0.4.0",
    "pytest >= 8.0.0",
    "pytest-cov >= 5.0.0",
    "pytest-timeout >= 2.2.0",
    "ruff >= 0.4.0",
    "pre-commit >= 3.5.0",
    "pyneedle-pointer ~= 0.2.1",
]
~~~~~

#### Acts 2: 完善 `scripts/check_monorepo_deps.py` 内部包自动豁免逻辑

将检查脚本中的规则三（裸依赖检查）进一步增强：如果某个依赖属于当前 Monorepo 的 workspace 内部包（即存在于 `workspace_pkg_versions` 中），且是在 `pyquipu-monorepo` 根工作区中引入，则自动豁免或仅按内部包版本比对规则处理，不再产生误报。

~~~~~act
patch_file
scripts/check_monorepo_deps.py
~~~~~
~~~~~python
    # 5. 校验规则三：裸依赖检查（不允许缺乏版本范围）
    print("\n📋 [检查项 3/3] 裸依赖检查 (不允许无版本范围限制)...")
    for req_name, occurrences in dep_map.items():
        # 允许根 monorepo 的 dev 依赖或者 meta 依赖适当放宽？严格原则下建议一律报错
        for occ in occurrences:
            # 排除自身工作区根项目引用 pyquipu 的元声明
            if occ.package_name == "pyquipu-monorepo" and req_name == "pyquipu":
                continue

            if not occ.spec_version:
                # 忽略一些纯粹开发工具且已在其他地方锁定的，若遵循严格原则直接报错
                print(
                    f"  ⚠️  警告/错误: 发现裸依赖 (缺乏版本约束):\n"
                    f"     依赖: '{req_name}'\n"
                    f"     位置: {occ.package_name} ({occ.file_path})"
                )
                has_errors = True
~~~~~
~~~~~python
    # 5. 校验规则三：裸依赖检查（不允许缺乏版本范围）
    print("\n📋 [检查项 3/3] 裸依赖检查 (不允许无版本范围限制)...")
    for req_name, occurrences in dep_map.items():
        for occ in occurrences:
            # 根 monorepo 引用自身 workspace 内部包时，如果未指定版本则由 workspace 源码解析，不视作裸外部依赖
            if occ.package_name == "pyquipu-monorepo" and req_name in workspace_pkg_versions:
                continue

            if not occ.spec_version:
                print(
                    f"  ⚠️  警告/错误: 发现裸依赖 (缺乏版本约束):\n"
                    f"     依赖: '{req_name}'\n"
                    f"     位置: {occ.package_name} ({occ.file_path})"
                )
                has_errors = True
~~~~~

### 下一步建议

1. **重新运行检查**：
   在终端中再次执行检查脚本：
   ```bash
   python scripts/check_monorepo_deps.py
   ```
   此时应该全部通过并输出 `✅ 检查通过！`。
2. **运行测试套件**：
   执行测试确保修改没有影响开发环境：
   ```bash
   uv run pytest
   ```
3. **完成阶段提交**：
   测试均通过后，可通知我生成 `[COMMIT]` 计划以将这些修复提交到版本控制中。
