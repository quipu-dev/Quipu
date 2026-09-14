你的分析非常精准。

在基于 `uv` 的 Monorepo 项目中，使用 `uv pip install -e .[dev]` 会绕过 `uv.lock`，退化为在线动态依赖解析，不仅无法保障环境的确定性与复现性，还无法正确处理本地多包 workspace（工作空间）内部的互引与依赖拓扑。规范的做法应是通过 `uv sync --frozen --all-packages --extra dev` 进行确定性同步，并通过 `uv run` 执行代码检查与测试套件。

我已为你生成了调整 CI 工作流的计划。

## [WIP] fix(ci): 使用 uv sync 替代 uv pip install 以支持 lockfile 与 workspace

### 错误分析

1. **绕过 Lockfile 机制**：原 CI 步骤中使用 `uv pip install -e .[dev]`，该命令本质上模拟 `pip` 的动态解析与安装行为，忽略了仓库中已有的 `uv.lock`，导致 CI 环境运行时的第三方依赖版本与本地开发环境不一致。
2. **丢失 Workspace 拓扑支持**：当前仓库是包含多个包（如 `pyquipu-cli`, `pyquipu-engine`, `pyquipu-test-utils` 等）的 Monorepo。原方案仅以 editable 方式安装顶层包，容易导致 workspace 内部子包在相互引用或运行测试时出现模块查找或版本覆盖问题。
3. **环境激活冗余**：手动创建 `.envs/dev` 并通过 `source` 激活容易受环境路径影响，而使用 `uv run` 可以由 uv 自动感知并管理虚拟环境，执行更加稳定。

### 用户需求

更新 `.github/workflows/ci.yml`，使用标准的 `uv sync` 命令结合 `uv.lock` 锁定文件安装整个 workspace 的依赖（包括开发依赖 `dev`），并使用 `uv run` 执行后续的 Ruff 与 Pytest 步骤。

### 评论

这是一个非常关键且及时的 CI 质量加固。确保 CI 环境与本地开发环境严格对齐是避免“在我机器上是好的”这一问题的核心前提，同时充分利用了 `uv` 原生对 monorepo/workspace 的高效支持。

### 目标

1. 移除 `ci.yml` 中手动的 `uv venv` 和 `uv pip install` 逻辑。
2. 引入 `uv sync --frozen --all-packages --extra dev`，确保依赖严格受 `uv.lock` 约束，且所有子包及开发依赖均被正确安装。
3. 将 Ruff 检查和 Pytest 测试执行命令迁移至 `uv run`。

### 基本原理

`uv sync` 是 uv 针对项目和工作空间推荐的核心工作流命令：
- `--frozen`：保证在不修改 `uv.lock` 的前提下同步依赖，如果 lockfile 过期或缺失则立刻阻断 CI。
- `--all-packages`：同步 monorepo 中声明的所有 workspace 成员。
- `--extra dev`：同步根目录声明的 `dev` 开发依赖（包含 ruff, pytest, pytest-cov 等）。
- `uv run`：自动在已同步的虚拟环境中运行工具，无需手动 `source activate`。

### 标签

#intent/fix #flow/ready #priority/high #comp/build #scope/dx #ai/instruct #task/domain/build #task/object/ci-workflow #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 更新 `.github/workflows/ci.yml` 中的依赖安装与测试流程

我们将原有的 `uv pip install` 与手动激活虚拟环境逻辑替换为标准的 `uv sync` 与 `uv run`。

~~~~~act
patch_file
.github/workflows/ci.yml
~~~~~
~~~~~yaml
      # 步骤 4: 创建虚拟环境并安装开发依赖
      #   这模拟了 `setup_dev.py` 中创建 dev 环境的过程
      - name: Create venv and install dev dependencies
        run: |
          # 激活 uv
          source $HOME/.cargo/env
          # 创建虚拟环境
          uv venv .envs/dev
          # 安装开发和测试工具，以及所有本地包（可编辑模式）
          uv pip install -p .envs/dev \
            -e .[dev]

      # 步骤 5: 运行 Ruff (代码风格检查和静态分析)
      #   使用 --check 标志，如果代码格式不正确，CI 会失败
      - name: Run Ruff Linter and Formatter Check
        run: |
          source .envs/dev/bin/activate
          ruff check .
          ruff format --check .

      # 步骤 6: 运行 Pytest
      #   pytest 会自动读取 pyproject.toml 中的配置
      - name: Run Pytest with Coverage
        run: |
          source .envs/dev/bin/activate
          pytest
~~~~~
~~~~~yaml
      # 步骤 4: 使用 uv sync 基于 lockfile 同步 workspace 及开发依赖
      - name: Sync workspace dependencies with uv
        run: |
          source $HOME/.cargo/env
          uv sync --frozen --all-packages --extra dev

      # 步骤 5: 运行 Ruff (代码风格检查和静态分析)
      #   使用 --check 标志，如果代码格式不正确，CI 会失败
      - name: Run Ruff Linter and Formatter Check
        run: |
          source $HOME/.cargo/env
          uv run ruff check .
          uv run ruff format --check .

      # 步骤 6: 运行 Pytest
      #   pytest 会自动读取 pyproject.toml 中的配置
      - name: Run Pytest with Coverage
        run: |
          source $HOME/.cargo/env
          uv run pytest
~~~~~

### 下一步建议

1. **本地同步验证**：在本地运行 `uv sync --all-packages --extra dev` 并确认 `uv.lock` 已提交且最新。
2. **CD 流程审查**：审查 `.github/workflows/cd.yml`，若有类似的打包或环境配置步骤，也可考虑统一为 uv 标准规范。
