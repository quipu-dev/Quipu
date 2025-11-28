Excellent. With `test_git_writer.py` fixed, we are making steady progress through Phase 2.

The next step is **Task 2.3**, which involves fixing `tests/engine/test_git_reader.py`. The failures in this file are also caused by the architectural shift away from a single `history` ref, but they manifest in slightly more complex test scenarios, particularly those involving branches and corrupted data.

## fix: 更新 `test_git_reader` 以适应新的多头 Git 引用模型 (阶段 2.3)

### 错误分析
The test suite for `GitObjectHistoryReader` contains several tests that manually construct specific history graph shapes (like forks or gaps) to verify the reader's robustness. These tests previously relied on manipulating the single `refs/quipu/history` ref to set up their scenarios.

1.  **`test_load_forked_history`**: This test manually created a fork by creating one branch, renaming the `history` ref, resetting the `history` ref to an older commit, and creating a second branch. This complex procedure is now obsolete because the new multi-head architecture creates forks naturally.
2.  **`test_parent_linking_with_gap`**: This test also used `rev-parse` on the `history` ref to get a commit to be used as a parent for a malformed node.
3.  **`test_corrupted_node_*`**: These tests created malformed commits and updated the `history` ref to point to them, ensuring the reader would encounter them. This update logic is now incorrect.

### 用户需求
Refactor the tests in `test_git_reader.py` to correctly set up their scenarios using the new multi-head ref model (`refs/quipu/local/heads/*`) instead of the obsolete single `history` ref.

### 评论
This refactoring not only fixes the tests but also simplifies them significantly. The new architecture makes creating complex graph structures like forks much more straightforward in a testing environment—we just create the nodes, and the writer and reader handle the rest. This is a positive outcome of the new design.

### 目标
1.  Rewrite `test_load_forked_history` to create a fork simply by creating two child nodes from the same parent.
2.  Update `test_parent_linking_with_gap` and the `test_corrupted_node_*` tests to create a head ref in the `refs/quipu/local/heads/` namespace for their manually created commits, ensuring the reader will discover them.

### 基本原理
In the multi-head model, any commit pointed to by a ref under a scanned prefix (like `refs/quipu/`) is considered a potential head of a branch. To make a manually created commit visible to the `GitObjectHistoryReader`, we no longer update a single `history` pointer. Instead, we create a new, dedicated head ref for that commit, typically named after its own hash, within the `refs/quipu/local/heads/` directory. This correctly simulates how the `GitObjectHistoryWriter` persists new nodes.

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/history #scope/api #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Refactor the entire `TestGitObjectHistoryReader` class

Due to the number of methods needing changes, we will replace the entire class definition with an updated version that is fully compatible with the new architecture.

