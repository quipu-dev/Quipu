好的，我将为你生成一个 `[WIP]` 计划，用于修复所有发现的 Monorepo 依赖不一致问题，并将新创建的依赖检查脚本集成到 GitHub Actions CI 流水线中。

## [WIP] fix(deps): 修复 monorepo 内部与外部依赖约束并集成检查脚本到 CI

### 错误分析
当前 monorepo 存在多处依赖版本不一致和约束缺失的问题：
1. **内部依赖版本错位**：`packages/pyquipu-runtime/pyproject.toml` 中声明 `pyquipu-spec ~= 0.1.1`，而实际工作区中 `pyquipu-spec` 的当前版本为 `0.2.0`（其他所有子包均声明为 `~= 0.2.0`）。这导致 `pyquipu-runtime` 单独打包后无法解析新版 `pyquipu-spec`。
2. **约束不一致与裸依赖**：
   - `packages/pyquipu-test-utils/pyproject.toml` 中将 `typer` 声明为裸依赖，与 `pyquipu-cli` / `pyquipu-runtime` 中的 `typer >= 0.9.0` 不一致。
   - 根目录 `pyproject.toml` 的 `optional-dependencies.dev` 中包含裸依赖 `pyneedle-pointer`，与子包中要求的 `~= 0.2.1` 不一致。
3. **CI 流程缺少依赖一致性守门机制**：目前 `.github/workflows/ci.yml` 仅执行代码格式检查和测试，缺乏对 monorepo 结构与依赖规范的自动化校验，容易再次引入类似问题。

### 用户需求
1. 修复子包与根目录中的依赖版本不一致和裸依赖问题，保证单版本一致性原则。
2. 将 `scripts/check_monorepo_deps.py` 检查脚本集成到 CI 流水线中。

### 评论
在 monorepo 架构中，严格执行单一版本策略（Single Version Policy）和内部包对齐是确保构建确定性和发布可靠性的关键基础。将自定义校验脚本作为 CI 的首要阶段运行，能够以零开销在代码合并前拦截配置冲突。

### 目标
1. 修正 `packages/pyquipu-runtime/pyproject.toml` 中的 `pyquipu-spec` 约束至 `~= 0.2.0`。
2. 修正 `packages/pyquipu-test-utils/pyproject.toml` 中的 `typer` 约束至 `typer >= 0.9.0`。
3. 修正根目录 `pyproject.toml` 中的 `pyneedle-pointer` 约束至 `~= 0.2.1`。
4. 在 `.github/workflows/ci.yml` 的 `quality-checks` 作业中增加执行 `scripts/check_monorepo_deps.py` 的步骤。

### 基本原理
通过 `patch_file` 精确修复各 `pyproject.toml` 中声明的依赖版本。在 CI 流程中，在 `uv sync` 同步完依赖之后、运行测试之前执行依赖检查脚本，一旦发现依赖违规直接报错阻断，保证主分支的依赖卫生。

### 标签
#intent/fix #flow/ready #priority/high #comp/build #concept/config #scope/dx #ai/instruct #task/domain/tooling #task/object/monorepo-deps #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 修复 `pyquipu-runtime` 中的内部包依赖版本

我们将 `pyquipu-spec` 依赖版本从 `~= 0.1.1` 修正为与整个工作区一致的 `~= 0.2.0`。

~~~~~act
patch_file
packages/pyquipu-runtime/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.1.1",
    "pyquipu-common ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-common ~= 0.2.0",
    "typer >= 0.9.0"
]
~~~~~

#### Acts 2: 修复 `pyquipu-test-utils` 中的裸依赖

将 `typer` 约束统一为 `typer >= 0.9.0`。

~~~~~act
patch_file
packages/pyquipu-test-utils/pyproject.toml
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyneedle-bus ~= 0.1.4",
    "pyneedle-pointer ~= 0.2.1",
    "typer"
]
~~~~~
~~~~~toml
dependencies = [
    "pyquipu-spec ~= 0.2.0",
    "pyquipu-engine ~= 0.4.0",
    "pyneedle-bus ~= 0.1.4",
    "pyneedle-pointer ~= 0.2.1",
    "typer >= 0.9.0"
]
~~~~~

#### Acts 3: 修复根目录 `pyproject.toml` 中的裸依赖

将 `optional-dependencies.dev` 中的 `pyneedle-pointer` 统一为 `~= 0.2.1`。

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
    "pyneedle-pointer",
]
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

#### Acts 4: 将依赖检查脚本集成到 CI 配置文件中

在 `.github/workflows/ci.yml` 的 `quality-checks` 作业中加入运行 `scripts/check_monorepo_deps.py` 的步骤。

~~~~~act
patch_file
.github/workflows/ci.yml
~~~~~
~~~~~yaml
      # 步骤 4: 使用 uv sync 基于 lockfile 同步 workspace 及开发依赖
      - name: Sync workspace dependencies with uv
        run: |
          source $HOME/.cargo/env
          uv sync --frozen --all-packages --extra dev

      # 步骤 5: 运行 Ruff (代码风格检查和静态分析)
~~~~~
~~~~~yaml
      # 步骤 4: 使用 uv sync 基于 lockfile 同步 workspace 及开发依赖
      - name: Sync workspace dependencies with uv
        run: |
          source $HOME/.cargo/env
          uv sync --frozen --all-packages --extra dev

      # 步骤 5: 检查 Monorepo 依赖一致性
      - name: Check Monorepo Dependency Consistency
        run: |
          python scripts/check_monorepo_deps.py

      # 步骤 6: 运行 Ruff (代码风格检查和静态分析)
~~~~~

### 下一步建议

1. **执行并验证**：
   在本地终端中运行检查脚本进行验证：
   ```bash
   python scripts/check_monorepo_deps.py
   ```
2. **更新 lock 文件**：
   因为修改了 `pyproject.toml` 中的依赖约束，请执行以下命令更新 `uv.lock`：
   ```bash
   uv lock
   ```
3. **提交变更**：
   验证无误后，通知我生成 `[COMMIT]` 计划以将更改提交至 Git。
