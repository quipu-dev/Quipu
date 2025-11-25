# fix: TUI 分栏模式下保留摘要显示

## 用户需求
用户发现在 TUI 的分栏预览模式下，左侧列表隐藏了“Node Info”（摘要）列，导致浏览体验下降。用户希望无论是否分栏，都始终显示摘要信息，充分利用屏幕空间。

## 目标
1.  修改 `tui.py`，在分栏模式下不再隐藏 "Node Info" 列。
2.  确保左侧列表在变窄（50% 宽度）后，摘要列依然存在（接受被截断）。

## 基本原理
移除 `_refresh_table` 和 `_populate_table` 方法中关于 `self.is_split_mode` 的条件判断，使得第三列（摘要）始终被渲染。Textual 的 DataTable 会自动处理列宽适应。

## 标签
#comp/cli #scope/ux #fix

---

## Script

### Acts 1: 移除列隐藏逻辑

修改 `tui.py`，让 "Node Info" 列常驻。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
    def _refresh_table(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        
        # 在分栏模式下，隐藏详细信息列以节省空间
        cols = ["Time", "Graph"]
        if not self.is_split_mode:
            cols.append("Node Info")
            
        table.add_columns(*cols)
        self._populate_table(table)
        
        # 初始加载时定位到当前 HEAD
~~~~~
~~~~~python
    def _refresh_table(self):
        table = self.query_one(DataTable)
        table.clear(columns=True)
        
        # 始终显示详细信息列，即使在分栏模式下
        cols = ["Time", "Graph", "Node Info"]
            
        table.add_columns(*cols)
        self._populate_table(table)
        
        # 初始加载时定位到当前 HEAD
~~~~~

~~~~~act
replace packages/quipu-cli/src/quipu/cli/tui.py
~~~~~
~~~~~python
            ts_str = f"{dim_tag}{node.timestamp.strftime('%Y-%m-%d %H:%M')}{end_dim_tag}"
            
            row_data = [ts_str, "".join(graph_chars)]
            
            # 仅在非分栏模式下显示详细信息列
            if not self.is_split_mode:
                summary = self._get_node_summary(node)
                tag_char = node.node_type.upper()
                info_text = f"[{base_color}][{tag_char}] {node.short_hash}[/{base_color}] - {summary}"
                info_str = f"{dim_tag}{info_text}{end_dim_tag}"
                row_data.append(info_str)
            
            # 使用 filename 作为唯一的 key
            table.add_row(*row_data, key=str(node.filename))
~~~~~
~~~~~python
            ts_str = f"{dim_tag}{node.timestamp.strftime('%Y-%m-%d %H:%M')}{end_dim_tag}"
            
            row_data = [ts_str, "".join(graph_chars)]
            
            # 始终显示详细信息列
            summary = self._get_node_summary(node)
            tag_char = node.node_type.upper()
            info_text = f"[{base_color}][{tag_char}] {node.short_hash}[/{base_color}] - {summary}"
            info_str = f"{dim_tag}{info_text}{end_dim_tag}"
            row_data.append(info_str)
            
            # 使用 filename 作为唯一的 key
            table.add_row(*row_data, key=str(node.filename))
~~~~~