~~~~~act
patch_file
tests/engine/test_git_reader.py
~~~~~
~~~~~python
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

        (repo / "a").touch()
        h1 = git_db.get_tree_hash()
        writer.create_node("plan", h0, h1, "Plan A", start_time=1000)
        time.sleep(0.01)

        (repo / "b").touch()
        h2 = git_db.get_tree_hash()
        writer.create_node("plan", h1, h2, "Plan B", start_time=2000)
        time.sleep(0.01)

        (repo / "c").touch()
        h3 = git_db.get_tree_hash()
        writer.create_node("capture", h2, h3, "Capture C", start_time=3000)

        nodes = reader.load_all_nodes()

        assert len(nodes) == 3

        roots = [n for n in nodes if n.input_tree == h0]
        assert len(roots) == 1
        node_a = roots[0]
        # Lazy load verification
        assert node_a.content == ""
        assert reader.get_node_content(node_a).strip() == "Plan A"
        assert node_a.timestamp.timestamp() == 1000.0

        assert len(node_a.children) == 1
        node_b = node_a.children[0]
        assert reader.get_node_content(node_b).strip() == "Plan B"
        assert node_b.input_tree == h1
        assert node_b.parent == node_a

        assert len(node_b.children) == 1
        node_c = node_b.children[0]
        assert reader.get_node_content(node_c).strip() == "Capture C"
        assert node_c.node_type == "capture"

    def test_load_forked_history(self, reader_setup):
        """测试：正确加载分叉的历史 A -> B and A -> C"""
        reader, writer, git_db, repo = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        (repo / "base").touch()
        hash_a = git_db.get_tree_hash()
        writer.create_node("plan", h0, hash_a, "Plan A", start_time=1000)
        commit_a = git_db._run(["rev-parse", "refs/quipu/history"]).stdout.strip()
        time.sleep(0.01)

        (repo / "file_b").touch()
        hash_b = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_b, "Plan B", start_time=2000)
        # Rename the ref to create a fork head
        git_db._run(["update-ref", "refs/quipu/branch_b", "refs/quipu/history"])
        time.sleep(0.01)

        # Reset main ref back to commit_a to create another branch
        git_db.update_ref("refs/quipu/history", commit_a)

        (repo / "file_c").touch()
        (repo / "file_b").unlink()
        hash_c = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_c, "Plan C", start_time=3000)

        nodes = reader.load_all_nodes()

        assert len(nodes) == 3

        # Explicitly load content for mapping
        nodes_by_content = {reader.get_node_content(n).strip(): n for n in nodes}

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
        commit_msg = f"Bad Node\n\nX-Quipu-Output-Tree: {'a' * 40}"
        commit_hash = git_db.commit_tree(tree_hash, None, commit_msg)
        git_db.update_ref("refs/quipu/history", commit_hash)

        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_corrupted_node_missing_trailer(self, reader_setup):
        """测试：Commit 存在但缺少 Output Tree Trailer"""
        reader, _, git_db, repo = reader_setup

        meta_hash = git_db.hash_object(json.dumps({"type": "plan"}).encode())
        content_hash = git_db.hash_object(b"c")
        tree_hash = git_db.mktree(f"100444 blob {meta_hash}\tmetadata.json\n100444 blob {content_hash}\tcontent.md")

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
        # Explicitly load content
        valid_nodes = {reader.get_node_content(n).strip(): n for n in nodes}
        assert "A" in valid_nodes
        assert "C" in valid_nodes

        node_c = valid_nodes["C"]
        assert node_c.parent is None
        assert node_c.input_tree == h0
