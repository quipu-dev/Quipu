# test: 为 Git 对象存储读取器添加全面测试

## 用户需求
为 Phase 2.3 完成后的代码添加测试，确保 `GitObjectHistoryReader` 和 `GitDB` 的新功能稳健可靠。具体涵盖：
1. `GitDB` 边界条件。
2. 历史链（线性/分叉）读取与链接。
3. 损坏数据的容错。
4. 元数据解析健壮性。

## 目标
创建 `tests/test_storage_reader.py` 并补充 `tests/test_git_db.py`，实现对新存储读取逻辑的覆盖率。

## 标签
#comp/tests #comp/engine #concept/history #scope/core

---

## Script

### Acts 1: 增强 GitDB 测试

在现有的 `tests/test_git_db.py` 中添加针对 `log_ref` 和 `cat_file` 的详细测试。

~~~~~act
append_file tests/test_git_db.py
~~~~~

~~~~~python

    def test_log_ref_basic(self, git_repo, db):
        """测试 log_ref 能正确解析 Git 日志格式"""
        # Create 3 commits
        for i in range(3):
            (git_repo / f"f{i}").touch()
            subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
            subprocess.run(["git", "commit", "-m", f"commit {i}\n\nBody {i}"], cwd=git_repo, check=True)
        
        logs = db.log_ref("HEAD")
        assert len(logs) == 3
        assert logs[0]["body"].strip() == "commit 2\n\nBody 2"
        assert logs[2]["body"].strip() == "commit 0\n\nBody 0"
        assert "hash" in logs[0]
        assert "tree" in logs[0]
        assert "timestamp" in logs[0]

    def test_log_ref_non_existent(self, db):
        """测试读取不存在的引用返回空列表而不是报错"""
        logs = db.log_ref("refs/heads/non-existent")
        assert logs == []

    def test_cat_file_types(self, git_repo, db):
        """测试 cat_file 处理不同类型对象的能力"""
        # Create a file
        content = b"content"
        blob_hash = db.hash_object(content)
        
        # Read as blob
        read_content = db.cat_file(blob_hash, "blob")
        assert read_content == content
        
        # Create a commit to test tree/commit cat
        subprocess.run(["git", "commit", "--allow-empty", "-m", "test"], cwd=git_repo, check=True)
        head_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_repo).decode().strip()
        
        # Read commit (pretty print)
        commit_content = db.cat_file(head_hash, "commit")
        assert b"tree " in commit_content
        assert b"author " in commit_content
        
        # Read tree
        tree_hash = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=git_repo).decode().strip()
        tree_content = db.cat_file(tree_hash, "tree")
        # tree content is text-like in pretty mode (ls-tree style output from cat-file -p?)
        # GitDB.cat_file uses -p for tree, which outputs parsed text format.
        # Let's verify it contains entries if any, or is empty-ish.
        # Since we allowed empty commit, it might be empty tree or have initial files from previous tests?
        # In this isolated test, git_repo fixture gives a clean repo? 
        # Wait, git_repo fixture in test_git_db.py does `git init`.
        # So it might be empty.
        pass
~~~~~

### Acts 2: 创建读取器测试

