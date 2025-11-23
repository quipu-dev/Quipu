import logging
import re
from pathlib import Path
from typing import Dict, Optional
import yaml
from .models import AxonNode
from datetime import datetime

logger = logging.getLogger(__name__)

# 文件名格式: {input_hash}_{output_hash}_{timestamp}.md
# 示例: 000..._a1b2c3..._20231028120000.md
FILENAME_PATTERN = re.compile(
    r"([0-9a-f]{40}|_{40})_([0-9a-f]{40})_(\d{14})\.md"
)
# 注意: input_hash 可能是 40 个下划线，代表创世节点
# Python 3.11+ re.Scanner is much faster, but this is fine for now.

def _parse_frontmatter(text: str) -> tuple[Dict, str]:
    """从 Markdown 文本中分离 YAML frontmatter 和主体内容"""
    if not text.startswith("---"):
        return {}, text
    
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text # 格式不完整

    _, frontmatter_str, content = parts
    try:
        meta = yaml.safe_load(frontmatter_str) or {}
        return meta, content.strip()
    except yaml.YAMLError:
        return {}, text # YAML 解析失败

def load_history_graph(history_dir: Path) -> Dict[str, AxonNode]:
    """
    扫描历史目录，加载所有节点，并构建一个包含父子关系的图。
    返回以 output_tree_hash 为键的节点字典。
    """
    graph: Dict[str, AxonNode] = {}
    if not history_dir.exists():
        return graph

    # --- 第一遍: 加载所有独立的节点 ---
    for file_path in history_dir.glob("*.md"):
        match = FILENAME_PATTERN.match(file_path.name)
        if not match:
            logger.warning(f"跳过格式不匹配的历史文件: {file_path.name}")
            continue
        
        input_hash, output_hash, ts_str = match.groups()
        
        try:
            full_content = file_path.read_text("utf-8")
            meta, body_content = _parse_frontmatter(full_content)
            
            node = AxonNode(
                input_tree=input_hash,
                output_tree=output_hash,
                timestamp=datetime.strptime(ts_str, "%Y%m%d%H%M%S"),
                filename=file_path,
                node_type=meta.get("type", "unknown"),
                parent_hint=meta.get("parent_hint"),
                content=body_content
            )
            graph[output_hash] = node
        except Exception as e:
            logger.error(f"加载历史节点失败 {file_path.name}: {e}")

    # --- 第二遍: 连接父子关系 ---
    for node in graph.values():
        # 节点的 input_tree 就是其父节点的 output_tree
        if node.input_tree in graph:
            parent_node = graph[node.input_tree]
            node.parent = parent_node
            parent_node.children.append(node)

    # 为所有节点的子列表按时间排序，确保导航行为一致
    for node in graph.values():
        node.children.sort(key=lambda n: n.timestamp)

    logger.info(f"从 '{history_dir}' 加载并连接了 {len(graph)} 个历史节点。")
    return graph