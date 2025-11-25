# fix 修复并增强历史读取器的测试与实现

## 用户需求
`tests/test_storage_reader.py` 中的测试用例失败。失败原因有两个：
1.  `test_parent_linking_with_gap` 使用了非法的短哈希，导致 Trailer 解析失败，有效节点被跳过。
2.  `test_load_forked_history` 的测试设置不正确，并且 `GitObjectHistoryReader` 本身不支持从多个分叉的 ref 中加载历史。

## 评论
这是一个关键的修复和功能增强。为了让 Quipu 支持真实的团队协作场景，历史读取器必须能够处理因并行工作而产生的历史分叉。本次修改将使读取器变得更加健壮，能够发现并加载所有在 `refs/quipu/` 命名空间下的历史分支，同时修复测试中的数据格式错误。

## 目标
1.  **增强 `GitDB`**：使其能够发现所有 Quipu 相关的 ref heads，并能从多个 ref heads 开始记录日志。
2.  **增强 `GitObjectHistoryReader`**：利用 `GitDB` 的新功能来加载所有分叉的历史。
3.  **修复 `tests/test_storage_reader.py`**：修正 `test_parent_linking_with_gap` 中的无效哈希，并重写 `test_load_forked_history` 以正确测试分叉场景。

## 标签
#fix #refactor #comp/engine #comp/tests #concept/history #scope/core

---

## Script

### Acts 1: 增强 GitDB 以支持多 Ref 查询

修改 `git_db.py`，增加 `get_all_ref_heads` 方法，并使 `log_ref` 接受字符串列表。

~~~~~act
write_file packages/quipu-engine/src/quipu/core/git_db.py
~~~~~

~~~~~python
import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union
from contextlib import contextmanager
from quipu.core.exceptions import ExecutionError

logger = logging.getLogger(__name__)

