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