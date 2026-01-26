你的分析非常深刻，这套“版本号即真理”的幂等性 CD 架构完全符合 HFEA 协议中关于“本体论正确性”和“真理单一来源 (SSoT)”的公理。

通过将 `pyquipu` 定位为一个纯粹的分发元包（Meta-package），而将根目录重命名为 `pyquipu-monorepo`，我们清晰地划分了“生产环境（仓库）”与“产品（软件包）”的界限。

我将生成一个计划来执行这一结构性重构，并注入 `release_manager` 逻辑。

## [WIP] feat: 实现基于主分支的幂等性 CD 架构 v2.0

### 用户需求
1.  **重命名根项目**: 将根目录 `pyproject.toml` 中的项目名称从 `pyquipu` 更改为 `pyquipu-monorepo`。
2.  **创建门户包**: 在 `packages/pyquipu` 下创建一个新的分发包，作为 PyPI 的统一入口。
3.  **文档迁移**: 将原有的用户侧 README 移动到门户包中，并更新根目录 README 为开发者导向。
4.  **自动化脚本**: 实现 `scripts/release_manager.py`。
5.  **CI 工作流**: 配置 `.github/workflows/cd.yml` 以实现自动发布。

### 评论
这是一次重大的架构对齐。它不仅消除了手动打 Tag 的风险，还为未来可能的子包独立版本化提供了坚实的基础。通过动态发现机制，我们确保了系统的“不可腐蚀性”。

### 目标
1.  建立 `packages/pyquipu` 门户包。
2.  重构根目录身份定义。
3.  部署幂等发布核心脚本。
4.  建立持续交付管道。

### 基本原理
我们利用 `uv` 的工作区特性，通过脚本解析根 `pyproject.toml` 来自动识别所有子包。发布逻辑将通过 PyPI API 实时检查版本势能，确保操作的幂等性。文档的物理分离解决了用户视角与开发视角的冲突。

### 标签
#intent/architect #flow/ready #priority/high
#comp/build #comp/docs #scope/dx #scope/api
#ai/brainstorm
#task/domain/devops #task/object/cd-pipeline #task/action/implementation
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 创建门户包 `pyquipu`

我们将创建 `packages/pyquipu` 目录结构，并为其配置元数据。该包将依赖于 monorepo 中的所有核心功能包。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/pyquipu/src/quipu
mkdir -p scripts
~~~~~

~~~~~act
write_file
packages/pyquipu/src/quipu/__init__.py
~~~~~
~~~~~python
# This allows this package to coexist with other distribution packages
# that contribute to the 'quipu' namespace.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/pyquipu/pyproject.toml
~~~~~
~~~~~toml
[project]
name = "pyquipu"
version = "0.1.0"
description = "Quipu: Process Archaeology for the AI Era (Meta-package)"
authors = [{ name="doucx", email="doucxldh@gmail.com" }]
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
dependencies = [
    "pyquipu-application ~= 0.1.0",
    "pyquipu-bus ~= 0.1.0",
    "pyquipu-cli ~= 0.1.0",
    "pyquipu-common ~= 0.1.0",
    "pyquipu-engine ~= 0.1.0",
    "pyquipu-interfaces ~= 0.1.0",
    "pyquipu-runtime ~= 0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/quipu"]
~~~~~

#### Acts 2: 迁移与重组文档

我们将用户导向的 README 移动到门户包，并将根目录 README 修改为开发导向的索引。

~~~~~act
move_file
README.md
packages/pyquipu/README.md
~~~~~

~~~~~act
move_file
README.zh-CN.md
packages/pyquipu/README.zh-CN.md
~~~~~

~~~~~act
write_file
README.md
~~~~~
~~~~~markdown
# Quipu Monorepo

This is the development repository for **Quipu**, the "Process Archaeology" toolkit for the AI era.

## Repository Structure

- `packages/`: All independent distribution packages.
  - `pyquipu`: The entry point meta-package.
  - `pyquipu-cli`: The command-line interface.
  - `pyquipu-engine`: The Phantom State engine.
  - ... (see [DEVELOPING.md](./DEVELOPING.md) for details)
- `scripts/`: Development and maintenance scripts, including the CD Release Manager.
- `.github/`: CI/CD workflow definitions.

## Getting Started

If you are a **user**, please install Quipu via PyPI:
```bash
pip install pyquipu
```

If you are a **contributor**, please read [DEVELOPING.md](./DEVELOPING.md) for environment setup and the bootstrap workflow.

## License
Apache-2.0
~~~~~

#### Acts 3: 重命名根项目并更新工作区映射