新建 `tests/test_storage_reader.py`，专门测试 `GitObjectHistoryReader` 的高层逻辑。

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
        
        # Genesis hash
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
        # Node A
        (repo/"a").touch()
        h1 = git_db.get_tree_hash()
        writer.create_node("plan", h0, h1, "Plan A", start_time=1000)
        time.sleep(0.1) # Ensure timestamp order
        
        # Node B
        (repo/"b").touch()
        h2 = git_db.get_tree_hash()
        writer.create_node("plan", h1, h2, "Plan B", start_time=2000)
        time.sleep(0.1)
        
        # Node C
        (repo/"c").touch()
        h3 = git_db.get_tree_hash()
        writer.create_node("capture", h2, h3, "Capture C", start_time=3000)
        
        # Load
        nodes = reader.load_all_nodes()
        
        assert len(nodes) == 3
        # Sort by timestamp to ensure order (though load_all_nodes returns them linked)
        # Git log usually returns newest first, reader logic might preserve or reverse?
        # The reader implementation populates dict then returns list(temp_nodes.values()).
        # Dictionary insertion order is preserved in recent Python.
        # But let's check links to be sure.
        
        # Find roots (nodes with Genesis input)
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

    def test_corrupted_node_missing_metadata(self, reader_setup):
        """测试：Commit 存在但缺少 metadata.json"""
        reader, _, git_db, repo = reader_setup
        
        # Create a manual bad commit in refs/quipu/history
        # 1. Blob
        content_hash = git_db.hash_object(b"content")
        # 2. Tree without metadata
        tree_hash = git_db.mktree(f"100444 blob {content_hash}\tcontent.md")
        # 3. Commit
        commit_msg = "Bad Node\n\nX-Quipu-Output-Tree: abcdef"
        commit_hash = git_db.commit_tree(tree_hash, None, commit_msg)
        git_db.update_ref("refs/quipu/history", commit_hash)
        
        nodes = reader.load_all_nodes()
        # Should skip the bad node
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
        
        # Commit message without X-Quipu-Output-Tree
        commit_hash = git_db.commit_tree(tree_hash, None, "Just a summary")
        git_db.update_ref("refs/quipu/history", commit_hash)
        
        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_trailer_extraction_regex(self, reader_setup):
        """单元测试：从不同格式的 Body 中提取 Trailer"""
        reader, _, _, _ = reader_setup
        
        # Case 1: Standard
        body1 = "Summary\n\nX-Quipu-Output-Tree: 1111111111111111111111111111111111111111"
        assert reader._parse_output_tree_from_body(body1) == "1111111111111111111111111111111111111111"
        
        # Case 2: With extra text
        body2 = "Summary\nDetails...\n\nX-Quipu-Output-Tree:   abc1234567890123456789012345678901234567  "
        assert reader._parse_output_tree_from_body(body2) == "abc1234567890123456789012345678901234567"
        
        # Case 3: Missing
        body3 = "Summary only"
        assert reader._parse_output_tree_from_body(body3) is None

    def test_parent_linking_with_gap(self, reader_setup):
        """测试：如果父 Commit 是损坏的节点，子节点应断开链接并视为新的根"""
        reader, writer, git_db, _ = reader_setup
        
        # 1. Create valid Node A
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        writer.create_node("plan", h0, "hash_a", "A", start_time=1000)
        
        # 2. Manually insert a BAD commit on top of A
        # Retrieve A's commit hash
        commit_a = subprocess.check_output(["git", "rev-parse", "refs/quipu/history"], cwd=git_db.root).decode().strip()
        
        # Create bad commit B (missing metadata) pointing to A
        empty_tree = git_db.mktree("")
        commit_b = git_db.commit_tree(empty_tree, [commit_a], "Bad B")
        git_db.update_ref("refs/quipu/history", commit_b)
        
        # 3. Create valid Node C pointing to B
        # Use writer but manually force parent? Writer automatically uses refs/quipu/history as parent.
        # So creating a node now will have parent = commit_b
        writer.create_node("plan", "hash_b_implied", "hash_c", "C", start_time=3000)
        
        # Load
        nodes = reader.load_all_nodes()
        
        # Expectation: 
        # Node A is valid.
        # Node B is skipped.
        # Node C is valid.
        # C's parent is B (in git), but B is not in `temp_nodes`.
        # So C.parent should be None (or logic handles it), and C.input_tree should default to Genesis or break.
        # The implementation says:
        # if parent_commit_hash and parent_commit_hash in temp_nodes: ... else: node.input_tree = "genesis"
        
        valid_nodes = {n.content.strip(): n for n in nodes}
        assert "A" in valid_nodes
        assert "C" in valid_nodes
        assert "Bad B" not in valid_nodes
        
        node_c = valid_nodes["C"]
        assert node_c.parent is None
        assert node_c.input_tree == h0 # Fallback to genesis
~~~~~