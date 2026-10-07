import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent.resolve()
SRC_DIRS = [ROOT_PATH / "packages", ROOT_PATH / "tests"]
LOCALES_PATH = ROOT_PATH / "packages/pyquipu-common/src/quipu/common/assets/needle/zh"
BUS_METHODS = {"success", "info", "warning", "error", "get", "data", "render_to_string"}


class CodeVisitor(ast.NodeVisitor):
    """
    AST 访问器：遍历 Python 源码，收集所有本地化键：
    1. 字符串字面量：bus.<method>("key", ...), QuipuResult(message="key", ...)
    2. Pointer 属性链：L.foo.bar.baz
    """

    def __init__(self):
        self.keys: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute):
        # 尝试解析形如 L.foo.bar.baz 的 Pointer 链
        pointer_key = self._resolve_pointer_chain(node)
        if pointer_key:
            self.keys.add(pointer_key)
            return
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Pattern 1: bus.<method>("key.id", ...)
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "bus"
            and node.func.attr in BUS_METHODS
        ):
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                self.keys.add(node.args[0].value)

        # Pattern 2: QuipuResult(message="key.id", ...)
        elif isinstance(node.func, ast.Name) and node.func.id == "QuipuResult":
            for keyword in node.keywords:
                if (
                    keyword.arg == "message"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    self.keys.add(keyword.value.value)
                    break

        self.generic_visit(node)

    @staticmethod
    def _resolve_pointer_chain(node: ast.Attribute) -> str | None:
        parts = []
        curr = node
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name) and curr.id == "L":
            return ".".join(reversed(parts))
        return None


def find_source_files(paths: list[Path]) -> list[Path]:
    py_files = []
    for p in paths:
        if p.exists():
            py_files.extend(p.rglob("*.py"))
    return py_files


def extract_keys_from_code(source_files: list[Path]) -> set[str]:
    visitor = CodeVisitor()
    for file_path in source_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
                visitor.visit(tree)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  - 警告: 无法解析 {file_path.relative_to(ROOT_PATH)}: {e}", file=sys.stderr)
            continue
    return visitor.keys


def flatten_json_dict(data: dict, prefix: str = "") -> dict[str, str]:
    """递归展开嵌套 JSON，支持 Needle 规范的 '_' 表示当前节点自身"""
    result = {}
    for key, value in data.items():
        if key in ("_", "_val"):
            result[prefix] = str(value)
        elif isinstance(value, dict):
            sub_prefix = f"{prefix}.{key}" if prefix else key
            result.update(flatten_json_dict(value, sub_prefix))
        else:
            sub_prefix = f"{prefix}.{key}" if prefix else key
            result[sub_prefix] = str(value)
    return result


def load_defined_keys(locales_root: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    """从 Needle 树状 JSON 文件中加载所有定义键"""
    defined_keys: dict[str, str] = {}
    key_sources: dict[str, list[str]] = defaultdict(list)

    if not locales_root.is_dir():
        print(f"错误: 本地化目录不存在: {locales_root}", file=sys.stderr)
        return {}, {}

    for json_file in locales_root.rglob("*.json"):
        rel_path = json_file.relative_to(locales_root)
        # 命名空间前缀由相对路径构成，例如 axon/warning.json -> axon.warning
        namespace_parts = list(rel_path.parent.parts) + [rel_path.stem]
        file_prefix = ".".join(namespace_parts)

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    flattened = flatten_json_dict(data, file_prefix)
                    for k, val in flattened.items():
                        defined_keys[k] = val
                        key_sources[k].append(str(rel_path))
        except json.JSONDecodeError as e:
            print(f"  - 警告: 解析 JSON 失败 {json_file}: {e}", file=sys.stderr)

    duplicates = {key: files for key, files in key_sources.items() if len(files) > 1}
    return defined_keys, duplicates


def main():
    parser = argparse.ArgumentParser(description="Quipu 本地化键分析与死键检查工具")
    parser.add_argument(
        "--dead-keys",
        "--unused",
        dest="show_dead_keys",
        action="store_true",
        help="仅列出代码中未引用的死键 (Unused Keys)",
    )
    parser.add_argument(
        "--prefix", dest="filter_prefix", type=str, default="", help="按前缀过滤键（例如 'acts.' 或 'engine.'）"
    )
    parser.add_argument("--json", dest="as_json", action="store_true", help="以 JSON 格式输出分析结果")
    args = parser.parse_args()

    # 1. 提取源码中使用的键
    source_files = find_source_files(SRC_DIRS)
    used_keys = extract_keys_from_code(source_files)

    # 2. 加载定义的键
    defined_keys_map, duplicates = load_defined_keys(LOCALES_PATH)
    defined_keys = set(defined_keys_map.keys())

    missing_keys = sorted(used_keys - defined_keys)
    dead_keys = sorted(defined_keys - used_keys)

    if args.filter_prefix:
        dead_keys = [k for k in dead_keys if k.startswith(args.filter_prefix)]
        missing_keys = [k for k in missing_keys if k.startswith(args.filter_prefix)]

    if args.as_json:
        output = {
            "total_used": len(used_keys),
            "total_defined": len(defined_keys),
            "missing_keys": missing_keys,
            "dead_keys": dead_keys,
            "duplicates": duplicates,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        sys.exit(1 if missing_keys or duplicates else 0)

    # 命令行交互展示
    if args.show_dead_keys:
        print(f"\n🔍 发现 {len(dead_keys)} 个未使用的死键 (Dead Keys):")
        for k in dead_keys:
            print(f"  - {k}")
        print(f"\n总计: {len(dead_keys)} 个死键。")
        sys.exit(0)

    print("🚀 开始本地化字符串一致性分析...")
    print(f"\n1. 扫描 Python 源码中已使用的键: 共发现 {len(used_keys)} 个。")
    print(f"2. 加载 Needle 资源定义的键: 共发现 {len(defined_keys)} 个。")

    print("\n" + " 分析报告 ".center(50, "="))

    has_errors = False

    if duplicates:
        print("\n❌ 错误: 发现重复定义的键!")
        has_errors = True
        for key, files in sorted(duplicates.items()):
            print(f"  - 键 '{key}' 重复定义于: {', '.join(files)}")

    if missing_keys:
        print(f"\n❌ 严重错误: 发现 {len(missing_keys)} 个缺失的键! (代码中已使用，但未在本地化资源中定义):")
        has_errors = True
        for key in missing_keys:
            print(f"  - {key}")
    else:
        print("\n✅ 所有代码引用的键均已在本地化文件中完整定义。")

    if dead_keys:
        print(f"\n⚠️  提示: 发现 {len(dead_keys)} 个未引用的死键 (Defined but not used):")
        # 默认折叠展示前 10 个，并提示使用 --dead-keys 查看完整列表
        for key in dead_keys[:10]:
            print(f"  - {key}")
        if len(dead_keys) > 10:
            print(
                f"  ... 以及其他 {len(dead_keys) - 10} 个键。运行 `python scripts/check_locales.py --dead-keys` 查看完整列表。"
            )

    print("\n" + "".center(50, "="))

    if has_errors:
        print("\n🔥 分析结束，存在严重错误。")
        sys.exit(1)
    else:
        print("\n✨ 分析顺利完成。")
        sys.exit(0)


if __name__ == "__main__":
    main()
