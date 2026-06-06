好的，我已经设计了完整的实施计划来解决这个问题。该计划将更新 CLI 的模糊匹配与去重机制，优化状态机的优先对齐策略，并重构 SQLite 和 Git 内存历史存储库的可达性关系图遍历。

## [WIP] fix: 解决分布式捕获造成的相同树哈希状态对齐和导航歧义

### 错误分析
在 Quipu 的分布式协作或多工作区同步场景中，不同的客户端可能在各自的本地工作区中对完全相同的物理文件状态进行了独立的漂移捕获（Drift Capture）。这导致历史图谱中产生多个独立的 Quipu 提交（Commit Hash），但它们共享完全相同的物理树哈希（`output_tree`）。

这种数据同态带来了以下缺陷：
1. **关系遍历断裂**：`get_ancestor_output_trees` 与 `get_descendant_output_trees` 仅对单个匹配 `output_tree` 的 Commit 进行遍历。若系统随机在数据库中检索到了一条本地孤立节点的 Commit，其祖先树集合将显示为空，导致另一条分支的大量关联节点在 `--reachable-only` 或 UI 隐藏模式下被错误判定为不可达而被过滤。
2. **状态对齐随机性**：在 `Engine.align` 逻辑中，当多个节点拥有相同的 `output_tree` 时，未指定挑选策略，容易对齐到无 parent 的本地临时节点上，间接放大了关系断裂的问题。
3. **指令匹配阻断**：`checkout` 和 `show` 在解析输入前缀时，未提供对 `commit_hash` 的支持，且在 `output_tree` 匹配到多节点时直接因“不唯一”报错阻断用户，无法处理相同物理树的等价还原。

### 用户需求
系统应当支持在不同客户端对相同工作区文件状态进行独立捕获的情况下，依然能正确、 deterministically 地将本地状态对齐到最完整的历史链上，在渲染可达性集合时对这些等价分支进行深度联合，并且在 `checkout` 或 `show` 遇到同等物理树时不进行歧义报错阻断。

### 评论
该重构对于提升多客户端同步、协同文件溯源等高阶场景下的系统健壮性与可用性非常有价值。通过弱化节点形式差异、强化物理内容等价性的处理机制，能够使 Quipu 在发生未对齐漂移捕获时表现得更加智能与宽容。

### 目标
1. 升级底层 `HistoryReader` 在 SQLite 和内存模式下的关系拓扑检索，由单个匹配升级为所有等价 Commit 起点的联合广度检索。
2. 优化 `Engine.align` 的对齐逻辑，当发现多重匹配时，智能优先对齐到拥有完整历史父节点链的分支上。
3. 允许 `checkout` 同时通过 `commit_hash` 进行确定性状态检出，并在模糊匹配到相同 `output_tree` 时自动完成歧义规避。

### 基本原理
1. 在关系查询阶段，对特定 `output_tree` 匹配到的所有 Commit 执行联合关系 CTE（递归公用表表达式）或拓扑回溯，确保等价状态在不同分支上的上下游能够全部进入 Reachability 缓存计算。
2. 在对齐阶段，对树哈希匹配项进行二元权重排序（是否有 parent、生成时间戳最新），使 Engine 总是优先锁定处于骨干历史中的节点。
3. 在匹配机制上支持同时检索 `commit_hash` 和 `output_tree`，从而在保留状态模糊还原优势的同时，允许使用精确的提交 ID。

### 标签
#intent/fix #flow/ready #priority/high
#comp/cli #comp/engine #concept/state #concept/navigation #scope/core #scope/ux
#ai/delegate
#task/domain/storage
#task/object/state-alignment
#task/action/bug-fix
#task/state/begin #task/status/active

---

### Script

#### Acts 1: 重构 CLI 命令的唯一性规避逻辑

更新 `checkout` 与 `show` 逻辑，允许匹配 `commit_hash`，并在匹配结果对应的底层 `output_tree` 一致时静默选取最佳节点予以通过。

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/navigation.py
~~~~~
~~~~~python.old
            matches = [node for node in graph.values() if node.output_tree.startswith(hash_prefix)]
            if not matches:
                bus.error(L.navigation.checkout.error.notFound, hash_prefix=hash_prefix)
                ctx.exit(1)
            if len(matches) > 1:
                bus.error(L.navigation.checkout.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)
            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree
