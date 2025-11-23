import sys
from datetime import datetime
from typing import List, Optional, Dict
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable
from textual.binding import Binding

# 确保能从上级目录导入 core 模块
sys.path.append('..')
from core.models import AxonNode

class AxonUiApp(App):
    """
    Axon Timeline Explorer
    一个基于 DataTable 的时间轴历史浏览器，实现了类似 git log --graph 的多轨道视图。
    """

    CSS = """
    DataTable {
        height: 100%;
        background: $surface;
        border: none;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("c", "checkout_node", "检出节点"),
        Binding("enter", "checkout_node", "检出节点"),
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
    ]

    def __init__(self, nodes: List[AxonNode], current_hash: Optional[str] = None):
        super().__init__()
        # 1. 数据预处理：按时间戳倒序排列 (最新的在上面)
        self.sorted_nodes = sorted(nodes, key=lambda n: n.timestamp, reverse=True)
        self.current_hash = current_hash
        self.node_map = {node.output_tree: node for node in nodes}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # zebra_stripes=False 以避免干扰 ASCII 图形的连贯性
        yield DataTable(cursor_type="row", zebra_stripes=False)
        yield Footer()

    def on_mount(self) -> None:
        """初始化表格数据与样式"""
        table = self.query_one(DataTable)
        
        # 定义列
        # Graph 列需要足够的宽度来展示多分支
        table.add_columns("Time", "Graph", "Node Info")
        
        # 填充数据
        self._populate_table(table)
        
        # 自动定位到当前状态
        self._focus_current_node(table)
        
        table.focus()

    def _populate_table(self, table: DataTable):
        """
        构建时间轴视图。
        使用轨道追踪算法生成类似 git log --graph 的 ASCII 图形。
        """
        # 轨道列表：存储当前每一列正在追踪的 parent_hash
        # 列表索引对应列索引。None 表示该位置为空（之前的分支已结束）。
        tracks: List[Optional[str]] = []

        for node in self.sorted_nodes:
            node_hash = node.output_tree
            parent_hash = node.input_tree

            # 1. 确定当前节点所在的轨道索引
            # 如果 node_hash 在 tracks 中，说明它是上面某个节点的 parent，承接该轨道
            # 如果不在，说明它是某个分支的顶端 (Head)，需要分配新轨道
            
            # 查找所有指向当前节点的轨道（可能是在倒序中发生的合并）
            merging_indices = [i for i, h in enumerate(tracks) if h == node_hash]
            
            if merging_indices:
                # 继承第一个匹配的轨道
                col_idx = merging_indices[0]
            else:
                # 新的分支顶端：找一个空位或追加
                try:
                    col_idx = tracks.index(None)
                    tracks[col_idx] = node_hash # 临时占位
                except ValueError:
                    tracks.append(node_hash)
                    col_idx = len(tracks) - 1
                    
            # 2. 生成图形字符串
            graph_chars = []
            
            # 为了美观，我们使用 2 个字符宽度的列：符号 + 空格
            for i, track_hash in enumerate(tracks):
                if track_hash is None:
                    graph_chars.append("  ")
                    continue
                
                # 确定当前位置的符号
                if i == col_idx:
                    # 当前节点位置
                    # 区分 Plan 和 Capture
                    symbol = "●" if node.node_type == 'plan' else "○"
                    
                    # 颜色处理 (使用 Rich 标记)
                    if node.node_type == 'plan':
                        symbol = f"[cyan]{symbol}[/]"
                    else:
                        symbol = f"[magenta]{symbol}[/]"
                        
                    # 如果有合并（其他轨道汇入此轨道）
                    if len(merging_indices) > 1:
                        # 这里可以显示特殊合并符号，但简单起见，我们只在那些轨道画连线
                        pass
                    
                    graph_chars.append(f"{symbol} ")
                    
                elif i in merging_indices:
                    # 这是一条汇入当前节点的轨道 (倒序视图中的分叉点)
                    # 显示向左合并的连接符
                    graph_chars.append("┘ ") 
                else:
                    # 这是一条路过的轨道，与当前节点无关
                    graph_chars.append("│ ")

            graph_str = "".join(graph_chars)

            # 3. 更新轨道状态 (为下一行做准备)
            # 当前轨道的使命结束，它的目标更新为当前节点的父节点
            tracks[col_idx] = parent_hash
            
            # 其他汇入的轨道已终结 (Merged)
            for i in merging_indices[1:]:
                tracks[i] = None
            
            # 优化：清理末尾的 None，防止轨道列表无限增长
            while tracks and tracks[-1] is None:
                tracks.pop()

            # 4. 构建其他列信息
            ts_str = node.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            node_type_code = "[P]" if node.node_type == "plan" else "[C]"
            short_hash = node.short_hash
            summary = self._get_node_summary(node)
            
            # 颜色高亮
            color = "cyan" if node.node_type == "plan" else "magenta"
            info_str = f"[{color}]{node_type_code} {short_hash}[/] - {summary}"

            # 5. 添加行
            table.add_row(ts_str, graph_str, info_str, key=node.output_tree)

    def _get_node_summary(self, node: AxonNode) -> str:
        """提取简洁的摘要信息"""
        content = node.content.strip()
        lines = content.split('\n')
        
        summary = "No description"
        
        if node.node_type == 'plan':
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith(('~~~', '```')):
                    continue
                if clean_line:
                    summary = clean_line
                    break
        elif node.node_type == 'capture':
            user_msg = ""
            for line in lines:
                if "### 💬 备注:" in line:
                    continue
                if line.strip() and not line.startswith(('#', '`', '-')):
                     user_msg = line.strip()
                     break
            if user_msg:
                summary = user_msg
            else:
                summary = "Workspace Snapshot"

        return (summary[:60] + '...') if len(summary) > 60 else summary

    def _focus_current_node(self, table: DataTable):
        """尝试定位并高亮当前工作区对应的行"""
        if not self.current_hash:
            return
        try:
            row_index = table.get_row_index(self.current_hash)
            table.move_cursor(row=row_index)
        except Exception:
            pass

    def action_checkout_node(self) -> None:
        """处理检出动作"""
        table = self.query_one(DataTable)
        try:
            selected_hash = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            if selected_hash:
                self.exit(result=selected_hash)
        except Exception:
            pass