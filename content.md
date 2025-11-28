好的，`test_writer.py` (SQLite) 的问题已成功修复。

我们现在继续执行修复计划的第二阶段，处理 **Task 2.2**: 修复 `tests/engine/test_git_writer.py`。这个问题与上一步的根源完全相同，都是由于测试代码依赖了已废弃的 `refs/quipu/history` 引用。

## fix: 更新 `test_git_writer` 以适应新的多头 Git 引用模型 (阶段 2.2)

### 错误分析
`test_create_node_end_to_end` 测试用例在 `GitObjectHistoryWriter` 创建一个新节点后，通过 `git rev-parse refs/quipu/history` 命令来获取并验证新创建的 commit hash。由于 `GitObjectHistoryWriter` 的 `create_node` 方法现在创建的是 `refs/quipu/local/heads/{commit_hash}` 引用，`history` 引用不再存在，导致 `git rev-parse` 命令失败并抛出 `subprocess.CalledProcessError`。

### 用户需求
修改 `test_create_node_end_to_end` 测试，使其能够正确验证 `GitObjectHistoryWriter` 在新的多头引用架构下的行为。

### 评论
这个修复将使测试更加健壮和精确。它不再依赖一个全局的、间接的副作用（更新 `history` ref），而是直接验证 `create_node` 方法的返回值 (`QuipuNode` 对象) 和其承诺创建的直接产物（对应的 head ref）。这是一种更好的测试实践。

### 目标
重构 `test_create_node_end_to_end` 的验证逻辑：
1.  停止调用 `git rev-parse refs/quipu/history`。
2.  从 `writer.create_node` 返回的 `node` 对象中直接获取 `commit_hash`。
3.  断言一个新的引用文件确实在 `.git/refs/quipu/local/heads/` 目录下被创建，并且其内容就是正确的 commit hash。

### 基本原理
`GitObjectHistoryWriter.create_node` 的核心职责是创建一个 Git commit 对象，并为其创建一个持久化的 head 引用。测试应该直接验证这个核心职责。通过检查返回的 `node` 对象和文件系统中对应的 ref 文件，我们可以精确地确认该方法是否按预期工作，而无需依赖任何遗留的引用结构。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/history #scope/api #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 更新 `test_git_writer.py` 的验证逻辑

我们将修改 `test_create_node_end_to_end` 方法，使其验证逻辑与新的多头引用架构对齐。

~~~~~act
patch_file
tests/engine/test_git_writer.py
~~~~~
~~~~~python
class TestGitObjectHistoryWriterIntegration:
    """对 GitObjectHistoryWriter 与真实 Git 仓库的交互进行集成测试。"""

    def test_create_node_end_to_end(self, git_writer_setup):
        writer, git_db, repo_path = git_writer_setup

        # 1. 准备工作区状态
        (repo_path / "main.py").write_text("print('hello')", "utf-8")
        output_tree = git_db.get_tree_hash()

        # 2. 调用 create_node
        plan_content = "# feat: Initial implementation\nThis is the first version."
        node = writer.create_node(
            node_type="plan",
            input_tree="4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # Empty tree
            output_tree=output_tree,
            content=plan_content,
        )

        # 3. 验证 Git 状态
        # 3.1 检查引用是否更新
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "refs/quipu/history"], cwd=repo_path, text=True
        ).strip()
        assert len(commit_hash) == 40

        # 3.2 检查 Commit 内容
        commit_data = subprocess.check_output(["git", "cat-file", "-p", commit_hash], cwd=repo_path, text=True)
        assert f"tree " in commit_data
        assert "feat: Initial implementation" in commit_data
        assert f"X-Quipu-Output-Tree: {output_tree}" in commit_data

        # 3.3 检查 Tree 内容
        tree_hash = commit_data.splitlines()[0].split(" ")[1]
        tree_data = subprocess.check_output(["git", "ls-tree", tree_hash], cwd=repo_path, text=True)
        assert "metadata.json" in tree_data
        assert "content.md" in tree_data

        # 3.4 检查 Blob 内容
        meta_blob_hash = [line.split()[2] for line in tree_data.splitlines() if "metadata.json" in line][0]
        meta_content_str = subprocess.check_output(
            ["git", "cat-file", "blob", meta_blob_hash], cwd=repo_path, text=True
        )
        meta_data = json.loads(meta_content_str)

        assert meta_data["meta_version"] == "1.0"
        assert meta_data["type"] == "plan"
        assert meta_data["summary"] == "feat: Initial implementation"
        assert meta_data["generator"]["id"] == "manual"
~~~~~
~~~~~python
class TestGitObjectHistoryWriterIntegration:
    """对 GitObjectHistoryWriter 与真实 Git 仓库的交互进行集成测试。"""

    def test_create_node_end_to_end(self, git_writer_setup):
        writer, git_db, repo_path = git_writer_setup

        # 1. 准备工作区状态
        (repo_path / "main.py").write_text("print('hello')", "utf-8")
        output_tree = git_db.get_tree_hash()

        # 2. 调用 create_node
        plan_content = "# feat: Initial implementation\nThis is the first version."
        node = writer.create_node(
            node_type="plan",
            input_tree="4b825dc642cb6eb9a060e54bf8d69288fbee4904",  # Empty tree
            output_tree=output_tree,
            content=plan_content,
        )

        # 3. 验证 Git 状态
        commit_hash = node.commit_hash
        assert len(commit_hash) == 40

        # 3.1 检查引用是否更新为新的 head 格式
        ref_path = repo_path / ".git" / "refs" / "quipu" / "local" / "heads" / commit_hash
        assert ref_path.is_file(), "A new head ref file was not created."
        assert ref_path.read_text().strip() == commit_hash, "The head ref does not point to the correct commit."

        # 3.2 检查 Commit 内容
        commit_data = subprocess.check_output(["git", "cat-file", "-p", commit_hash], cwd=repo_path, text=True)
        assert f"tree " in commit_data
        assert "feat: Initial implementation" in commit_data
        assert f"X-Quipu-Output-Tree: {output_tree}" in commit_data

        # 3.3 检查 Tree 内容
        tree_hash = commit_data.splitlines()[0].split(" ")[1]
        tree_data = subprocess.check_output(["git", "ls-tree", tree_hash], cwd=repo_path, text=True)
        assert "metadata.json" in tree_data
        assert "content.md" in tree_data

        # 3.4 检查 Blob 内容
        meta_blob_hash = [line.split()[2] for line in tree_data.splitlines() if "metadata.json" in line][0]
        meta_content_str = subprocess.check_output(
            ["git", "cat-file", "blob", meta_blob_hash], cwd=repo_path, text=True
        )
        meta_data = json.loads(meta_content_str)

        assert meta_data["meta_version"] == "1.0"
        assert meta_data["type"] == "plan"
        assert meta_data["summary"] == "feat: Initial implementation"
        assert meta_data["generator"]["id"] == "manual"
~~~~~

### 下一步建议
请执行此计划。成功后，我们将继续处理 `tests/engine/test_git_reader.py`，以完成 **Task 2.3**，这是处理遗留引用问题的下一个关键步骤。
