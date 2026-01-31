import json
import os
from pathlib import Path
from typing import Any, Dict

# --- 配置 ---
SOURCE_DIR = Path("packages/pyquipu-bus/src/quipu/locales/zh")
TARGET_DIR = Path("packages/pyquipu-common/src/quipu/common/assets/needle/zh")

def load_source_files(source_dir: Path) -> Dict[str, str]:
    """读取源目录下的所有 JSON，并将其展平为点分隔的键值对。"""
    flat_data = {}
    
    if not source_dir.exists():
        print(f"❌ 源目录不存在: {source_dir}")
        return {}

    for file_path in source_dir.glob("*.json"):
        print(f"📖 读取: {file_path.name}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                # 假设现有文件可能是扁平的 key="a.b.c"，也可能是嵌套的
                # 我们统一将其展平，以便重新分配
                flatten_recursive(content, flat_data)
        except Exception as e:
            print(f"⚠️ 读取 {file_path} 失败: {e}")

    return flat_data

def flatten_recursive(data: Any, result: Dict[str, str], prefix: str = ""):
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else k
            flatten_recursive(v, result, new_key)
    else:
        result[prefix] = str(data)

def set_nested(d: Dict[str, Any], keys: list[str], value: str):
    """在字典中创建深层嵌套结构"""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value

def migrate():
    print("🚀 开始迁移 Quipu Locales 到 Needle 格式...")
    
    # 1. 加载数据
    flat_data = load_source_files(SOURCE_DIR)
    if not flat_data:
        print("❌ 未找到数据，中止。")
        return

    print(f"📊 共加载 {len(flat_data)} 条消息。")

    # 2. 重组结构
    # 结构: { "directory_name": { "filename": { nested_json_content } } }
    structure: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for full_key, message in flat_data.items():
        parts = full_key.split(".")
        
        if len(parts) >= 2:
            directory = parts[0]  # e.g., "acts"
            filename = parts[1]   # e.g., "basic"
            inner_keys = parts[2:] # e.g., ["success", "fileWritten"]
        else:
            # 处理只有一段的键，放入 'global' 目录的 'common.json' 中
            directory = "global"
            filename = "common"
            inner_keys = parts

        # 如果没有内部键（例如 key="acts.basic"），直接赋值
        if not inner_keys:
             # 这在 Needle 中对应 {"_": "message"}，或者作为叶子节点
             # 这里我们简单处理，假设大多数都有层级
             inner_keys = ["_val"] 

        # 初始化结构
        dir_dict = structure.setdefault(directory, {})
        file_dict = dir_dict.setdefault(filename, {})
        
        # 填充内容
        set_nested(file_dict, inner_keys, message)

    # 3. 写入文件
    if TARGET_DIR.exists():
        import shutil
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    count_files = 0
    for dirname, files in structure.items():
        dir_path = TARGET_DIR / dirname
        dir_path.mkdir(exist_ok=True)
        
        for filename, content in files.items():
            file_path = dir_path / f"{filename}.json"
            
            # 清理特殊的 _val 键 (如果有)
            # 这是一个简化的处理，实际情况可能需要更复杂的冲突解决
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            count_files += 1

    print(f"✨ 迁移完成！")
    print(f"📂 输出目录: {TARGET_DIR}")
    print(f"📄 生成文件: {count_files} 个")

if __name__ == "__main__":
    migrate()
