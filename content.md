好的，这个需求非常棒，可以让历史记录更具可读性。

为了实现这个功能，我需要修改 `ui/tui.py` 文件中的表格渲染逻辑。目前的颜色是根据节点类型（`plan` 或 `capture`）来决定的。我将加入一个新的判断条件：如果一个节点是 `plan` 类型，并且其输入与输出哈希相同，就将其颜色设置为绿色。

这个修改将统一图表符号（`●`）和文本信息的颜色，确保视觉上的一致性。

~~~~~act
replace
~~~~~

~~~~~path
ui/tui.py
~~~~~

~~~~~old_string
            # --- 2. 生成图形 ---
            graph_chars = []
            for i, track_hash in enumerate(tracks):
                if track_hash is None:
                    graph_chars.append("  ")
                    continue
                
                # 确定基础符号
                if i == col_idx:
                    symbol = "●" if node.node_type == 'plan' else "○"
                    # 基础颜色
                    color = "cyan" if node.node_type == 'plan' else "magenta"
                    symbol = f"[{color}]{symbol}[/]"
                    
                    # 组合: Dim + Color + Symbol
                    # 例如 [dim][cyan]●[/][/dim]
                    cell_str = f"{dim_tag}{symbol} {end_dim_tag}"
                    graph_chars.append(cell_str)
                    
                elif i in merging_indices:
                    graph_chars.append(f"{dim_tag}┘ {end_dim_tag}") 
                else:
                    graph_chars.append(f"{dim_tag}│ {end_dim_tag}")

            graph_str = "".join(graph_chars)

            # --- 3. 更新轨道 ---
            tracks[col_idx] = parent_hash
            for i in merging_indices[1:]:
                tracks[i] = None
            while tracks and tracks[-1] is None:
                tracks.pop()

            # --- 4. 文本信息 ---
            ts_str = node.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            # 时间戳也应用 dim
            ts_str = f"{dim_tag}{ts_str}{end_dim_tag}"
            
            node_type_code = "[P]" if node.node_type == "plan" else "[C]"
            short_hash = node.short_hash
            summary = self._get_node_summary(node)
            
            # Info 列颜色逻辑
            base_color = "cyan" if node.node_type == "plan" else "magenta"
            
            # 组合 Info 字符串
            # 结构: [dim] [color][P] hash[/] - summary [/dim]
            info_str = f"{dim_tag}[{base_color}]{node_type_code} {short_hash}[/] - {summary}{end_dim_tag}"
~~~~~

~~~~~new_string
            # --- 2. 颜色与元信息准备 ---
            base_color = "magenta"  # 默认为 Capture 颜色
            if node.node_type == "plan":
                if node.input_tree == node.output_tree:
                    base_color = "green"  # 幂等节点
                else:
                    base_color = "cyan"   # 普通 Plan

            # --- 3. 生成图形 ---
            graph_chars = []
            for i, track_hash in enumerate(tracks):
                if track_hash is None:
                    graph_chars.append("  ")
                    continue
                
                if i == col_idx:
                    symbol_char = "●" if node.node_type == 'plan' else "○"
                    symbol = f"[{base_color}]{symbol_char}[/]"
                    cell_str = f"{dim_tag}{symbol} {end_dim_tag}"
                    graph_chars.append(cell_str)
                elif i in merging_indices:
                    graph_chars.append(f"{dim_tag}┘ {end_dim_tag}") 
                else:
                    graph_chars.append(f"{dim_tag}│ {end_dim_tag}")

            graph_str = "".join(graph_chars)

            # --- 4. 更新轨道 ---
            tracks[col_idx] = parent_hash
            for i in merging_indices[1:]:
                tracks[i] = None
            while tracks and tracks[-1] is None:
                tracks.pop()

            # --- 5. 文本信息 ---
            ts_str = node.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            ts_str = f"{dim_tag}{ts_str}{end_dim_tag}"
            
            node_type_code = "[P]" if node.node_type == "plan" else "[C]"
            short_hash = node.short_hash
            summary = self._get_node_summary(node)
            info_str = f"{dim_tag}[{base_color}]{node_type_code} {short_hash}[/] - {summary}{end_dim_tag}"
~~~~~