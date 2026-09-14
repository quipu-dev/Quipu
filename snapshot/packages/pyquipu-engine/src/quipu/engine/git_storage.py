import importlib.metadata
import json
import logging
import os
import platform
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from quipu.engine.git_db import GitDB
from quipu.spec.constants import EMPTY_TREE_HASH
from quipu.spec.models.graph import QuipuNode
from quipu.spec.protocols.storage import SnapshotStorage

logger = logging.getLogger(__name__)


class GitSnapshotStorage(SnapshotStorage):
    """Git 物理快照存储实现 (Source of Truth).

    负责与底层 Git plumbing 交互，执行 Tree 捕获、检出、Blob/Tree 读写及 Commit 持久化。
    此模块绝不依赖 SQLite。
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir.resolve()
        self.git_db = GitDB(self.root_dir)

    def get_tree_hash(self) -> str:
        return self.git_db.get_tree_hash()

    def capture_workspace(self, message: str | None = None) -> str:
        return self.git_db.get_tree_hash()

    def restore_workspace(self, tree_hash: str) -> None:
        self.git_db.checkout_tree(new_tree_hash=tree_hash)

    def read_blob(self, blob_hash: str) -> bytes:
        return self.git_db.cat_file(blob_hash, "blob")

    def read_tree_blobs(self, tree_hash: str) -> dict[str, bytes]:
        return self.git_db.get_blobs_from_tree(tree_hash)

    def get_diff_stat(self, old_tree: str, new_tree: str, count: int = 30) -> str:
        return self.git_db.get_diff_stat(old_tree, new_tree, count=count)

    def get_diff_name_status(self, old_tree: str, new_tree: str) -> list[tuple[str, str]]:
        return self.git_db.get_diff_name_status(old_tree, new_tree)

    def _get_generator_info(self) -> dict[str, str]:
        return {
            "id": os.getenv("QUIPU_GENERATOR_ID", "manual"),
            "tool": os.getenv("QUIPU_TOOL", "quipu-cli"),
        }

    def _get_env_info(self) -> dict[str, str]:
        try:
            quipu_version = importlib.metadata.version("pyquipu-engine")
        except importlib.metadata.PackageNotFoundError:
            try:
                quipu_version = importlib.metadata.version("quipu-engine")
            except importlib.metadata.PackageNotFoundError:
                quipu_version = "unknown"

        return {
            "quipu": quipu_version,
            "python": platform.python_version(),
            "os": platform.system().lower(),
        }

    def generate_summary(
        self,
        node_type: str,
        content: str,
        input_tree: str,
        output_tree: str,
        summary_override: str | None = None,
        message: str | None = None,
    ) -> str:
        if summary_override:
            return summary_override

        if node_type == "plan":
            match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip()
            first_line = next((line.strip() for line in content.strip().splitlines() if line.strip()), "Plan executed")
            return (first_line[:75] + "...") if len(first_line) > 75 else first_line

        elif node_type == "capture":
            changes = self.git_db.get_diff_name_status(input_tree, output_tree)
            if not changes:
                auto_summary = "Capture: No changes detected"
            else:
                formatted_changes = [f"{status} {Path(path).name}" for status, path in changes[:3]]
                summary_part = ", ".join(formatted_changes)
                if len(changes) > 3:
                    summary_part += f" ... and {len(changes) - 3} more files"
                auto_summary = f"Capture: {summary_part}"

            user_msg = (message or "").strip()
            return f"{user_msg} {auto_summary}".strip() if user_msg else auto_summary

        return "Unknown node type"

    def create_snapshot_commit(
        self,
        node_type: str,
        input_tree: str,
        output_tree: str,
        content: str,
        summary_override: str | None = None,
        parent_commit_hash: str | None = None,
        message: str | None = None,
        owner_id: str | None = None,
        start_time: float | None = None,
    ) -> tuple[QuipuNode, str]:
        """按照 QDPS 规范创建 Git Commit，返回 (QuipuNode, meta_json_str)."""
        actual_start_time = start_time or time.time()
        end_time = time.time()
        duration_ms = int((end_time - actual_start_time) * 1000)

        summary = self.generate_summary(
            node_type=node_type,
            content=content,
            input_tree=input_tree,
            output_tree=output_tree,
            summary_override=summary_override,
            message=message,
        )

        metadata = {
            "meta_version": "1.0",
            "summary": summary,
            "type": node_type,
            "generator": self._get_generator_info(),
            "env": self._get_env_info(),
            "exec": {"start": actual_start_time, "duration_ms": duration_ms},
        }

        meta_json_bytes = json.dumps(metadata, sort_keys=False, ensure_ascii=False).encode("utf-8")
        content_md_bytes = content.encode("utf-8")

        meta_blob_hash = self.git_db.hash_object(meta_json_bytes)
        content_blob_hash = self.git_db.hash_object(content_md_bytes)

        # 构建包含 snapshot tree 强引用的 tree descriptor
        tree_descriptor = (
            f"100444 blob {meta_blob_hash}\tmetadata.json\n"
            f"100444 blob {content_blob_hash}\tcontent.md\n"
            f"040000 tree {output_tree}\tsnapshot"
        )
        tree_hash = self.git_db.mktree(tree_descriptor)

        # 确定父 Commit
        resolved_parent = parent_commit_hash
        if not resolved_parent and input_tree != EMPTY_TREE_HASH:
            resolved_parent = self.git_db.get_commit_by_output_tree(input_tree)

        parents = [resolved_parent] if resolved_parent else None

        commit_message = f"{summary}\n\nX-Quipu-Output-Tree: {output_tree}"
        new_commit_hash = self.git_db.commit_tree(tree_hash=tree_hash, parent_hashes=parents, message=commit_message)

        # 更新本地 head ref
        self.git_db.update_ref(f"refs/quipu/local/heads/{new_commit_hash}", new_commit_hash)

        logger.info(f"✅ Git 快照 Commit 已创建: {new_commit_hash[:7]}")

        node = QuipuNode(
            commit_hash=new_commit_hash,
            input_tree=input_tree,
            output_tree=output_tree,
            timestamp=datetime.fromtimestamp(actual_start_time),
            filename=Path(f".quipu/git_objects/{new_commit_hash}"),
            node_type=node_type,
            content=content,
            summary=summary,
            owner_id=owner_id,
        )

        if resolved_parent:
            node.parent = QuipuNode(
                commit_hash=resolved_parent,
                input_tree="",
                output_tree=input_tree,
                timestamp=datetime.fromtimestamp(0),
                filename=Path(f".quipu/git_objects/{resolved_parent}"),
                node_type="unknown",
                content="",
                summary="",
            )

        return node, meta_json_bytes.decode("utf-8")

    def read_node_content(self, node: QuipuNode) -> str:
        """从 Git 对象库按需提取 content.md."""
        if node.content:
            return node.content

        try:
            commit_bytes = self.git_db.cat_file(node.commit_hash, "commit")
            tree_line = commit_bytes.split(b"\n", 1)[0].decode("utf-8")
            if not tree_line.startswith("tree "):
                return ""
            tree_hash = tree_line.split()[1]

            tree_content_map = self.git_db.batch_cat_file([tree_hash])
            if tree_hash not in tree_content_map:
                return ""

            tree_content = tree_content_map[tree_hash]
            entries = self._parse_tree_binary(tree_content)
            blob_hash = entries.get("content.md")
            if not blob_hash:
                return ""

            content_bytes = self.git_db.cat_file(blob_hash, "blob")
            content = content_bytes.decode("utf-8", errors="ignore")
            node.content = content
            return content
        except Exception as e:
            logger.error(f"Failed to read content for {node.short_hash}: {e}")
            return ""

    def _parse_tree_binary(self, data: bytes) -> dict[str, str]:
        entries = {}
        idx = 0
        length = len(data)
        while idx < length:
            space_idx = data.find(b" ", idx)
            if space_idx == -1:
                break
            null_idx = data.find(b"\0", space_idx + 1)
            if null_idx == -1:
                break
            filename = data[space_idx + 1 : null_idx].decode("utf-8", errors="ignore")
            hash_start = null_idx + 1
            if hash_start + 20 > length:
                break
            hash_bytes = data[hash_start : hash_start + 20]
            entries[filename] = hash_bytes.hex()
            idx = hash_start + 20
        return entries