class GitDB:
    """
    Axon 的 Git 底层接口 (Plumbing Interface)。
    负责与 Git 对象数据库交互，维护 Shadow Index 和 Refs。
    """
    def __init__(self, root_dir: Path):
        if not shutil.which("git"):
            raise ExecutionError("未找到 'git' 命令。请安装 Git 并确保它在系统的 PATH 中。")

        self.root = root_dir.resolve()
        self.quipu_dir = self.root / ".quipu"
        self._ensure_git_repo()

    def _ensure_git_repo(self):
        """确保目标是一个 Git 仓库"""
        if not (self.root / ".git").is_dir():
            # 这是一个关键的前置条件检查
            raise ExecutionError(f"工作目录 '{self.root}' 不是一个有效的 Git 仓库。请先运行 'git init'。")

    def _run(
        self,
        args: list[str],
        env: Optional[Dict] = None,
        check: bool = True,
        log_error: bool = True,
        input_data: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """执行 git 命令的底层封装，返回完整的 CompletedProcess 对象"""
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
            
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.root,
                env=full_env,
                capture_output=True,
                text=True,
                check=check,
                input=input_data
            )
            return result
        except subprocess.CalledProcessError as e:
            if log_error:
                logger.error(f"Git plumbing error: {e.stderr}")
            raise RuntimeError(f"Git command failed: {' '.join(args)}\n{e.stderr}") from e

    @contextmanager
    def shadow_index(self):
        """
        上下文管理器：创建一个隔离的 Shadow Index。
        在此上下文内的操作不会污染用户的 .git/index。
        """
        index_path = self.quipu_dir / "tmp_index"
        self.quipu_dir.mkdir(exist_ok=True)
        
        # 定义隔离的环境变量
        env = {"GIT_INDEX_FILE": str(index_path)}
        
        try:
            yield env
        finally:
            # 无论成功失败，必须清理临时索引文件
            if index_path.exists():
                try:
                    index_path.unlink()
                except OSError:
                    logger.warning(f"Failed to cleanup shadow index: {index_path}")

    def get_tree_hash(self) -> str:
        """
        计算当前工作区的 Tree Hash (Snapshot)。
        实现 'State is Truth' 的核心。
        """
        with self.shadow_index() as env:
            # 1. 将当前工作区全量加载到影子索引
            # 使用 ':(exclude).quipu' 确保 Axon 自身数据不影响状态计算
            # -A: 自动处理添加、修改、删除
            # --ignore-errors: 即使某些文件无法读取也继续（尽力而为）
            self._run(
                ["add", "-A", "--ignore-errors", ".", ":(exclude).quipu"],
                env=env
            )
            
            # 2. 将索引写入对象库，返回 Tree Hash
            result = self._run(["write-tree"], env=env)
            return result.stdout.strip()

    def hash_object(self, content_bytes: bytes, object_type: str = "blob") -> str:
        """
        将内容写入 Git 对象数据库并返回对象哈希。
        """
        try:
            result = subprocess.run(
                ["git", "hash-object", "-w", "-t", object_type, "--stdin"],
                cwd=self.root,
                input=content_bytes,
                capture_output=True,
                check=True
            )
            return result.stdout.decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            stderr_str = e.stderr.decode('utf-8') if e.stderr else "No stderr"
            logger.error(f"Git hash-object failed: {stderr_str}")
            raise RuntimeError(f"Git command failed: hash-object\n{stderr_str}") from e

    def mktree(self, tree_descriptor: str) -> str:
        """
        从描述符创建 tree 对象并返回其哈希。
        """
        result = self._run(["mktree"], input_data=tree_descriptor)
        return result.stdout.strip()

    def commit_tree(self, tree_hash: str, parent_hashes: Optional[List[str]], message: str) -> str:
        """
        创建一个 commit 对象并返回其哈希。
        """
        cmd = ["commit-tree", tree_hash]
        if parent_hashes:
            for p in parent_hashes:
                cmd.extend(["-p", p])
        
        result = self._run(cmd, input_data=message)
        return result.stdout.strip()

    def update_ref(self, ref_name: str, commit_hash: str):
        """
        更新引用 (如 refs/quipu/history)。
        防止 Commit 被 GC 回收。
        """
        self._run(["update-ref", ref_name, commit_hash])

    def get_head_commit(self) -> Optional[str]:
        """获取当前工作区 HEAD 的 Commit Hash"""
        try:
            result = self._run(["rev-parse", "HEAD"])
            return result.stdout.strip()
        except RuntimeError:
            return None # 可能是空仓库

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """
        判断两个 Commit 是否具有血统关系。
        用于解决 'Lost Time' 问题。
        """
        # merge-base --is-ancestor A B 返回 0 表示真，1 表示假
        # 我们在这里直接调用 subprocess，因为我们关心返回码而不是输出
        result = self._run(
            ["merge-base", "--is-ancestor", ancestor, descendant],
            check=False, # 必须禁用 check，否则非 0 退出码会抛异常
            log_error=False # 我们不认为这是一个错误
        )
        return result.returncode == 0

    def get_diff_stat(self, old_tree: str, new_tree: str) -> str:
        """
        获取两个 Tree 之间的差异统计 (Human Readable)。
        """
        result = self._run(["diff-tree", "--stat", old_tree, new_tree])
        return result.stdout.strip()

    def get_diff_name_status(self, old_tree: str, new_tree: str) -> List[Tuple[str, str]]:
        """
        获取两个 Tree 之间的文件变更状态列表 (M, A, D, etc.)。
        """
        result = self._run(["diff-tree", "--name-status", "--no-commit-id", "-r", old_tree, new_tree])
        changes = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, path = parts
                changes.append((status, path))
        return changes

    def checkout_tree(self, tree_hash: str):
        """
        将工作区强制重置为目标 Tree 的状态。
        这是一个底层方法，上层应确保工作区的未提交更改已被处理。
        """
        logger.info(f"Executing hard checkout to tree: {tree_hash[:7]}")
        
        # 1. 使用 read-tree 更新索引，这是一个安全的操作
        self._run(["read-tree", tree_hash])
        
        # 2. 从更新后的索引检出文件，-a (all) -f (force)
        self._run(["checkout-index", "-a", "-f"])
        
        # 3. 清理工作区中多余的文件和目录
        # -d: 目录, -f: 强制
        # 移除了 -x 参数，以尊重 .gitignore 规则
        # -e .quipu: 排除 .quipu 目录，防止自毁
        self._run(["clean", "-df", "-e", ".quipu"])
        
        logger.info("✅ Workspace reset to target state.")

    def cat_file(self, object_hash: str, object_type: str = "blob") -> bytes:
        """读取 Git 对象的内容，返回字节流。"""
        # 使用 -p (pretty print) for commits/trees, and no flag for blobs
        cmd = ["cat-file"]
        if object_type in ["commit", "tree"]:
            cmd.append("-p")
        else:
            cmd.append(object_type)
        cmd.append(object_hash)

        result = self._run(cmd)
        return result.stdout.encode('utf-8')

    def get_all_ref_heads(self, prefix: str) -> List[str]:
        """查找指定前缀下的所有 ref heads 并返回其 commit 哈希。"""
        res = self._run(["for-each-ref", f"--format=%(objectname)", prefix], check=False)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        return res.stdout.strip().splitlines()

    def log_ref(self, ref_names: Union[str, List[str]]) -> List[Dict[str, str]]:
        """获取指定引用的日志，并解析为结构化数据列表。"""
        # A unique delimiter that's unlikely to appear in commit messages
        DELIMITER = "---QUIPU-LOG-ENTRY---"
        # Format: H=hash, P=parent, T=tree, ct=commit_timestamp, B=body
        log_format = f"%H%n%P%n%T%n%ct%n%B{DELIMITER}"
        
        if isinstance(ref_names, str):
            refs_to_log = [ref_names]
        else:
            refs_to_log = ref_names

        if not refs_to_log:
            return []
        
        # Git log on multiple refs will automatically show the union of their histories without duplicates.
        cmd = ["log", f"--format={log_format}"] + refs_to_log
        res = self._run(cmd, check=False, log_error=False)

        if res.returncode != 0:
            return []

        entries = res.stdout.strip().split(DELIMITER)
        parsed_logs = []
        for entry in entries:
            if not entry.strip():
                continue
            
            parts = entry.strip().split('\n', 4)
            if len(parts) >= 4:
                parsed_logs.append({
                    "hash": parts[0],
                    "parent": parts[1],
                    "tree": parts[2],
                    "timestamp": parts[3],
                    "body": parts[4] if len(parts) > 4 else ""
                })
        return parsed_logs
