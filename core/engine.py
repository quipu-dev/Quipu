import logging
from pathlib import Path
from typing import Dict, Optional

from .git_db import GitDB
from .history import load_history_graph
from .models import AxonNode

logger = logging.getLogger(__name__)

class Engine:
    """
    Axon v4.2 状态引擎。
    负责协调 Git 物理状态和 Axon 逻辑图谱。
    """
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.axon_dir = self.root_dir / ".axon"
        self.history_dir = self.axon_dir / "history"
        
        self.git_db = GitDB(self.root_dir)
        self.history_graph: Dict[str, AxonNode] = {}
        self.current_node: Optional[AxonNode] = None

    def align(self) -> str:
        """
        核心对齐方法：确定 "我现在在哪"。
        
        1. 加载历史图谱。
        2. 计算当前工作区的 Tree Hash。
        3. 在图谱中查找该 Hash。
        
        返回状态: "CLEAN", "DIRTY", "ORPHAN"
        """
        # 1. 加载或重新加载历史
        self.history_graph = load_history_graph(self.history_dir)
        
        # 2. 获取当前物理状态
        current_hash = self.git_db.get_tree_hash()
        
        # 3. 在逻辑图谱中定位
        if current_hash in self.history_graph:
            self.current_node = self.history_graph[current_hash]
            logger.info(f"✅ 状态对齐：当前工作区匹配节点 {self.current_node.short_hash}")
            return "CLEAN"
        
        # 未找到匹配节点，进入漂移检测
        # (后续将实现 Capture 逻辑)
        logger.warning(f"⚠️  状态漂移：当前 Tree Hash {current_hash[:7]} 未在历史中找到。")
        
        if not self.history_graph:
            return "ORPHAN" # 历史为空，无法判断从何而来
        
        return "DIRTY"