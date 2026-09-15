#!/usr/bin/env python3
"""Monorepo 依赖一致性与规范检查工具 (Dependency Linter for Monorepo).

功能：
1. 检查同一个依赖（无论第三方还是内部包）在所有子包及根目录中的版本约束规范是否全局唯一。
2. 检查内部包互引时，其版本约束是否能与当前 workspace 内该包的实际版本（project.version）兼容匹配。
3. 检查是否存在裸依赖（即缺少任何版本约束，如只写了 "typer"）。
4. CI/CD 友好：若有任何校验失败，返回非零状态码 (exit code 1)。
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 优先使用 Python 3.11 标准库 tomllib，3.10 回退至 tomli
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        print("[ERROR] 需要 tomllib (Python 3.11+) 或 tomli (Python 3.10: pip install tomli)。", file=sys.stderr)
        sys.exit(1)


# 匹配简单 PEP 508 依赖声明的正则：包名与版本说明符
# 例如: "typer >= 0.9.0", "pyneedle-bus ~= 0.1.4", "pyquipu"
DEP_REGEX = re.compile(
    r"^(?P<name>[A-Za-z0-9_.\-]+)(?:\s*(?P<marker>;.*))?$"
)
SPEC_SPLIT_REGEX = re.compile(
    r"^(?P<name>[A-Za-z0-9_.\-]+)\s*(?P<spec>(?:==|~=|>=|<=|>|<|!=).*)$"
)


@dataclass
class DepOccurrence:
    package_name: str
    file_path: Path
    raw_spec: str
    spec_version: str  # e.g., "~= 0.2.0" or "" (无版本约束)
    is_dev: bool = False


def parse_requirement_str(req_str: str) -> tuple[str, str]:
    """解析依赖字符串，返回 (归一化包名, 版本约束条件)."""
    # 剔除环境标记 (markers)，例如: 'pywin32 ; sys_platform == "win32"'
    clean_req = req_str.split(";")[0].strip()
    match = SPEC_SPLIT_REGEX.match(clean_req)
    if match:
        name = match.group("name").strip().lower().replace("_", "-")
        spec = match.group("spec").strip()
        return name, spec
    
    # 无版本号的情况
    name = clean_req.strip().lower().replace("_", "-")
    return name, ""


def find_repo_root() -> Path:
    """寻找 monorepo 根目录（包含根 pyproject.toml 且带有 workspace 配置）."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            if "workspace" in content:
                return current
        current = current.parent
    # 回退：以 scripts 的上一级作为根目录
    return Path(__file__).resolve().parent.parent


def check_version_compat(actual_ver: str, spec: str) -> bool:
    """简单校验版本约束是否匹配本地版本（主要防范 ~= 带来的主次版本不兼容）."""
    actual_parts = [int(p) for p in actual_ver.split(".") if p.isdigit()]
    if not actual_parts:
        return True

    # 针对常见的兼容操作符 ~= X.Y.Z
    tilde_match = re.match(r"^~=\s*([0-9.]+)", spec)
    if tilde_match:
        expected_parts = [int(p) for p in tilde_match.group(1).split(".") if p.isdigit()]
        # ~= 0.1.1 只能匹配 0.1.x (前两段必须完全一致)
        # ~= 0.2.0 只能匹配 0.2.x
        prefix_len = min(len(expected_parts) - 1 if len(expected_parts) > 1 else 1, len(actual_parts))
        if expected_parts[:prefix_len] != actual_parts[:prefix_len]:
            return False
        # 实际版本不得低于目标要求的起始版本
        if actual_parts < expected_parts:
            return False

    # 针对精确操作符 == X.Y.Z
    eq_match = re.match(r"^==\s*([0-9.]+)", spec)
    if eq_match:
        expected_parts = [int(p) for p in eq_match.group(1).split(".") if p.isdigit()]
        if actual_parts != expected_parts:
            return False

    return True