~~~~~

### Acts 2: 升级历史读取器以处理分叉

修改 `git_object_storage.py`，使其能够发现并读取所有 Quipu 历史分支。

~~~~~act
write_file packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~

~~~~~python
import json
import logging
import os
import platform
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import importlib.metadata

from quipu.core.git_db import GitDB
from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryReader, HistoryWriter

logger = logging.getLogger(__name__)


class GitObjectHistoryReader(HistoryReader):
    """
    一个从 Git 底层对象读取历史的实现。
    """
    def __init__(self, git_db: GitDB):
        self.git_db = git_db

    def _parse_output_tree_from_body(self, body: str) -> Optional[str]:
        match = re.search(r"X-Quipu-Output-Tree:\s*([0-9a-f]{40})", body)
        return match.group(1) if match else None

    def load_all_nodes(self) -> List[QuipuNode]:
        all_heads = self.git_db.get_all_ref_heads("refs/quipu/")
        if not all_heads:
            return []

        log_entries = self.git_db.log_ref(all_heads)
        if not log_entries:
            return []

        temp_nodes: Dict[str, QuipuNode] = {}
        parent_map: Dict[str, str] = {}

        for entry in log_entries:
            commit_hash = entry["hash"]
            # Git log can return same commit multiple times if it's an ancestor of multiple heads.
            # We only need to process each commit once.
            if commit_hash in temp_nodes:
                continue

            tree_hash = entry["tree"]
            
            try:
                # 1. Read tree content to find metadata and content blobs
                tree_content = self.git_db.cat_file(tree_hash, "tree").decode('utf-8')
                blob_hashes = {}
                for line in tree_content.splitlines():
                    parts = line.split()
                    if len(parts) == 4:
                        # format: <mode> <type> <hash>\t<filename>
                        blob_hashes[parts[3]] = parts[2]
                
                if "metadata.json" not in blob_hashes:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: metadata.json not found.")
                    continue
                
                # 2. Read metadata and content
                meta_bytes = self.git_db.cat_file(blob_hashes["metadata.json"])
                meta_data = json.loads(meta_bytes)
                
                content_bytes = self.git_db.cat_file(blob_hashes.get("content.md", "")) if "content.md" in blob_hashes else b""
                content = content_bytes.decode('utf-8', errors='ignore')

                output_tree = self._parse_output_tree_from_body(entry["body"])
                if not output_tree:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: X-Quipu-Output-Tree trailer not found.")
                    continue

                node = QuipuNode(
                    # Placeholder, will be filled in the linking phase
                    input_tree="", 
                    output_tree=output_tree,
                    timestamp=datetime.fromtimestamp(float(meta_data.get("exec", {}).get("start") or entry["timestamp"])),
                    filename=Path(f".quipu/git_objects/{commit_hash}"),
                    node_type=meta_data.get("type", "unknown"),
                    content=content,
                )
                
                temp_nodes[commit_hash] = node
                # A commit can have multiple parents, we take the first one for our linear history model
                parent_hash = entry["parent"].split(" ")[0] if entry["parent"] else None
                if parent_hash:
                    parent_map[commit_hash] = parent_hash

            except Exception as e:
                logger.error(f"Failed to load history node from commit {commit_hash[:7]}: {e}")

        # Phase 2: Link nodes
        for commit_hash, node in temp_nodes.items():
            parent_commit_hash = parent_map.get(commit_hash)
            if parent_commit_hash and parent_commit_hash in temp_nodes:
                parent_node = temp_nodes[parent_commit_hash]
                node.parent = parent_node
                parent_node.children.append(node)
                node.input_tree = parent_node.output_tree
            else:
                # Node is a root or parent is not a valid Quipu node
                node.input_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904" # Assume genesis from empty tree

        # Sort children by timestamp
        for node in temp_nodes.values():
            node.children.sort(key=lambda n: n.timestamp)
            
        return list(temp_nodes.values())


