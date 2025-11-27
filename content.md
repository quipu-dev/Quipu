为了彻底解决这个问题，我们需要切断 `SQLiteHistoryWriter` 对 Git 状态反查的依赖，转而通过对象传递的方式，将明确的“父子关系”从 Git 写入层直接传递给 SQLite 写入层。

这不仅修复了幂等操作中的自引用 bug，也使得整个写入流程在逻辑上更加严密和高效（减少了一次昂贵的 `git log` 查询）。

## refactor(engine): 重构写入层以显式传递父节点信息

### 错误分析
在幂等操作（Idempotent Operation）中，新节点与父节点拥有相同的 `Output Tree`。
`SQLiteHistoryWriter` 原先通过 `get_commit_by_output_tree(input_tree)` 来反查父节点。在幂等场景下，Git 中会存在多个 Commit 指向同一个 Tree。由于反查通常返回最新的 Commit（即刚刚创建的当前节点），导致系统错误地将当前节点记录为它自己的父节点，形成自引用边。

### 用户需求
修复幂等操作导致 UI 显示断开（孤儿节点）和数据库自引用的问题。

### 评论
这是一个架构层面的数据流修正。我们不再“猜测”父节点是谁，而是让创建者（GitWriter）直接“告诉”记录者（SQLiteWriter）父节点是谁。

### 目标
1.  修改 `GitObjectHistoryWriter`，使其返回的 `QuipuNode` 对象中包含一个指向父 Commit Hash 的 `parent` 引用（通过一个轻量级的占位节点实现）。
2.  修改 `SQLiteHistoryWriter`，直接从 `git_node.parent` 读取父节点 Hash 来写入 `edges` 表，完全移除易错的反查逻辑。

### 基本原理
利用 `QuipuNode` 数据模型中已有的 `parent` 字段。虽然该字段通常用于存储完整的父节点对象，但在写入阶段，我们可以构造一个仅包含 `filename`（存储 Hash）的轻量级 `QuipuNode` 作为数据传输对象（DTO），在层级间传递确定的父节点身份。

### 标签
#intent/refine #flow/ready #priority/high
#comp/engine #concept/state #scope/core
#ai/instruct
#task/domain/storage
#task/object/sqlite-backend
#task/action/bug-fix
#task/state/continue

---

### Script

#### Acts 1: 修改 GitObjectHistoryWriter 显式填充 Parent

我们将在 `create_node` 返回前，根据已知的 `parent_commit` 构造一个带有 `parent` 属性的节点对象。

~~~~~act
patch_file
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
        if parent_commit:
            self.git_db.delete_ref(f"refs/quipu/heads/{parent_commit}")

        logger.info(f"✅ History node created as commit {new_commit_hash[:7]}")

        # 返回一个 QuipuNode 实例，content 此时已在内存中，无需 Lazy Load
        return QuipuNode(
            input_tree=input_tree,
            output_tree=output_tree,
            timestamp=datetime.fromtimestamp(start_time),
            filename=Path(f".quipu/git_objects/{new_commit_hash}"),
            node_type=node_type,
            content=content,
        )
~~~~~
~~~~~python
        if parent_commit:
            self.git_db.delete_ref(f"refs/quipu/heads/{parent_commit}")

        logger.info(f"✅ History node created as commit {new_commit_hash[:7]}")

        # 返回一个 QuipuNode 实例，content 此时已在内存中，无需 Lazy Load
        node = QuipuNode(
            input_tree=input_tree,
            output_tree=output_tree,
            timestamp=datetime.fromtimestamp(start_time),
            filename=Path(f".quipu/git_objects/{new_commit_hash}"),
            node_type=node_type,
            content=content,
        )

        # 关键修改：显式填充 parent 信息，以便上层 Writer (如 SQLite) 可以直接获取确切的父节点 Hash
        # 而无需通过容易出错的 Tree 反查。我们使用一个最小化的占位节点。
        if parent_commit:
            # 这里的 filename 实际上存储的是 commit hash
            node.parent = QuipuNode(
                input_tree="",  # Placeholder
                output_tree="", # Placeholder
                timestamp=datetime.fromtimestamp(0), # Placeholder
                filename=Path(f".quipu/git_objects/{parent_commit}"),
                node_type="unknown",
                content=""
            )

        return node
~~~~~

#### Acts 2: 修改 SQLiteHistoryWriter 使用显式 Parent

我们将移除 `get_commit_by_output_tree` 调用，改为直接读取 `git_node.parent`。

~~~~~act
patch_file
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/sqlite_storage.py
~~~~~
~~~~~python
            # 2.3 写入 'edges' 表
            parent_commit = self.git_writer.git_db.get_commit_by_output_tree(input_tree)
            if parent_commit:
                self.db_manager.execute_write(
                    "INSERT OR IGNORE INTO edges (child_hash, parent_hash) VALUES (?, ?)",
                    (commit_hash, parent_commit),
                )
~~~~~
~~~~~python
            # 2.3 写入 'edges' 表
            # 关键修改：直接使用 GitWriter 传递回来的确切父节点信息，不再进行 Tree 反查
            if git_node.parent:
                parent_hash = git_node.parent.filename.name
                self.db_manager.execute_write(
                    "INSERT OR IGNORE INTO edges (child_hash, parent_hash) VALUES (?, ?)",
                    (commit_hash, parent_hash),
                )
~~~~~

### 下一步建议
应用此重构后，建议执行一次空操作（例如 `qs run o.md`，其中 `o.md` 包含 `act: end` 或其他无实际变更的指令），然后检查 `qs ui` 是否正确将其显示为连接到主干的绿色节点，而不是断开的新分支。
