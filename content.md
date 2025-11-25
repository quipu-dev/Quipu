# fix 修复 storage_reader 测试中的 Hash 格式问题

## 用户需求
修复 `tests/test_storage_reader.py` 中的测试失败。
失败原因是测试用例中使用了简短的 Mock Hash（如 `"hash_a"`），而 `GitObjectHistoryReader` 中的正则严格匹配 40 位 SHA-1 哈希，导致无法解析 `X-Quipu-Output-Tree` Trailer，进而跳过有效节点。

## 目标
1. 修改 `tests/test_storage_reader.py`，使用合法的 40 位字符作为 Mock Hash。
2. 确保 `test_parent_linking_with_gap` 等测试通过。

## 标签
#comp/tests #fix

---

## Script

### Acts 1: 修正测试数据格式

~~~~~act
replace tests/test_storage_reader.py
~~~~~

~~~~~python
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

~~~~~python
    def test_parent_linking_with_gap(self, reader_setup):
        """测试：如果父 Commit 是损坏的节点，子节点应断开链接并视为新的根"""
        reader, writer, git_db, _ = reader_setup
        
        # 1. Create valid Node A
        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        hash_a = "a" * 40
        writer.create_node("plan", h0, hash_a, "A", start_time=1000)
        
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
        hash_c = "c" * 40
        writer.create_node("plan", "hash_b_implied", hash_c, "C", start_time=3000)
        
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

### Acts 2: 补充 GitDB 的测试 (如果尚未添加)

为了确保覆盖率，再次明确添加 `tests/test_git_db.py` 的补充测试部分（如果之前的操作因为某种原因未生效，这里确保其存在；如果已存在则会被追加到文件末尾，可能导致重复，使用 `read_file` 检查或直接使用追加操作）。
鉴于我是 AI，无法实时检查文件状态，保险起见，我将读取 `tests/test_git_db.py` 确认是否已包含 `test_log_ref_basic`。

~~~~~act
read_file tests/test_git_db.py
~~~~~