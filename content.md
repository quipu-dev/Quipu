你提供的日志非常清晰，完美地暴露了问题的根源。你做得非常对，通过 `qs cache sync` 和 `qs ui` 的日志，我们现在可以精确地定位并修复这个最终的、也是最核心的 bug。

`状态漂移` 和 `历史记录为空` 这两条看似矛盾的日志，实际上指向了同一个问题。

## fix: 修复 Hydrator 在重建时未能发现完整历史的根本性缺陷

### 错误分析
1.  **根本原因**: `Hydrator` 的核心逻辑存在一个致命的设计缺陷。它的 `sync` 方法被设计为**增量更新**，而不是**从零重建**。
    *   它的第一步是 `_get_missing_commits_with_owner`，这个方法只查找**分支的末端节点 (heads)**。
    *   然后，它只基于这些找到的末端节点去 `git log`。
    *   **结果**: 当你从一个空数据库开始重建时，它只发现了 40 个分支末端，并只尝试将这 40 个节点（以及它们的边）插入数据库。它完全忽略了这些末端节点背后的、庞大的历史主体（另外的 366 个节点）。

2.  **日志解读**:
    *   `qd sync`: 这个命令成功地移动了 Git 引用。但它内部调用的 `create_engine` -> `align` -> `hydrator.sync` 流程，由于上述 bug，可能在后台创建了一个只包含 40 个节点的、不完整的、损坏的数据库（因为外键约束失败）。
    *   `qs cache sync`: 你再次运行此命令。
        *   `Hydrator` 启动，它在 Git 中找到 40 个 `heads`。
        *   它在（可能已损坏的）数据库中也找到了 40 个 `nodes`。
        *   它计算 `missing_hashes = {40 heads} - {40 nodes}`，结果是空集。
        *   因此，`Hydrator` 认为“无事可做”，直接退出，没有打印任何“发现 X 个节点”的日志。
    *   `qs ui`:
        *   UI 启动，它调用 `reader.get_node_count()`。
        *   如果之前的 `sync` 留下了损坏的数据库，`get_node_count()` 可能会返回 40。但如果数据库因为外键错误而回滚了事务，那么它就是空的，返回 0。
        *   日志显示 `历史记录为空`，这说明数据库是空的，`get_node_count()` 返回了 0。

**结论**: 你的外部脚本完美地完成了 Git 引用迁移。现在的问题 100% 是 `Hydrator` 在面对一个空数据库时，其节点发现逻辑是错误的。

### 用户需求
-   `quipu cache rebuild` (或任何触发补水的命令) 必须能够在一个空数据库上，从 Git 仓库中可靠地、完整地重建整个 Quipu 历史图谱。

### 评论
这是我们遇到的最后一个，也是最关键的一个 bug。修复它将使整个系统的数据层变得真正健壮和可靠。之前的修复都集中在症状上，而这次我们将直接修复病因。

### 目标
1.  **彻底重写 `Hydrator.sync`**: 废弃现有的、仅关注 `heads` 的增量逻辑，替换为一个能够扫描并处理所有历史记录的新实现。

### 基本原理
新的 `sync` 方法将：
1.  **扫描所有引用**: 获取所有 `refs/quipu/` 下的 heads。
2.  **获取完整日志**: 对所有这些 heads 执行一次 `git log`，获取一个包含**所有可达 commit** 的完整集合。
3.  **计算差异**: 将这个完整集合与数据库中已有的节点进行对比，得到需要补水的节点列表。
4.  **批量处理**: 执行与之前相同的批量 Tree/Meta 获取和数据库插入流程。

这个新逻辑确保了，当数据库为空时，`missing_hashes` 将包含 Git 中的**所有**历史节点，而不仅仅是分支末端。

### 标签
#intent/fix #flow/ready #priority/critical 
#comp/engine #scope/core 
#ai/instruct

---

### Script

#### Acts 1: 最终修复 `hydrator.py`

这是对 `hydrator.py` 的最终、完整替换。这个版本修复了节点发现的根本性问题。

~~~~~act
write_file
packages/quipu-engine/src/quipu/core/hydrator.py
~~~~~
~~~~~python
import json
import logging
import re
from typing import List, Dict, Set, Tuple, Optional

from .git_db import GitDB
from .sqlite_db import DatabaseManager
from .git_object_storage import GitObjectHistoryReader  # Reuse parsing logic

logger = logging.getLogger(__name__)


