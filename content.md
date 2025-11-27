好的，我将执行任务 4.4。

这个任务的目标是更新数据读取逻辑，确保从 SQLite 数据库加载历史节点时，能够包含新添加的 `owner_id` 字段，从而将所有权信息传递给应用程序的上层。

我将修改 `SQLiteHistoryReader` 中的三个核心读取方法：`load_all_nodes`、`load_nodes_paginated` 和 `find_nodes`。

---
## feat: 在数据读取层中加载并填充节点所有者信息

### 用户需求
系统后端已经能够存储每个历史节点的 `owner_id`，现在需要更新数据读取层 (`SQLiteHistoryReader`)，使其在查询数据库时能够获取此信息，并将其填充到 `QuipuNode` 数据模型中。这是让 UI 等上层应用能够展示多用户信息的关键一步。

### 评论
这是一个直接的数据管道疏通工作。由于之前我们在 `nodes` 表中使用了 `SELECT *`，因此 SQL 查询本身可能不需要大改，核心是确保在将数据库行映射到 `QuipuNode` 对象时， `owner_id` 字段被正确传递。

### 目标
1.  修改 `SQLiteHistoryReader.load_all_nodes` 方法，使其加载的 `QuipuNode` 对象包含 `owner_id`。
2.  修改 `SQLiteHistoryReader.load_nodes_paginated` 方法，使其分页加载的 `QuipuNode` 对象包含 `owner_id`。
3.  修改 `SQLiteHistoryReader.find_nodes` 方法，使其查找结果中的 `QuipuNode` 对象包含 `owner_id`，并修复一个之前存在的 `commit_hash` 字段未填充的缺陷。

### 基本原理
通过修改 `QuipuNode` 构造函数的调用，将从 `sqlite3.Row` 对象中读取到的 `owner_id` 值赋给 `QuipuNode` 实例的 `owner_id` 属性。由于 `SELECT *` 已经包含了新字段，我们无需修改 SQL 查询语句。

### 标签
#intent/build #flow/ready #priority/high #comp/engine #comp/interfaces #concept/history #scope/core #ai/instruct #task/domain/storage #task/object/sqlite-backend #task/action/integration #task/state/continue

---

### Script

#### Acts 1: 更新 `load_all_nodes` 方法

我们将修改 `load_all_nodes` 方法中的 `QuipuNode` 实例化过程，添加 `owner_id` 字段。

`````````act
patch_file
packages/quipu-engine/src/quipu/core/sqlite_storage.py
`````````
`````````python
                # 内容是懒加载的
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
            )
            temp_nodes[commit_hash] = node
`````````
`````````python
                # 内容是懒加载的
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                owner_id=row["owner_id"],
            )
            temp_nodes[commit_hash] = node
`````````

#### Acts 2: 更新 `load_nodes_paginated` 方法

同样，在 `load_nodes_paginated` 方法中，为 `QuipuNode` 实例添加 `owner_id`。

`````````act
patch_file
packages/quipu-engine/src/quipu/core/sqlite_storage.py
`````````
`````````python
                    node_type=row["node_type"],
                    summary=row["summary"],
                    content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                )

            # 2. Fetch edges to identify parents
`````````
`````````python
                    node_type=row["node_type"],
                    summary=row["summary"],
                    content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                    owner_id=row["owner_id"],
                )

            # 2. Fetch edges to identify parents
`````````

#### Acts 3: 更新 `find_nodes` 方法并修复缺陷

最后，在 `find_nodes` 方法中添加 `owner_id`，并补上缺失的 `commit_hash` 字段。

`````````act
patch_file
packages/quipu-engine/src/quipu/core/sqlite_storage.py
`````````
`````````python
        # 将查询结果行映射回 QuipuNode 对象 (不含父子关系)
        results = []
        for row in rows:
            node = QuipuNode(
                input_tree="",  # 查找结果是扁平列表，不包含父子关系
                output_tree=row["output_tree"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                filename=Path(f".quipu/git_objects/{row['commit_hash']}"),
                node_type=row["node_type"],
                summary=row["summary"],
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
            )
            results.append(node)

        return results
`````````
`````````python
        # 将查询结果行映射回 QuipuNode 对象 (不含父子关系)
        results = []
        for row in rows:
            node = QuipuNode(
                commit_hash=row["commit_hash"],
                input_tree="",  # 查找结果是扁平列表，不包含父子关系
                output_tree=row["output_tree"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                filename=Path(f".quipu/git_objects/{row['commit_hash']}"),
                node_type=row["node_type"],
                summary=row["summary"],
                content=row["plan_md_cache"] if row["plan_md_cache"] is not None else "",
                owner_id=row["owner_id"],
            )
            results.append(node)

        return results
`````````

### 下一步建议
数据管道现已完全打通，从 Git 原始数据到应用程序内存中的 `QuipuNode` 对象，都已经包含了 `owner_id` 信息。

下一步是完成 **任务 5.1**：在 TUI 中利用 `owner_id` 字段来展示或区分不同作者的历史分支，让用户能够直观地看到协作成果。