class GitObjectHistoryWriter(HistoryWriter):
    """
    一个将历史节点作为 Git 底层对象写入存储的实现。
    遵循 Quipu 数据持久化协议规范 (QDPS) v1.0。
    """

    def __init__(self, git_db: GitDB):
        self.git_db = git_db

    def _get_generator_info(self) -> Dict[str, str]:
        """根据 QDPS v1.0 规范，通过环境变量获取生成源信息。"""
        return {
            "id": os.getenv("QUIPU_GENERATOR_ID", "manual"),
            "tool": os.getenv("QUIPU_TOOL", "quipu-cli"),
        }

    def _get_env_info(self) -> Dict[str, str]:
        """获取运行时环境指纹。"""
        try:
            quipu_version = importlib.metadata.version("quipu-engine")
        except importlib.metadata.PackageNotFoundError:
            quipu_version = "unknown"

        return {
            "quipu": quipu_version,
            "python": platform.python_version(),
            "os": platform.system().lower(),
        }

    def _generate_summary(
        self,
        node_type: str,
        content: str,
        input_tree: str,
        output_tree: str,
        **kwargs: Any,
    ) -> str:
        """根据节点类型生成单行摘要。"""
        if node_type == "plan":
            # 尝试从 Markdown 的第一个标题中提取
            match = re.search(r"^\s*#{1,6}\s+(.*)", content, re.MULTILINE)
            if match:
                return match.group(1).strip()
            # 如果找不到标题，则从第一个非空行提取
            for line in content.strip().splitlines():
                clean_line = line.strip()
                if clean_line:
                    return (clean_line[:75] + '...') if len(clean_line) > 75 else clean_line
            return "Plan executed"

        elif node_type == "capture":
            user_message = kwargs.get("message", "").strip()
            
            changes = self.git_db.get_diff_name_status(input_tree, output_tree)
            if not changes:
                auto_summary = "Capture: No changes detected"
            else:
                formatted_changes = [f"{status} {Path(path).name}" for status, path in changes[:3]]
                summary_part = ", ".join(formatted_changes)
                if len(changes) > 3:
                    summary_part += f" ... and {len(changes) - 3} more files"
                auto_summary = f"Capture: {summary_part}"

            return f"{user_message} {auto_summary}".strip() if user_message else auto_summary
        
        return "Unknown node type"

    def create_node(
        self,
        node_type: str,
        input_tree: str,
        output_tree: str,
        content: str,
        **kwargs: Any,
    ) -> QuipuNode:
        """
        在 Git 对象数据库中创建并持久化一个新的历史节点。
        """
        start_time = kwargs.get("start_time", time.time())
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        summary = self._generate_summary(
            node_type, content, input_tree, output_tree, **kwargs
        )

        metadata = {
            "meta_version": "1.0",
            "summary": summary,
            "type": node_type,
            "generator": self._get_generator_info(),
            "env": self._get_env_info(),
            "exec": {"start": start_time, "duration_ms": duration_ms},
        }

        meta_json_bytes = json.dumps(
            metadata, sort_keys=False, ensure_ascii=False
        ).encode("utf-8")
        content_md_bytes = content.encode("utf-8")

        meta_blob_hash = self.git_db.hash_object(meta_json_bytes)
        content_blob_hash = self.git_db.hash_object(content_md_bytes)

        # 使用 100444 权限 (只读文件)
        tree_descriptor = (
            f"100444 blob {meta_blob_hash}\tmetadata.json\n"
            f"100444 blob {content_blob_hash}\tcontent.md"
        )
        tree_hash = self.git_db.mktree(tree_descriptor)

        last_commit_hash: Optional[str] = None
        res = self.git_db._run(["rev-parse", "refs/quipu/history"], check=False, log_error=False)
        if res.returncode == 0:
            last_commit_hash = res.stdout.strip()

        parents = [last_commit_hash] if last_commit_hash else None
        commit_message = f"{summary}\n\nX-Quipu-Output-Tree: {output_tree}"
        new_commit_hash = self.git_db.commit_tree(
            tree_hash=tree_hash, parent_hashes=parents, message=commit_message
        )

        self.git_db.update_ref("refs/quipu/history", new_commit_hash)
        logger.info(f"✅ History node created as commit {new_commit_hash[:7]}")

        # 返回一个 QuipuNode 实例以兼容现有接口
        return QuipuNode(
            input_tree=input_tree,
            output_tree=output_tree,
            timestamp=datetime.fromtimestamp(start_time),
            # 使用 Commit Hash 作为唯一标识符，因为它不再对应单个文件
            filename=Path(f".quipu/git_objects/{new_commit_hash}"),
            node_type=node_type,
            content=content,
        )