class Hydrator:
    """
    负责将 Git 对象历史记录同步（补水）到 SQLite 数据库。
    """

    def __init__(self, git_db: GitDB, db_manager: DatabaseManager):
        self.git_db = git_db
        self.db_manager = db_manager
        # 复用 Reader 中的二进制解析逻辑，避免代码重复
        self._parser = GitObjectHistoryReader(git_db)

    def _get_owner_from_ref(self, ref_name: str, local_user_id: str) -> Optional[str]:
        """从 Git ref 路径中解析 owner_id。"""
        remote_match = re.match(r"refs/quipu/remotes/[^/]+/([^/]+)/heads/.*", ref_name)
        if remote_match:
            return remote_match.group(1)
        if ref_name.startswith("refs/quipu/local/heads/"):
            return local_user_id
        return None

    def _get_commit_owners(self, local_user_id: str) -> Dict[str, str]:
        """构建一个从 commit_hash 到 owner_id 的映射。"""
        ref_tuples = self.git_db.get_all_ref_heads("refs/quipu/")
        commit_to_owner: Dict[str, str] = {}
        for commit_hash, ref_name in ref_tuples:
            if commit_hash in commit_to_owner:
                continue
            owner_id = self._get_owner_from_ref(ref_name, local_user_id)
            if owner_id:
                commit_to_owner[commit_hash] = owner_id
        return commit_to_owner

    def sync(self, local_user_id: str):
        """
        执行增量补水操作。
        此实现经过重构，以确保在从零重建时能够处理完整的历史图谱。
        """
        # --- 阶段 1: 发现 ---
        all_ref_heads = [t[0] for t in self.git_db.get_all_ref_heads("refs/quipu/")]
        if not all_ref_heads:
            logger.debug("✅ Git 中未发现 Quipu 引用，无需补水。")
            return

        # 1.1 获取所有 Quipu 历史中的完整 commit 日志
        all_git_logs = self.git_db.log_ref(all_ref_heads)
        if not all_git_logs:
            logger.debug("✅ Git 中未发现 Quipu 历史，无需补水。")
            return
        log_map = {entry["hash"]: entry for entry in all_git_logs}
        
        # 1.2 确定 HEAD commit 的所有者
        commit_owners = self._get_commit_owners(local_user_id)

        # 1.3 计算需要插入的节点 (所有历史节点 - 已在数据库中的节点)
        db_hashes = self.db_manager.get_all_node_hashes()
        missing_hashes = set(log_map.keys()) - db_hashes
        
        if not missing_hashes:
            logger.debug("✅ 数据库与 Git 历史一致，无需补水。")
            return
            
        logger.info(f"发现 {len(missing_hashes)} 个需要补水的节点。")

        # --- 阶段 2: 批量准备数据 ---
        nodes_to_insert: List[Tuple] = []
        edges_to_insert: List[Tuple] = []

        tree_hashes = [log_map[h]["tree"] for h in missing_hashes if h in log_map]
        trees_content = self.git_db.batch_cat_file(tree_hashes)

        tree_to_meta_blob: Dict[str, str] = {}
        meta_blob_hashes: List[str] = []
        for tree_hash, content_bytes in trees_content.items():
            entries = self._parser._parse_tree_binary(content_bytes)
            if "metadata.json" in entries:
                blob_hash = entries["metadata.json"]
                tree_to_meta_blob[tree_hash] = blob_hash
                meta_blob_hashes.append(blob_hash)
        metas_content = self.git_db.batch_cat_file(meta_blob_hashes)

        for commit_hash in missing_hashes:
            log_entry = log_map[commit_hash]
            tree_hash = log_entry["tree"]
            owner_id = commit_owners.get(commit_hash, local_user_id)

            meta_blob_hash = tree_to_meta_blob.get(tree_hash)
            if not meta_blob_hash or meta_blob_hash not in metas_content:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 metadata.json 内容")
                continue

            output_tree = self._parser._parse_output_tree_from_body(log_entry["body"])
            if not output_tree:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 Output-Tree trailer")
                continue

            try:
                meta_bytes = metas_content[meta_blob_hash]
                meta_data = json.loads(meta_bytes)
                nodes_to_insert.append(
                    (
                        commit_hash, owner_id, output_tree,
                        meta_data.get("type", "unknown"),
                        float(meta_data.get("exec", {}).get("start") or log_entry["timestamp"]),
                        meta_data.get("summary", "No summary"),
                        meta_data.get("generator", {}).get("id"),
                        meta_bytes.decode("utf-8"), None
                    )
                )
                for p_hash in log_entry["parent"].split():
                    if p_hash in log_map:
                        edges_to_insert.append((commit_hash, p_hash))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析 {commit_hash[:7]} 的元数据失败: {e}")

        # --- 阶段 3: 批量写入数据库 ---
        if nodes_to_insert:
            self.db_manager.batch_insert_nodes(nodes_to_insert)
            logger.info(f"💧 {len(nodes_to_insert)} 个节点元数据已补水。")
        if edges_to_insert:
            self.db_manager.batch_insert_edges(edges_to_insert)
            logger.info(f"💧 {len(edges_to_insert)} 条边关系已补水。")
~~~~~

### 下一步建议

你已经拥有了正确的 Git 引用结构和一个健壮的 `Hydrator`。现在是最后一次验证。

1.  **应用代码补丁**: 使用上述内容，**完整覆盖** `packages/quipu-engine/src/quipu/core/hydrator.py` 文件。

2.  **重建缓存**:
    ```bash
    # 确保你位于 user_a_repo 或 user_b_repo 目录
    # 确保 .quipu/history.sqlite 不存在
    rm .quipu/history.sqlite

    # 运行重建命令
    qd cache rebuild --force
    ```

3.  **验证**:
    *   **检查日志**: 你现在**必须**看到 `发现 406 个需要补水的节点` 的日志，并且整个过程不应再有任何错误。
    *   **运行 `qd ui`**: 它现在应该会正常启动，并显示包含所有 406 个节点的、关系完整的历史图谱。