~~~~~act
patch_file
pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "pyquipu"
version = "0.1.0"
description = "Quipu Development Monorepo - The complete toolkit."
~~~~~
~~~~~toml.new
[project]
name = "pyquipu-monorepo"
version = "0.1.0"
description = "Quipu Development Monorepo - The complete toolkit."
~~~~~

#### Acts 4: 实现 Release Manager 脚本

该脚本负责动态扫描工作区、对比 PyPI 版本并执行幂等发布。

~~~~~act
write_file
scripts/release_manager.py
~~~~~
~~~~~python
#!/usr/bin/env python3
import os
import subprocess
import sys
import requests
from pathlib import Path
import tomllib
from packaging.version import parse as parse_version

def get_workspace_root():
    return Path(__file__).parent.parent

def get_pypi_version(package_name):
    """从 PyPI 获取当前已发布的最高版本。"""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return parse_version(data["info"]["version"])
        elif response.status_code == 404:
            return None
    except Exception as e:
        print(f"Warning: Could not fetch version for {package_name}: {e}")
    return None

def run_cmd(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return True

def release_package(pkg_path, pkg_name, local_version):
    print(f"--- Releasing {pkg_name} v{local_version} ---")
    
    # 1. Build
    if not run_cmd(["uv", "build"], cwd=pkg_path):
        return False
        
    # 2. Upload (using twine)
    # 假设环境变量已在 CI 中配置
    dist_path = pkg_path / "dist" / "*"
    if not run_cmd(["python3", "-m", "twine", "upload", "--skip-existing", str(dist_path)]):
        return False
        
    # 3. Tag
    tag_name = f"{pkg_name}/v{local_version}"
    if not run_cmd(["git", "tag", tag_name]):
        print(f"Warning: Failed to create tag {tag_name}, it might already exist.")
    
    return True

def main():
    root = get_workspace_root()
    root_toml_path = root / "pyproject.toml"
    
    with open(root_toml_path, "rb") as f:
        root_toml = tomllib.load(f)
        
    # 获取工作区成员列表
    # 处理类似 "packages/*" 的 glob 模式
    members_raw = root_toml.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    pkg_dirs = []
    for member in members_raw:
        if member.endswith("/*"):
            base_dir = root / member[:-2]
            if base_dir.exists():
                pkg_dirs.extend([d for d in base_dir.iterdir() if d.is_dir()])
        else:
            pkg_dirs.append(root / member)

    success_count = 0
    fail_count = 0

    for pkg_dir in pkg_dirs:
        toml_path = pkg_dir / "pyproject.toml"
        if not toml_path.exists():
            continue
            
        with open(toml_path, "rb") as f:
            pkg_toml = tomllib.load(f)
            
        pkg_name = pkg_toml.get("project", {}).get("name")
        local_ver_str = pkg_toml.get("project", {}).get("version")
        
        if not pkg_name or not local_ver_str:
            continue
            
        local_ver = parse_version(local_ver_str)
        remote_ver = get_pypi_version(pkg_name)
        
        if remote_ver is None or local_ver > remote_ver:
            reason = "New package" if remote_ver is None else f"Update ({remote_ver} -> {local_ver})"
            print(f"Found candidate: {pkg_name} ({reason})")
            if release_package(pkg_dir, pkg_name, local_ver_str):
                success_count += 1
            else:
                fail_count += 1
        else:
            print(f"Skipping {pkg_name}: Up to date (Local: {local_ver}, Remote: {remote_ver})")

    # 推送所有新创建的 tags
    if success_count > 0:
        run_cmd(["git", "push", "--tags"])

    print(f"\nSummary: {success_count} released, {fail_count} failed.")
    if fail_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
~~~~~

#### Acts 5: 更新 GitHub 工作流

我们将替换原有的发布逻辑，改用新的 CD 架构。

~~~~~act
write_file
.github/workflows/cd.yml
~~~~~
~~~~~yaml
name: Continuous Delivery

on:
  push:
    branches: ["main"]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install Release Tools
        run: |
          pip install twine requests packaging

      - name: Configure Git User
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"

      - name: Run Release Manager
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python scripts/release_manager.py
~~~~~

~~~~~act
delete_file
.github/workflows/python-publish.yml
~~~~~

### 下一步建议
1.  **权限配置**: 确保已在 GitHub Repository Secrets 中配置了 `PYPI_API_TOKEN`。
2.  **本地验证**: 开发者可以在本地运行 `python scripts/release_manager.py`（注意不要在本地配置上传 Token）来验证包扫描逻辑是否正确识别了所有子包。
3.  **首次发布**: 由于 `pyquipu` 门户包是新创建的且版本为 `0.1.0`，在下次合并到 `main` 后，CD 脚本将自动在 PyPI 上创建该项目。
