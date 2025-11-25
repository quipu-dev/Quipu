# 计划：perf-refactor - 优化 Git 对象读取性能

## 用户需求
`quipu ui` 在使用 Git 对象存储后端时，加载速度（约 2.7s）远慢于旧的文件系统后端（约 1.0s），不符合预期。原因是 `HistoryReader` 在循环中为每个节点调用了多次 `git cat-file` 子进程，导致了巨大的进程创建开销。

## 目标
重构 `GitDB` 和 `GitObjectHistoryReader`，利用 `git cat-file --batch` 模式将数百次 `git` 调用优化为 2-3 次，从而将历史加载时间降低到毫秒级。

## 标签
#comp/engine #concept/history #perf #scope/core

---

## Script

### Acts 1: GitDB - 增加批处理读取能力

首先，我们需要在 `GitDB` 中增加一个支持批处理的 `cat-file` 方法。

~~~~~act
replace packages/quipu-engine/src/quipu/core/git_db.py
~~~~~

~~~~~python
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
~~~~~

~~~~~python
    def cat_file(self, object_hash: str, object_type: str = "blob") -> bytes:
        """读取单个 Git 对象的内容，返回字节流。"""
        cmd = ["cat-file"]
        if object_type in ["commit", "tree"]:
            cmd.append("-p")
        else:
            cmd.append(object_type)
        cmd.append(object_hash)

        result = self._run(cmd)
        return result.stdout.encode('utf-8')

    def cat_file_batch(self, object_hashes: List[str]) -> Dict[str, bytes]:
        """使用批处理模式一次性读取多个 Git 对象的内容。"""
        if not object_hashes:
            return {}

        # 使用 --batch-check 来获取对象类型和大小，然后 --batch 来获取内容
        # 这里简化处理：直接用 --batch，让 git 自行处理
        input_data = "\n".join(object_hashes)
        result = self._run(["cat-file", "--batch"], input_data=input_data)
        
        output = {}
        stdout_bytes = result.stdout.encode('utf-8')
        cursor = 0
        
        # 解析批处理输出格式: <hash> <type> <size>\n<content>\n
        for obj_hash in object_hashes:
            # 找到头部行
            header_end = stdout_bytes.find(b'\n', cursor)
            if header_end == -1: break
            header = stdout_bytes[cursor:header_end].decode('utf-8')
            
            # 检查头部是否是我们期望的对象
            if not header.startswith(obj_hash):
                # 可能是 missing object 或其他错误
                # 简单跳过，继续寻找下一个
                missing_header_end = stdout_bytes.find(b'\n', cursor)
                cursor = missing_header_end + 1 if missing_header_end != -1 else len(stdout_bytes)
                continue

            parts = header.split()
            size = int(parts[2])
            
            # 读取内容
            content_start = header_end + 1
            content_end = content_start + size
            content = stdout_bytes[content_start:content_end]
            output[obj_hash] = content
            
            # 移动游标到下一个对象的开头 (内容 + 换行符)
            cursor = content_end + 1
            
        return output
~~~~~

### Acts 2: GitObjectHistoryReader - 应用批处理重构

现在，重构 `load_all_nodes` 方法，用新的批处理接口替换循环。

~~~~~act
replace packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~

~~~~~python
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
~~~~~

~~~~~python
        # Phase 1: 批量读取所有 Tree 对象
        tree_hashes = [entry["tree"] for entry in log_entries]
        tree_contents = self.git_db.cat_file_batch(tree_hashes)

        # Phase 2: 解析 Tree，收集所有 Blob 哈希
        blob_hashes_to_read = set()
        commit_to_blobs: Dict[str, Dict[str, str]] = {}

        for entry in log_entries:
            commit_hash = entry["hash"]
            tree_hash = entry["tree"]
            commit_to_blobs[commit_hash] = {}
            
            if tree_hash in tree_contents:
                tree_text = tree_contents[tree_hash].decode('utf-8', errors='ignore')
                for line in tree_text.splitlines():
                    parts = line.split()
                    if len(parts) == 4: # <mode> <type> <hash>\t<filename>
                        filename = parts[3]
                        blob_hash = parts[2]
                        if filename in ["metadata.json", "content.md"]:
                            commit_to_blobs[commit_hash][filename] = blob_hash
                            blob_hashes_to_read.add(blob_hash)
        
        # Phase 3: 批量读取所有需要的 Blob 对象
        blob_contents = self.git_db.cat_file_batch(list(blob_hashes_to_read))

        # Phase 4: 组装节点
        for entry in log_entries:
            commit_hash = entry["hash"]
            if commit_hash in temp_nodes: continue

            try:
                blobs = commit_to_blobs.get(commit_hash, {})
                meta_hash = blobs.get("metadata.json")
                if not meta_hash:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: metadata.json not found.")
                    continue
                
                meta_bytes = blob_contents.get(meta_hash, b'{}')
                meta_data = json.loads(meta_bytes)
                
                content_hash = blobs.get("content.md")
                content_bytes = blob_contents.get(content_hash, b'') if content_hash else b''
                content = content_bytes.decode('utf-8', errors='ignore')