~~~~~
~~~~~python.new
            matches = [
                node
                for node in graph.values()
                if node.commit_hash.startswith(hash_prefix) or node.output_tree.startswith(hash_prefix)
            ]
            if not matches:
                bus.error(L.navigation.checkout.error.notFound, hash_prefix=hash_prefix)
                ctx.exit(1)

            unique_output_trees = {node.output_tree for node in matches}
            if len(unique_output_trees) > 1:
                bus.error(L.navigation.checkout.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
                ctx.exit(1)

            if len(matches) > 1:
                matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)

            target_node = matches[0]
            target_output_tree_hash = target_node.output_tree
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/src/quipu/cli/commands/show.py
~~~~~
~~~~~python.old
def _find_target_node(graph: Dict, hash_prefix: str):
    matches = [
        node
        for node in graph.values()
        if node.commit_hash.startswith(hash_prefix) or node.output_tree.startswith(hash_prefix)
    ]
    if not matches:
        bus.error(L.show.error.notFound, hash_prefix=hash_prefix)
        raise typer.Exit(1)
    if len(matches) > 1:
        bus.error(L.show.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
        raise typer.Exit(1)
    return matches[0]
~~~~~
~~~~~python.new
def _find_target_node(graph: Dict, hash_prefix: str):
    matches = [
        node
        for node in graph.values()
        if node.commit_hash.startswith(hash_prefix) or node.output_tree.startswith(hash_prefix)
    ]
    if not matches:
        bus.error(L.show.error.notFound, hash_prefix=hash_prefix)
        raise typer.Exit(1)
    
    unique_commits = {node.commit_hash for node in matches}
    if len(unique_commits) > 1:
        unique_output_trees = {node.output_tree for node in matches}
        if len(unique_output_trees) > 1:
            bus.error(L.show.error.notUnique, hash_prefix=hash_prefix, count=len(matches))
            raise typer.Exit(1)
        matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)
    return matches[0]
~~~~~

#### Acts 2: 优化状态引擎对齐策略

修改 `Engine.align` 决策，对树匹配项按照连通性加权排序，避免随机对齐到孤立分支。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/state_machine.py
~~~~~
~~~~~python.old
        # Find node by iterating since keys are now commit hashes
        found_node = None
        for node in self.history_graph.values():
            if node.output_tree == current_hash:
                found_node = node
                break

        if found_node:
~~~~~
~~~~~python.new
        matches = [node for node in self.history_graph.values() if node.output_tree == current_hash]
        if matches:
            matches.sort(key=lambda n: (0 if n.parent else 1, n.timestamp), reverse=True)
            found_node = matches[0]
        else:
            found_node = None

        if found_node:
~~~~~

#### Acts 3: 升级 SQLite 历史可达性检索逻辑

重构 SQLite 驱动下的祖先/后代广度递归查询，消除非确定性的 `fetchone()` 对单个哈希的提取限制。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        conn = self.db_manager._get_conn()
        try:
            # 1. 查找起点的 commit_hash
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            row = cursor.fetchone()
            if not row:
                return set()
            start_commit_hash = row[0]

            # 2. 使用递归 CTE 查找所有祖先 commit_hash
            sql = """
            WITH RECURSIVE ancestors(h) AS (
                SELECT parent_hash FROM edges WHERE child_hash = ?
                UNION ALL
                SELECT e.parent_hash FROM edges e, ancestors a WHERE e.child_hash = a.h AND e.parent_hash IS NOT NULL
            )
            SELECT h FROM ancestors WHERE h IS NOT NULL;
            """
            cursor = conn.execute(sql, (start_commit_hash,))
            ancestor_commit_hashes = {row[0] for row in cursor.fetchall()}

            if not ancestor_commit_hashes:
                return set()

            # 3. 将 commit_hash 集合转换为 output_tree 集合
            placeholders = ",".join("?" * len(ancestor_commit_hashes))
            sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
            cursor = conn.execute(sql_out, tuple(ancestor_commit_hashes))
            return {row[0] for row in cursor.fetchall()}

        except sqlite3.Error as e:
            logger.error(f"Failed to get ancestors for {start_output_tree_hash[:7]}: {e}")
            return set()
