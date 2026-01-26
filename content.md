这是一个非常典型的 **“通配符未展开” (Wildcard Expansion Failure)** 错误。

**根本原因：**
在 `scripts/release_manager.py` 的 `release_package` 函数中，我们使用了如下代码：
```python
dist_path = pkg_path / "dist" / "*"
run_cmd(["python3", "-m", "twine", "upload", "--skip-existing", str(dist_path)])
```

在 Python 的 `subprocess.run`（由 `run_cmd` 调用）中，默认是不通过 Shell 执行命令的。这意味着 **`*` 号不会被自动展开为文件列表**。`twine` 接收到的参数是字符串文字 `"/.../dist/*"`，它在磁盘上找不到一个名字真的叫 `*` 的文件，因此报错（由于 `twine` 的某些版本会将此类错误输出到 `stdout` 而非 `stderr`，导致你的日志中 `Error:` 后面是空的）。

我们需要在 Python 层面使用 `glob` 或 `pathlib` 显式地展开通配符，将匹配到的所有文件路径作为独立的参数传递给 `twine`。此外，为了保证发布的纯净性，我们在构建前应该先清理 `dist` 目录。

## [WIP] fix: 修复 Release Manager 中的通配符解析与参数传递问题

### 错误分析
1.  **通配符失效**: `subprocess.run` 在不启用 `shell=True` 时不会解析路径中的 `*`。
2.  **错误捕获不全**: `run_cmd` 仅打印了 `stderr`，但许多工具（如 `twine`）的逻辑错误会输出到 `stdout`。
3.  **构建污染风险**: 缺少对 `dist` 目录的清理逻辑，可能导致旧版本的 wheel 包被意外上传。

### 用户需求
修复 CD 脚本，确保包能正确上传到 PyPI。

### 目标
1.  修改 `scripts/release_manager.py`，使用 `pathlib` 动态展开 `dist/*` 文件列表。
2.  增加 `dist` 目录清理步骤。
3.  改进 `run_cmd`，在失败时同时打印 `stdout` 和 `stderr` 以便调试。

### 标签
#intent/fix #flow/ready #priority/high
#comp/build #concept/executor #scope/dx
#ai/instruct
#task/domain/devops #task/object/release-manager #task/action/bug-fix
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 修复 `scripts/release_manager.py` 的核心逻辑

我们将重写 `run_cmd` 以增强调试能力，并修复 `release_package` 中的路径处理逻辑。

~~~~~act
write_file
scripts/release_manager.py
~~~~~
~~~~~python
#!/usr/bin/env python3
import os
import subprocess
import sys
import shutil
import requests
from pathlib import Path
import tomllib
from packaging.version import parse as parse_version

def get_workspace_root():
    return Path(__file__).parent.parent

def get_pypi_version(package_name):
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
        print(f"--- STDOUT ---\n{result.stdout}")
        print(f"--- STDERR ---\n{result.stderr}")
        return False
    return True

def release_package(pkg_path, pkg_name, local_version):
    print(f"--- Releasing {pkg_name} v{local_version} ---")
    
    # 0. Clean old artifacts
    dist_dir = pkg_path / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # 1. Build
    if not run_cmd(["uv", "build"], cwd=pkg_path):
        return False
        
    # 2. Expand wildcards for twine
    # Twine needs a list of actual file paths
    dist_files = [str(f) for f in dist_dir.glob("*") if f.is_file()]
    if not dist_files:
        print(f"Error: No build artifacts found in {dist_dir}")
        return False

    # 3. Upload (using twine)
    upload_cmd = ["python3", "-m", "twine", "upload", "--skip-existing"] + dist_files
    if not run_cmd(upload_cmd):
        return False
        
    # 4. Tag
    tag_name = f"{pkg_name}/v{local_version}"
    # Use --force to allow re-tagging if a previous run failed mid-way
    if not run_cmd(["git", "tag", "-f", tag_name]):
        print(f"Warning: Failed to create tag {tag_name}")
    
    return True

def main():
    root = get_workspace_root()
    root_toml_path = root / "pyproject.toml"
    
    with open(root_toml_path, "rb") as f:
        root_toml = tomllib.load(f)
        
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

    if success_count > 0:
        # Push tags with --force to handle updated tags from retries
        run_cmd(["git", "push", "origin", "--tags", "-f"])

    print(f"\nSummary: {success_count} released, {fail_count} failed.")
    if fail_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
~~~~~

### 下一步建议

1.  **重试 CD 工作流**: 提交此修复后，GitHub Actions 会自动重新运行。
2.  **检查输出**: 如果仍然失败，由于我们现在同时捕获了 `STDOUT` 和 `STDERR`，你将在 GitHub 的日志中看到 `twine` 报错的详细原因（例如认证失败、包名冲突等）。
3.  **Git Tag 策略**: 我增加了 `-f` (force) 参数来创建和推送 Tag。这是因为在幂等 CD 中，如果一次运行在上传成功后但在推送 Tag 前崩溃，下一次重试需要能够覆盖那个本地已经存在但远程不存在的 Tag。
