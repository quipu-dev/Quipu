# refactor: 实现 Git 对象历史读取器

## 用户需求
根据 [实施计划](Quipu%20储存架构改造实施计划%20(TODO).md) ，完成任务 2.3：实现 `GitObjectHistoryReader`，使其能够从 Git 对象数据库中读取历史记录，并将其转换为 `QuipuNode` 对象图谱。

## 评论
这是存储层改造的另一半关键工作。在实现了 `GitObjectHistoryWriter` 之后，我们需要一个对应的读取器来消费这些新格式的数据。`GitObjectHistoryReader` 将使 `quipu log`、TUI (`quipu ui`) 以及所有导航命令能够在新存储架构下正常工作，是实现新旧架构功能对等的必要步骤。

## 目标
1.  增强 `quipu.core.git_db.GitDB` 模块，为其添加读取 Git Commit、Tree 和 Blob 内容的底层方法。
2.  在 `quipu.core.git_object_storage.py` 模块中实现 `GitObjectHistoryReader` 类。
3.  确保 `load_all_nodes` 方法能够正确地：
    *   遍历 `refs/quipu/history` 引用下的所有 Commit。
    *   解析每个 Commit 的 Tree，并读取 `metadata.json` 和 `content.md` 的内容。
    *   根据 Commit 的父子关系，在内存中重建 `QuipuNode` 对象的完整图谱结构。

## 基本原理
我们将继续利用 Git 的底层命令 (plumbing) 来实现精确、高效的数据读取。
1.  首先，在 `GitDB` 中封装 `git log` 和 `git cat-file` 命令。`git log` 用于一次性获取整个历史链的结构化元数据，而 `git cat-file` 则用于按需读取特定 Git 对象（Commit, Tree, Blob）的内容。
2.  `GitObjectHistoryReader` 的实现将采用一个两阶段的方法来构建图谱：
    *   **第一阶段 (节点实例化)**：遍历 `git log` 的输出，为每个 Commit 创建一个临时的 `QuipuNode` 实例，解析并填充其自身的所有属性（如 `output_tree`, `timestamp`, `content` 等），并暂存其父 Commit 的哈希。
    *   **第二阶段 (关系链接)**：在所有节点都创建完毕后，再次遍历节点列表，根据暂存的父哈希建立 `parent` 和 `children` 关系，并推导出每个节点的 `input_tree`（即其父节点的 `output_tree`）。
这种方法确保了即使 `git log` 的输出顺序不确定，也能正确地构建出完整的有向无环图 (DAG)。

## 标签
#comp/engine #concept/history #scope/core

---

## Script

### Acts 1: 增强 GitDB 以支持读取操作

我们需要在 `GitDB` 中添加 `cat_file` 和 `log_ref` 两个核心方法，为 `GitObjectHistoryReader` 提供读取 Git 底层对象的能力。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_db.py
~~~~~
~~~~~python
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
~~~~~
~~~~~python
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

    def log_ref(self, ref_name: str) -> List[Dict[str, str]]:
        """获取指定引用的日志，并解析为结构化数据列表。"""
        # A unique delimiter that's unlikely to appear in commit messages
        DELIMITER = "---QUIPU-LOG-ENTRY---"
        # Format: H=hash, P=parent, T=tree, ct=commit_timestamp, B=body
        log_format = f"%H%n%P%n%T%n%ct%n%B{DELIMITER}"
        
        res = self._run(["log", f"--format={log_format}", ref_name], check=False, log_error=False)
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

### Acts 2: 实现 `GitObjectHistoryReader`

现在，我们将 `GitObjectHistoryReader` 类添加到 `git_object_storage.py` 文件中，并实现其 `load_all_nodes` 方法。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
from quipu.core.git_db import GitDB
from quipu.core.models import QuipuNode
from quipu.core.storage import HistoryWriter

logger = logging.getLogger(__name__)


class GitObjectHistoryWriter(HistoryWriter):
~~~~~
~~~~~python
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
        log_entries = self.git_db.log_ref("refs/quipu/history")
        if not log_entries:
            return []

        temp_nodes: Dict[str, QuipuNode] = {}
        parent_map: Dict[str, str] = {}

        for entry in log_entries:
            commit_hash = entry["hash"]
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
~~~~~