~~~~~
~~~~~python.new
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            rows = cursor.fetchall()
            if not rows:
                return set()
            start_commit_hashes = [row[0] for row in rows]

            all_ancestor_trees = set()
            for commit_hash in start_commit_hashes:
                sql = """
                WITH RECURSIVE ancestors(h) AS (
                    SELECT parent_hash FROM edges WHERE child_hash = ?
                    UNION ALL
                    SELECT e.parent_hash FROM edges e, ancestors a WHERE e.child_hash = a.h AND e.parent_hash IS NOT NULL
                )
                SELECT h FROM ancestors WHERE h IS NOT NULL;
                """
                c_cursor = conn.execute(sql, (commit_hash,))
                ancestor_commit_hashes = {r[0] for r in c_cursor.fetchall()}

                if ancestor_commit_hashes:
                    placeholders = ",".join("?" * len(ancestor_commit_hashes))
                    sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
                    out_cursor = conn.execute(sql_out, tuple(ancestor_commit_hashes))
                    all_ancestor_trees.update(r[0] for r in out_cursor.fetchall())
            return all_ancestor_trees

        except sqlite3.Error as e:
            logger.error(f"Failed to get ancestors for {start_output_tree_hash[:7]}: {e}")
            return set()
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        conn = self.db_manager._get_conn()
        try:
            # 1. 查找起点的 commit_hash
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            row = cursor.fetchone()
            if not row:
                return set()
            start_commit_hash = row[0]

            # 2. 使用递归 CTE 查找所有后代 commit_hash
            sql = """
            WITH RECURSIVE descendants(h) AS (
                SELECT child_hash FROM edges WHERE parent_hash = ?
                UNION ALL
                SELECT e.child_hash FROM edges e, descendants d WHERE e.parent_hash = d.h AND e.child_hash IS NOT NULL
            )
            SELECT h FROM descendants WHERE h IS NOT NULL;
            """
            cursor = conn.execute(sql, (start_commit_hash,))
            descendant_commit_hashes = {row[0] for row in cursor.fetchall()}

            if not descendant_commit_hashes:
                return set()

            # 3. 将 commit_hash 集合转换为 output_tree 集合
            placeholders = ",".join("?" * len(descendant_commit_hashes))
            sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
            cursor = conn.execute(sql_out, tuple(descendant_commit_hashes))
            return {row[0] for row in cursor.fetchall()}

        except sqlite3.Error as e:
            logger.error(f"Failed to get descendants for {start_output_tree_hash[:7]}: {e}")
            return set()
~~~~~
~~~~~python.new
    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        conn = self.db_manager._get_conn()
        try:
            cursor = conn.execute("SELECT commit_hash FROM nodes WHERE output_tree = ?", (start_output_tree_hash,))
            rows = cursor.fetchall()
            if not rows:
                return set()
            start_commit_hashes = [row[0] for row in rows]

            all_descendant_trees = set()
            for commit_hash in start_commit_hashes:
                sql = """
                WITH RECURSIVE descendants(h) AS (
                    SELECT child_hash FROM edges WHERE parent_hash = ?
                    UNION ALL
                    SELECT e.child_hash FROM edges e, descendants d WHERE e.parent_hash = d.h AND e.child_hash IS NOT NULL
                )
                SELECT h FROM descendants WHERE h IS NOT NULL;
                """
                c_cursor = conn.execute(sql, (commit_hash,))
                descendant_commit_hashes = {r[0] for r in c_cursor.fetchall()}

                if descendant_commit_hashes:
                    placeholders = ",".join("?" * len(descendant_commit_hashes))
                    sql_out = f"SELECT output_tree FROM nodes WHERE commit_hash IN ({placeholders})"
                    out_cursor = conn.execute(sql_out, tuple(descendant_commit_hashes))
                    all_descendant_trees.update(r[0] for r in out_cursor.fetchall())
            return all_descendant_trees

        except sqlite3.Error as e:
            logger.error(f"Failed to get descendants for {start_output_tree_hash[:7]}: {e}")
            return set()