~~~~~

### Acts 3: 全面修复和重写读取器测试

使用包含所有修正的新版本 `tests/test_storage_reader.py` 覆盖旧文件。

~~~~~act
write_file tests/test_storage_reader.py
~~~~~

~~~~~python
import json
import pytest
import subprocess
import time
from pathlib import Path
from typing import List

from quipu.core.git_db import GitDB
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
from quipu.core.models import QuipuNode

@pytest.fixture
def reader_setup(tmp_path):
    repo_path = tmp_path / "read_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "reader@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Quipu Reader"], cwd=repo_path, check=True)
    
    git_db = GitDB(repo_path)
    writer = GitObjectHistoryWriter(git_db)
    reader = GitObjectHistoryReader(git_db)
    
    return reader, writer, git_db, repo_path

class TestGitObjectHistoryReader:
    
    def test_load_empty_history(self, reader_setup):
        """测试：没有 Quipu 历史时的行为"""
        reader, _, _, _ = reader_setup
        nodes = reader.load_all_nodes()
        assert nodes == []

    def test_load_linear_history(self, reader_setup):
        """测试：标准的线性历史 A -> B -> C"""
        reader, writer, git_db, repo = reader_setup
        
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
        (repo/"a").touch()
        h1 = git_db.get_tree_hash()
        writer.create_node("plan", h0, h1, "Plan A", start_time=1000)
        time.sleep(0.01)
        
        (repo/"b").touch()
        h2 = git_db.get_tree_hash()
        writer.create_node("plan", h1, h2, "Plan B", start_time=2000)
        time.sleep(0.01)
        
        (repo/"c").touch()
        h3 = git_db.get_tree_hash()
        writer.create_node("capture", h2, h3, "Capture C", start_time=3000)
        
        nodes = reader.load_all_nodes()
        
        assert len(nodes) == 3
        
        roots = [n for n in nodes if n.input_tree == h0]
        assert len(roots) == 1
        node_a = roots[0]
        assert node_a.content.strip() == "Plan A"
        assert node_a.timestamp.timestamp() == 1000.0
        
        assert len(node_a.children) == 1
        node_b = node_a.children[0]
        assert node_b.content.strip() == "Plan B"
        assert node_b.input_tree == h1
        assert node_b.parent == node_a
        
        assert len(node_b.children) == 1
        node_c = node_b.children[0]
        assert node_c.content.strip() == "Capture C"
        assert node_c.node_type == "capture"

    def test_load_forked_history(self, reader_setup):
        """测试：正确加载分叉的历史 A -> B and A -> C"""
        reader, writer, git_db, repo = reader_setup
        
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        (repo/"base").touch()
        hash_a = git_db.get_tree_hash()
        writer.create_node("plan", h0, hash_a, "Plan A", start_time=1000)
        commit_a = git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()
        time.sleep(0.01)

        (repo/"file_b").touch()
        hash_b = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_b, "Plan B", start_time=2000)
        # Rename the ref to create a fork head
        git_db._run(["update-ref", "refs/quipu/branch_b", "refs/quipu/history"])
        time.sleep(0.01)

        # Reset main ref back to commit_a to create another branch
        git_db.update_ref("refs/quipu/history", commit_a)
        
        (repo/"file_c").touch()
        (repo/"file_b").unlink()
        hash_c = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_c, "Plan C", start_time=3000)

        nodes = reader.load_all_nodes()
        
        assert len(nodes) == 3
        
        nodes_by_content = {n.content.strip(): n for n in nodes}
        node_a = nodes_by_content["Plan A"]
        node_b = nodes_by_content["Plan B"]
        node_c = nodes_by_content["Plan C"]
        
        assert node_a.parent is None
        assert node_b.parent == node_a
        assert node_c.parent == node_a
        
        assert len(node_a.children) == 2
        child_contents = sorted([child.content.strip() for child in node_a.children])
        assert child_contents == ["Plan B", "Plan C"]

    def test_corrupted_node_missing_metadata(self, reader_setup):
        """测试：Commit 存在但缺少 metadata.json"""
        reader, _, git_db, repo = reader_setup
        
        content_hash = git_db.hash_object(b"content")
        tree_hash = git_db.mktree(f"100444 blob {content_hash}\tcontent.md")
        commit_msg = f"Bad Node\n\nX-Quipu-Output-Tree: {'a'*40}"
        commit_hash = git_db.commit_tree(tree_hash, None, commit_msg)
        git_db.update_ref("refs/quipu/history", commit_hash)
        
        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_corrupted_node_missing_trailer(self, reader_setup):
        """测试：Commit 存在但缺少 Output Tree Trailer"""
        reader, _, git_db, repo = reader_setup
        
        meta_hash = git_db.hash_object(json.dumps({"type": "plan"}).encode())
        content_hash = git_db.hash_object(b"c")
        tree_hash = git_db.mktree(
            f"100444 blob {meta_hash}\tmetadata.json\n"
            f"100444 blob {content_hash}\tcontent.md"
        )
        
        commit_hash = git_db.commit_tree(tree_hash, None, "Just a summary")
        git_db.update_ref("refs/quipu/history", commit_hash)
        
        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_parent_linking_with_gap(self, reader_setup):
        """测试：如果父 Commit 是损坏的节点，子节点应断开链接并视为新的根"""
        reader, writer, git_db, _ = reader_setup
        
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        hash_a = "a" * 40
        writer.create_node("plan", h0, hash_a, "A", start_time=1000)
        
        commit_a = git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()
        
        empty_tree = git_db.mktree("")
        commit_b_bad = git_db.commit_tree(empty_tree, [commit_a], "Bad B")
        git_db.update_ref("refs/quipu/history", commit_b_bad)
        
        hash_c = "c" * 40
        writer.create_node("plan", "b_implied", hash_c, "C", start_time=3000)
        
        nodes = reader.load_all_nodes()
        
        assert len(nodes) == 2
        valid_nodes = {n.content.strip(): n for n in nodes}
        assert "A" in valid_nodes
        assert "C" in valid_nodes
        
        node_c = valid_nodes["C"]
        assert node_c.parent is None
        assert node_c.input_tree == h0
~~~~~