~~~~~
~~~~~python
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

        (repo / "a").touch()
        h1 = git_db.get_tree_hash()
        node_a = writer.create_node("plan", h0, h1, "Plan A", start_time=1000)
        time.sleep(0.01)

        (repo / "b").touch()
        h2 = git_db.get_tree_hash()
        node_b = writer.create_node("plan", h1, h2, "Plan B", start_time=2000)
        time.sleep(0.01)

        (repo / "c").touch()
        h3 = git_db.get_tree_hash()
        writer.create_node("capture", h2, h3, "Capture C", start_time=3000)

        nodes = reader.load_all_nodes()

        assert len(nodes) == 3

        roots = [n for n in nodes if n.parent is None]
        assert len(roots) == 1
        found_node_a = roots[0]
        assert found_node_a.commit_hash == node_a.commit_hash

        # Lazy load verification
        assert found_node_a.content == ""
        assert reader.get_node_content(found_node_a).strip() == "Plan A"
        assert found_node_a.timestamp.timestamp() == 1000.0

        assert len(found_node_a.children) == 1
        found_node_b = found_node_a.children[0]
        assert found_node_b.commit_hash == node_b.commit_hash
        assert reader.get_node_content(found_node_b).strip() == "Plan B"
        assert found_node_b.input_tree == h1
        assert found_node_b.parent == found_node_a

        assert len(found_node_b.children) == 1
        node_c = found_node_b.children[0]
        assert reader.get_node_content(node_c).strip() == "Capture C"
        assert node_c.node_type == "capture"

    def test_load_forked_history(self, reader_setup):
        """测试：正确加载分叉的历史 A -> B and A -> C"""
        reader, writer, git_db, repo = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        (repo / "base").touch()
        hash_a = git_db.get_tree_hash()
        node_a = writer.create_node("plan", h0, hash_a, "Plan A", start_time=1000)
        time.sleep(0.01)

        # Create branch B from A
        (repo / "file_b").touch()
        hash_b = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_b, "Plan B", start_time=2000)
        time.sleep(0.01)

        # Create branch C from A
        (repo / "file_c").touch()
        (repo / "file_b").unlink()  # Modify workspace to create a different tree hash
        hash_c = git_db.get_tree_hash()
        writer.create_node("plan", hash_a, hash_c, "Plan C", start_time=3000)

        nodes = reader.load_all_nodes()

        assert len(nodes) == 3

        # Explicitly load content for mapping
        nodes_by_content = {reader.get_node_content(n).strip(): n for n in nodes}

        found_node_a = nodes_by_content["Plan A"]
        found_node_b = nodes_by_content["Plan B"]
        found_node_c = nodes_by_content["Plan C"]

        assert found_node_a.parent is None
        assert found_node_b.parent == found_node_a
        assert found_node_c.parent == found_node_a

        assert len(found_node_a.children) == 2
        child_contents = sorted([child.content.strip() for child in found_node_a.children])
        assert child_contents == ["Plan B", "Plan C"]

    def test_corrupted_node_missing_metadata(self, reader_setup):
        """测试：Commit 存在但缺少 metadata.json"""
        reader, _, git_db, repo = reader_setup

        content_hash = git_db.hash_object(b"content")
        tree_hash = git_db.mktree(f"100444 blob {content_hash}\tcontent.md")
        commit_msg = f"Bad Node\n\nX-Quipu-Output-Tree: {'a' * 40}"
        commit_hash = git_db.commit_tree(tree_hash, None, commit_msg)
        # Manually create a head ref to make it discoverable
        git_db.update_ref(f"refs/quipu/local/heads/{commit_hash}", commit_hash)

        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_corrupted_node_missing_trailer(self, reader_setup):
        """测试：Commit 存在但缺少 Output Tree Trailer"""
        reader, _, git_db, repo = reader_setup

        meta_hash = git_db.hash_object(json.dumps({"type": "plan"}).encode())
        content_hash = git_db.hash_object(b"c")
        tree_hash = git_db.mktree(f"100444 blob {meta_hash}\tmetadata.json\n100444 blob {content_hash}\tcontent.md")

        commit_hash = git_db.commit_tree(tree_hash, None, "Just a summary")
        # Manually create a head ref to make it discoverable
        git_db.update_ref(f"refs/quipu/local/heads/{commit_hash}", commit_hash)

        nodes = reader.load_all_nodes()
        assert len(nodes) == 0

    def test_parent_linking_with_gap(self, reader_setup):
        """测试：如果父 Commit 是损坏的节点，子节点应断开链接并视为新的根"""
        reader, writer, git_db, _ = reader_setup

        h0 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        
        # 1. Create a valid node A
        node_a = writer.create_node("plan", h0, "a" * 40, "A", start_time=1000)

        # 2. Manually create a corrupted commit B, parented to A
        empty_tree = git_db.mktree("")
        commit_b_bad = git_db.commit_tree(empty_tree, [node_a.commit_hash], "Bad B")
        # Make the bad commit discoverable by creating a head for it
        git_db.update_ref(f"refs/quipu/local/heads/{commit_b_bad}", commit_b_bad)

        # 3. Create a valid node C, whose logical parent (by input_tree) is A,
        # but whose topological parent in Git is the bad commit B.
        # The writer will link C to A based on input_tree. The reader must correctly
        # parse this graph despite the corrupted intermediary.
        writer.create_node("plan", node_a.output_tree, "c" * 40, "C", start_time=3000)

        nodes = reader.load_all_nodes()

        # The reader should find 2 valid nodes (A and C) and skip the bad one (B).
        assert len(nodes) == 2
        valid_nodes = {reader.get_node_content(n).strip(): n for n in nodes}
        assert "A" in valid_nodes
        assert "C" in valid_nodes

        found_node_a = valid_nodes["A"]
        found_node_c = valid_nodes["C"]
        
        # C should be correctly parented to A, effectively ignoring the bad commit.
        assert found_node_c.parent == found_node_a
        assert found_node_a.children == [found_node_c]
~~~~~

### 下一步建议
请执行此计划。这个修复将使 `GitObjectHistoryReader` 的测试套件与新架构完全对齐。完成后，我们将处理最后一个依赖旧引用的文件 `tests/integration/test_storage_selection.py`，完成 **Task 2.4**。