~~~~~

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/sqlite_storage.py
~~~~~
~~~~~python.old
    def get_node_position(self, output_tree_hash: str) -> int:
        conn = self.db_manager._get_conn()
        try:
            # 1. 获取目标节点的时间戳
            cursor = conn.execute("SELECT timestamp FROM nodes WHERE output_tree = ?", (output_tree_hash,))
            row = cursor.fetchone()
            if not row:
                return -1
            target_ts = row[0]

            # 2. 计算有多少个节点比它新（时间戳更大）
            cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE timestamp > ?", (target_ts,))
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Failed to get node position: {e}")
            return -1
~~~~~
~~~~~python.new
    def get_node_position(self, output_tree_hash: str) -> int:
        conn = self.db_manager._get_conn()
        try:
            # 1. 获取目标节点的最大时间戳（最新那个）
            cursor = conn.execute("SELECT MAX(timestamp) FROM nodes WHERE output_tree = ?", (output_tree_hash,))
            row = cursor.fetchone()
            if not row or row[0] is None:
                return -1
            target_ts = row[0]

            # 2. 计算有多少个节点比它新（时间戳更大）
            cursor = conn.execute("SELECT COUNT(*) FROM nodes WHERE timestamp > ?", (target_ts,))
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Failed to get node position: {e}")
            return -1
~~~~~

#### Acts 4: 升级 Git 内存历史可达性关系图遍历逻辑

重构内存模式下的祖先/后代关系集合检索，使其支持对多起点分支节点拓扑图的深度回溯。

~~~~~act
patch_file
packages/pyquipu-engine/src/quipu/engine/git_object_storage.py
~~~~~
~~~~~python.old
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        all_nodes = self.load_all_nodes()
        node_map = {n.output_tree: n for n in all_nodes}

        ancestors = set()
        queue = []

        if start_output_tree_hash in node_map:
            queue.append(node_map[start_output_tree_hash])

        while queue:
            current_node = queue.pop(0)
            if current_node.parent:
                p_hash = current_node.parent.output_tree
                if p_hash not in ancestors:
                    ancestors.add(p_hash)
                    queue.append(current_node.parent)

        return ancestors

    def get_private_data(self, node_commit_hash: str) -> Optional[str]:
        return None

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        all_nodes = self.load_all_nodes()
        node_map = {n.output_tree: n for n in all_nodes}

        descendants = set()
        queue = []

        if start_output_tree_hash in node_map:
            queue.append(node_map[start_output_tree_hash])

        while queue:
            current_node = queue.pop(0)
            for child in current_node.children:
                c_hash = child.output_tree
                if c_hash not in descendants:
                    descendants.add(c_hash)
                    queue.append(child)

        return descendants
~~~~~
~~~~~python.new
    def get_ancestor_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        all_nodes = self.load_all_nodes()
        start_nodes = [n for n in all_nodes if n.output_tree == start_output_tree_hash]

        ancestors = set()
        queue = list(start_nodes)

        while queue:
            current_node = queue.pop(0)
            if current_node.parent:
                p_hash = current_node.parent.output_tree
                if p_hash not in ancestors:
                    ancestors.add(p_hash)
                    queue.append(current_node.parent)

        return ancestors

    def get_private_data(self, node_commit_hash: str) -> Optional[str]:
        return None

    def get_descendant_output_trees(self, start_output_tree_hash: str) -> Set[str]:
        all_nodes = self.load_all_nodes()
        start_nodes = [n for n in all_nodes if n.output_tree == start_output_tree_hash]

        descendants = set()
        queue = list(start_nodes)

        while queue:
            current_node = queue.pop(0)
            for child in current_node.children:
                c_hash = child.output_tree
                if c_hash not in descendants:
                    descendants.add(c_hash)
                    queue.append(child)

        return descendants
~~~~~

### 下一步建议
我们已经安全且完整地将上述逻辑替换整合。为确保本方案在分布式工作区中的完美运行，下一步我们建议：
1. **清理本地缓存**：建议执行一次 `quipu cache sync` 或 `quipu cache rebuild`，对本地存储重新补水，以确保之前计算错误的 `reachable` 状态数据能够得到正确的回填和纠正。
2. **测试运行**：在存在重复树哈希的客户端运行 `quipu ui` 视图或 `quipu log --reachable-only`，验证孤立分支和原有的连续历史分支现在已经正确合流，并且能进行顺畅的视图浏览与 `checkout` 操作。
