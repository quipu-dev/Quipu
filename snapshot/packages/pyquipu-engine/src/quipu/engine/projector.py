import json
import logging
import re

from quipu.engine.git_db import GitDB
from quipu.engine.git_storage import GitSnapshotStorage
from quipu.engine.sqlite_db import DatabaseManager

logger = logging.getLogger(__name__)


class CacheProjector:
    def __init__(self, git_db: GitDB, db_manager: DatabaseManager):
        self.git_db = git_db
        self.db_manager = db_manager
        self._storage_parser = GitSnapshotStorage(git_db.root)

    def _get_owner_from_ref(self, ref_name: str, local_user_id: str) -> str | None:
        remote_match = re.match(r"refs/quipu/remotes/[^/]+/([^/]+)/heads/.*", ref_name)
        if remote_match:
            return remote_match.group(1)
        if ref_name.startswith("refs/quipu/local/heads/"):
            return local_user_id
        return None

    def _get_commit_owners(self, local_user_id: str) -> dict[str, str]:
        head_ref_tuples = self.git_db.get_all_ref_heads("refs/quipu/")
        head_owners: dict[str, str] = {}
        for commit_hash, ref_name in head_ref_tuples:
            owner_id = self._get_owner_from_ref(ref_name, local_user_id)
            if owner_id and (ref_name.startswith("refs/quipu/remotes") or commit_hash not in head_owners):
                head_owners[commit_hash] = owner_id

        if not head_owners:
            return {}

        all_git_logs = self.git_db.log_ref(list(head_owners.keys()))
        log_map = {entry["hash"]: entry for entry in all_git_logs}

        final_commit_owners: dict[str, str] = {}
        queue = list(head_owners.keys())

        for commit_hash in queue:
            final_commit_owners[commit_hash] = head_owners[commit_hash]

        visited = set(head_owners.keys())

        while queue:
            child_hash = queue.pop(0)
            owner = final_commit_owners.get(child_hash)
            if not owner or child_hash not in log_map:
                continue

            parent_hashes = log_map[child_hash]["parent"].split()
            for parent_hash in parent_hashes:
                if parent_hash and parent_hash not in visited:
                    final_commit_owners[parent_hash] = owner
                    visited.add(parent_hash)
                    queue.append(parent_hash)

        return final_commit_owners

    def _parse_output_tree_from_body(self, body: str) -> str | None:
        match = re.search(r"X-Quipu-Output-Tree:\s*([0-9a-f]{40})", body)
        return match.group(1) if match else None

    def project(self, local_user_id: str):
        all_ref_heads = [t[0] for t in self.git_db.get_all_ref_heads("refs/quipu/")]
        if not all_ref_heads:
            logger.debug("✅ Git 中未发现 Quipu 引用，无需投影。")
            return

        all_git_logs = self.git_db.log_ref(all_ref_heads)
        if not all_git_logs:
            logger.debug("✅ Git 中未发现 Quipu 历史，无需投影。")
            return
        log_map = {entry["hash"]: entry for entry in all_git_logs}

        commit_owners = self._get_commit_owners(local_user_id)
        db_hashes = self.db_manager.get_all_node_hashes()
        missing_hashes = set(log_map.keys()) - db_hashes

        if not missing_hashes:
            logger.debug("✅ 数据库索引与 Git 历史完全一致，无需投影。")
            return

        logger.info(f"发现 {len(missing_hashes)} 个待投影的历史节点。")

        nodes_to_insert: list[tuple] = []
        edges_to_insert: list[tuple] = []

        tree_hashes = [log_map[h]["tree"] for h in missing_hashes if h in log_map]
        trees_content = self.git_db.batch_cat_file(tree_hashes)

        tree_to_meta_blob: dict[str, str] = {}
        meta_blob_hashes: list[str] = []
        for tree_hash, content_bytes in trees_content.items():
            entries = self._storage_parser._parse_tree_binary(content_bytes)
            if "metadata.json" in entries:
                blob_hash = entries["metadata.json"]
                tree_to_meta_blob[tree_hash] = blob_hash
                meta_blob_hashes.append(blob_hash)
        metas_content = self.git_db.batch_cat_file(meta_blob_hashes)

        for commit_hash in missing_hashes:
            log_entry = log_map[commit_hash]
            tree_hash = log_entry["tree"]
            owner_id = commit_owners.get(commit_hash)
            if not owner_id:
                logger.warning(f"跳过 {commit_hash[:7]}: 无法确定所有者")
                continue

            meta_blob_hash = tree_to_meta_blob.get(tree_hash)
            if not meta_blob_hash or meta_blob_hash not in metas_content:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 metadata.json 内容")
                continue

            output_tree = self._parse_output_tree_from_body(log_entry["body"])
            if not output_tree:
                logger.warning(f"跳过 {commit_hash[:7]}: 找不到 Output-Tree trailer")
                continue

            try:
                meta_bytes = metas_content[meta_blob_hash]
                meta_data = json.loads(meta_bytes)
                nodes_to_insert.append(
                    (
                        commit_hash,
                        owner_id,
                        output_tree,
                        meta_data.get("type", "unknown"),
                        float(meta_data.get("exec", {}).get("start") or log_entry["timestamp"]),
                        meta_data.get("summary", "No summary"),
                        meta_data.get("generator", {}).get("id"),
                        meta_bytes.decode("utf-8"),
                        None,
                    )
                )
                for p_hash in log_entry["parent"].split():
                    if p_hash in log_map:
                        edges_to_insert.append((commit_hash, p_hash))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析 {commit_hash[:7]} 元数据失败: {e}")

        if nodes_to_insert:
            self.db_manager.batch_insert_nodes(nodes_to_insert)
            logger.info(f"💧 {len(nodes_to_insert)} 个节点索引已投影。")
        if edges_to_insert:
            self.db_manager.batch_insert_edges(edges_to_insert)
            logger.info(f"💧 {len(edges_to_insert)} 条边拓扑已投影。")
