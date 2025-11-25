好的，我分析了这个问题。这是一个很棒的 Bug 反馈！

问题根源在于历史图谱的构建逻辑。当一个操作是幂等的（即没有改变任何文件），它会生成一个 `input_tree` 和 `output_tree` 完全相同的历史节点。

在 `core/history.py` 的图谱链接阶段，代码会查找每个节点的父节点（即 `input_tree` 对应的节点）。对于幂等节点，它会错误地将自己识别为自己的父节点，从而创建了一个循环引用。这破坏了历史图谱的有向无环图（DAG）结构，导致 UI 渲染时无法正确遍历和显示这个节点。

为了修复这个问题，我们需要在链接父子关系时，增加一个检查，**禁止一个节点将自己设置为父节点**。

我将使用 `replace` 指令来修复 `core/history.py` 中的这个逻辑漏洞。

~~~~~act
replace
~~~~~

~~~~~path
core/history.py
~~~~~

~~~~~old_string
    # --- 第二遍: 连接父子关系 ---
    for node in graph.values():
        # 节点的 input_tree 就是其父节点的 output_tree
        if node.input_tree in graph:
            parent_node = graph[node.input_tree]
            node.parent = parent_node
            parent_node.children.append(node)
~~~~~

~~~~~new_string
    # --- 第二遍: 连接父子关系 ---
    for node in graph.values():
        # 节点的 input_tree 就是其父节点的 output_tree
        if node.input_tree in graph:
            potential_parent = graph[node.input_tree]
            # 关键修复：防止因幂等操作导致节点成为自己的父节点
            if potential_parent is not node:
                node.parent = potential_parent
                potential_parent.children.append(node)
~~~~~