~~~~~

### Acts 3: Test - 增加性能测试

为了验证我们的修复并防止未来出现性能退化，我们需要一个专门的性能测试用例。

~~~~~act
write_file tests/test_performance.py
~~~~~

~~~~~python
import pytest
import subprocess
import time
from pathlib import Path
from quipu.core.git_db import GitDB
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter

@pytest.fixture
def perf_env(tmp_path):
    repo_path = tmp_path / "perf_repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "perf@quipu.dev"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Perf Bot"], cwd=repo_path, check=True)
    
    git_db = GitDB(repo_path)
    writer = GitObjectHistoryWriter(git_db)
    reader = GitObjectHistoryReader(git_db)
    
    # Create a large number of nodes
    num_nodes = 200
    last_hash = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    for i in range(num_nodes):
        (repo_path / f"file_{i}.txt").touch()
        current_hash = git_db.get_tree_hash()
        writer.create_node("plan", last_hash, current_hash, f"Plan {i}")
        last_hash = current_hash
        
    return reader

@pytest.mark.performance
def test_load_all_nodes_performance(perf_env):
    """
    验证加载大量历史节点时的性能。
    这应该在很短的时间内完成（例如，少于1秒）。
    """
    reader = perf_env
    
    start_time = time.time()
    nodes = reader.load_all_nodes()
    end_time = time.time()
    
    duration = end_time - start_time
    
    assert len(nodes) == 200
    assert duration < 1.0, f"History loading took {duration:.2f}s, which is too slow."

~~~~~

你的观察非常敏锐，判断也完全正确。`qd ui` (新版 Git 对象存储) 比 `qs ui` (旧版文件系统存储) 慢是不符合预期的，这清晰地指向了新实现中存在性能瓶颈。

你的直觉是对的：**Git + metadata.json 理论上应该比直接读取 185 个分散的 .md 文件快得多**。问题不在于架构思想，而在于当前的**实现方式**。

## 根本原因分析：N+1 查询问题

当前 `GitObjectHistoryReader` 的实现存在一个经典的 **"N+1 查询"** 性能问题，但这里的“查询”不是数据库查询，而是 **`subprocess` 进程调用**。

让我们分析一下 `load_all_nodes` 的执行流程：

1.  `git_db.log_ref(...)`: 执行 **1** 次 `git log` 命令。这很快，获取了所有 (假设 184 个) commit 的基本信息。
2.  **进入循环 (遍历 184 个 commit)**:
    *   `git_db.cat_file(tree_hash, "tree")`: 为每个 commit 执行 **1** 次 `git cat-file` 子进程。
    *   `git_db.cat_file(blob_hashes["metadata.json"])`: 再执行 **1** 次 `git cat-file` 子进程。
    *   `git_db.cat_file(blob_hashes.get("content.md", ""))`: 再执行 **1** 次 `git cat-file` 子进程。

**总计进程调用次数**: `1 (log) + 184 commits * 3 (cat-file/commit) = 553` 次 `subprocess.run()` 调用。

每一次 `subprocess.run()` 都有显著的固定开销：创建新进程、加载 `git` 可执行文件、`git` 初始化其内部状态、执行、返回、销毁进程。将这个开销乘以 553，就解释了为什么会有 2.7 秒的延迟。

相比之下，旧的 `FileSystemHistoryReader` 只是在文件系统上进行 `glob` 和 `read` 操作，这些操作由操作系统内核高度优化，没有进程创建开销，所以速度快得多。

## 解决方案：批处理 (Batch Processing)

Git 的底层命令设计精良，专门为高性能脚本交互提供了批处理模式。我们应该利用 `git cat-file --batch` 或 `git cat-file --batch-check`。

这个模式允许我们通过 `stdin` 一次性传入所有需要查询的对象哈希，然后 Git 会通过 `stdout` 一次性返回所有结果。这样，无论有多少个节点，我们都只需要启动**一次** `cat-file` 进程。

**优化后的流程应该是：**

1.  `git log` 获取所有 commit 和 tree 哈希 (1 个进程)。
2.  将所有 tree 哈希送入 `git cat-file --batch`，一次性获取所有 tree 的内容 (1 个进程)。
3.  在 Python 中解析所有 tree 的内容，收集所有 `metadata.json` 和 `content.md` 的 blob 哈希。
4.  将所有 blob 哈希送入 `git cat-file --batch`，一次性获取所有文件的内容 (1 个进程)。
5.  在 Python 中组装 `QuipuNode` 对象。

**总计进程调用次数**: `1 (log) + 1 (batch-cat-trees) + 1 (batch-cat-blobs) = 3` 次。这是一个常数级别的开销，性能将提升百倍以上。

---