def run_checks() -> int:
    repo_root = find_repo_root()
    print(f"🔍 Monorepo 根目录: {repo_root}")

    # 1. 扫描所有 pyproject.toml
    pyproject_files: list[Path] = [repo_root / "pyproject.toml"]
    packages_dir = repo_root / "packages"
    if packages_dir.is_dir():
        pyproject_files.extend(packages_dir.glob("*/pyproject.toml"))

    workspace_pkg_versions: dict[str, str] = {}
    dep_map: dict[str, list[DepOccurrence]] = defaultdict(list)

    # 2. 收集各包信息及所有声明的依赖
    for p_file in pyproject_files:
        try:
            with open(p_file, "rb") as f:
                data: dict[str, Any] = tomllib.load(f)
        except Exception as e:
            print(f"[ERROR] 无法解析 TOML 文件: {p_file}: {e}", file=sys.stderr)
            return 1

        project = data.get("project", {})
        pkg_name = project.get("name", "").strip().lower().replace("_", "-")
        pkg_version = project.get("version", "").strip()

        if pkg_name and pkg_version:
            workspace_pkg_versions[pkg_name] = pkg_version

        # 收集生产依赖
        for dep_str in project.get("dependencies", []):
            req_name, spec = parse_requirement_str(dep_str)
            dep_map[req_name].append(
                DepOccurrence(
                    package_name=pkg_name,
                    file_path=p_file.relative_to(repo_root),
                    raw_spec=dep_str,
                    spec_version=spec,
                    is_dev=False,
                )
            )

        # 收集可选/开发依赖 (optional-dependencies)
        opt_deps = project.get("optional-dependencies", {})
        for _, deps in opt_deps.items():
            for dep_str in deps:
                req_name, spec = parse_requirement_str(dep_str)
                dep_map[req_name].append(
                    DepOccurrence(
                        package_name=pkg_name,
                        file_path=p_file.relative_to(repo_root),
                        raw_spec=dep_str,
                        spec_version=spec,
                        is_dev=True,
                    )
                )

    has_errors = False

    print(f"📦 扫描到 {len(workspace_pkg_versions)} 个 Workspace 包，共计 {len(dep_map)} 个声明依赖项。\n")

    # 3. 校验规则一：内部依赖版本匹配性检查
    print("📋 [检查项 1/3] 内部工作区依赖版本兼容性...")
    for target_pkg, actual_ver in workspace_pkg_versions.items():
        if target_pkg in dep_map:
            for occ in dep_map[target_pkg]:
                # 排除根项目引用 meta-package 的情况
                if occ.package_name == "pyquipu-monorepo":
                    continue
                if not occ.spec_version:
                    print(f"  ❌ 错误: '{occ.package_name}' ({occ.file_path}) 引用内部包 '{target_pkg}' 时未指定版本约束！")
                    has_errors = True
                elif not check_version_compat(actual_ver, occ.spec_version):
                    print(
                        f"  ❌ 错误: 内部依赖版本不匹配！\n"
                        f"     声明方: {occ.package_name} ({occ.file_path})\n"
                        f"     声明要求: {target_pkg} {occ.spec_version}\n"
                        f"     实际版本: {target_pkg} == {actual_ver}"
                    )
                    has_errors = True

    # 4. 校验规则二：第三方包版本一致性检查 (Single Version Policy)
    print("\n📋 [检查项 2/3] 依赖声明一致性 (唯一版本原则)...")
    for req_name, occurrences in dep_map.items():
        # 如果是依赖自身 monorepo 的包，且已经在上面的步骤里检查过了，只检查外部包与跨模块约束是否冲突
        # 收集所有不同的 spec_version（过滤掉空约束，空约束将在规则三检查）
        distinct_specs = {occ.spec_version for occ in occurrences if occ.spec_version}
        if len(distinct_specs) > 1:
            print(f"  ❌ 冲突: 依赖项 '{req_name}' 存在多个不一致的版本约束:")
            for occ in occurrences:
                print(f"     - [{occ.package_name}] ({occ.file_path}): {occ.raw_spec}")
            has_errors = True

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

    # 6. 最终汇总
    print("\n" + "=" * 60)
    if has_errors:
        print("❌ 检查失败！Monorepo 依赖关系存在不一致或违规，请根据上方提示修复。")
        return 1
    else:
        print("✅ 检查通过！所有包的依赖关系符合 Monorepo 规范且版本保持一致。")
        return 0


if __name__ == "__main__":
    sys.exit(run_checks())
