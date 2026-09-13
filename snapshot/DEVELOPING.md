# Quipu 开发指南 (The Quipu Development Workflow)

本文档介绍了如何在一个“依靠 Quipu 构建 Quipu”的自举环境中安全、高效地工作。

## 核心概念：双环境隔离 (Dual-Environment Separation)

为了解决“修改工具本身会导致工具崩溃”的死锁问题，我们维护了两个隔离的环境：

1. **🔵 Stable 环境 (`qs`)**:
   - **角色**: 医生 / 基础设施。
   - **本质**: 直接从 PyPI 安装的线上稳定发布版 (`pyquipu-cli`)。
   - **用途**: **你的生产力工具**。用它来执行 Plan 文件、重构源码和代码修改。它完全独立于本地工作树，无论本地代码怎么改坏，它都能正常运行。
2. **🟢 Dev 环境 (`qd`)**:
   - **角色**: 病人 / 被测对象。
   - **本质**: 当前本地源码环境，由 `uv sync --extra dev` 管理的可编辑工作区。
   - **用途**: **你的测试与调试对象**。用它来跑本地 CLI 验证、排查 bug、验证新功能。它实时反映本地源码的最新变动。

---

## 快速开始

### 1. 初始化本地开发环境

首次克隆项目或拉取代码后，在项目根目录执行：

```bash
# 1. 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 一键同步本地开发环境依赖 (生成 .venv)
uv sync --extra dev
```

### 2. 配置 CLI 别名

为了便捷地在 stable 和 dev 之间切换，建议将别名加入你的 Shell 配置文件（如 `~/.bashrc`、`~/.zshrc` 或 `~/.config/fish/config.fish`）：

**Bash / Zsh:**
```bash
# 稳定版：直接通过 PyPI 隔离运行稳定版 CLI
alias qs="uvx --from pyquipu-cli quipu"

# 开发版：运行当前本地工作树的代码
alias qd="uv run quipu"
```

> *注：如果你偏好手动将 `pyquipu-cli` 安装到全局或单独环境中（如 `uv tool install pyquipu-cli`），也可将 `qs` 指向对应的可执行文件路径。*

**Fish:**
```fish
alias qs="uvx --from pyquipu-cli quipu"
alias qd="uv run quipu"
```

---

## 常用命令速查

| 命令 | 方式 / 机制 | 用途 |
| :--- | :--- | :--- |
| **`qs`** | `uvx --from pyquipu-cli quipu` | **稳定执行工具**。用这个来跑 `Plan.md`、修改/生成代码。 |
| **`qd`** | `uv run quipu` (`.venv`) | **开发调试对象**。用于手动调试和验证本地新功能。 |
| **`uv run pytest`** | 本地虚拟环境测试套件 | **运行测试**。运行单元测试与集成测试。 |
| **`uv run ruff check / format`** | 本地代码检查器 | **代码检查与格式化**。代码质量与规范检查。 |

---

## 标准开发循环 (The Loop)

### 场景 A：常规功能开发

1. **编写计划**: 创建 `feat_xxx.md`。
2. **执行修改**: 使用 **Stable** 环境执行计划，自动修改源码。
   ```bash
   qs run feat_xxx.md
   ```
3. **验证代码**:
   ```bash
   # 1. 运行测试
   uv run pytest

   # 2. 手动运行开发版 CLI 验证新特性
   qd --help
   ```

### 场景 B：依赖更新或子包注册

如果在 `pyproject.toml` 或工作区子目录中增删了依赖包，只需重新同步：

```bash
uv sync --extra dev
```

---

## 故障排除

### Q: 我把本地代码写崩了，`qd` 报错无法运行，但我需要用 Quipu 来修复它。
**A**: 这正是双环境隔离的意义。`qs` 始终运行来自 PyPI 的独立稳定版本，不受本地破损源码影响。你可以直接继续使用：
```bash
qs run fix_bug.md
```

### Q: 新增了模块或子包后，测试报找不到模块？
**A**: 重新执行一次 `uv sync --extra dev` 即可自动重新同步本地工作区映射与依赖。
