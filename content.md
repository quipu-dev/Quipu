好的，我分析了测试失败的报告。这些失败是由两个独立但相关的原因造成的，都源于最近对底层存储接口的重构。

1.  **接口不匹配 (`TypeError`)**: `HistoryReader` 接口新增了一个抽象方法 `get_node_blobs`，但测试中使用的模拟类（Mocks）没有实现它，导致大量测试无法实例化而失败。
2.  **行为变更 (`AssertionError`/`KeyError`)**: `git_db.cat_file` 方法现在返回原始二进制数据 (`bytes`) 而不是文本，并且我在 `GitObjectHistoryReader` 中引入了一个调用错误。依赖旧文本输出或受此错误影响的测试因此失败。

我将按照 `测试套件更新.md` 中规划的策略，通过一个计划来系统性地修复整个测试套件。

## [WIP] fix(tests): 修复因接口和底层数据格式变更导致的测试套件失败

### 错误分析
测试套件的大规模失败是底层 `HistoryReader` 接口和 `git_db` 模块行为变更后的正常连锁反应。主要问题有两个：

1.  **模拟类未实现新接口**: 大量测试使用的 `MockHistoryReader` 和 `InMemoryHistoryManager` 没有实现新增的 `get_node_blobs` 抽象方法，导致 `TypeError`。
2.  **逻辑未适配二进制数据**:
    *   `GitObjectHistoryReader.get_node_content` 中对 `git_db.cat_file` 的调用缺少了 `object_type` 参数，导致方法静默失败并返回空字符串，引发了多个 `AssertionError` 和 `KeyError`。
    *   `test_git_db.py` 中的 `test_cat_file_types` 测试用例还在基于文本的假设来断言二进制数据，导致失败。

### 用户需求
修复整个测试套件，使其与新的 `HistoryReader` 接口和 `git_db` 的二进制数据处理行为保持一致，恢复所有测试的通过状态。

### 评论
这次修复是重构后必不可少的一步，它验证了测试套件作为“安全网”的价值。我们将通过更新测试来巩固这次重构的成果，确保系统的健壮性。

### 目标
1.  为所有 `HistoryReader` 的模拟实现添加 `get_node_blobs` 方法，解决所有 `TypeError`。
2.  修正 `GitObjectHistoryReader.get_node_content` 中的方法调用错误。
3.  更新 `test_cat_file_types` 测试，使其能够正确断言二进制数据。

### 基本原理
我们将采用“分而治之”的策略。首先通过实现缺失的接口方法来消除大量的 `TypeError`，这将使我们能够清晰地看到真正的逻辑失败。然后，我们将逐一修复这些因底层行为变更而导致的逻辑错误，确保测试逻辑与代码实现重新对齐。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #comp/engine #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复模拟类中的接口符合性问题

我们将为 `InMemoryHistoryManager` 和 `MockHistoryReader` 添加 `get_node_blobs` 方法的实现，以解决 `TypeError`。

~~~~~act
patch_file
tests/engine/test_engine_memory.py
~~~~~
~~~~~python
class TestEngineWithMemoryBackend:
    def test_align_clean_genesis(self, memory_engine: Engine):
        """测试在创世状态下的对齐。"""
~~~~~
~~~~~python
    def get_node_blobs(self, commit_hash: str) -> Dict[str, bytes]:
        """获取一个节点内所有文件的原始二进制内容，以字典形式返回 {filename: content_bytes}。"""
        # For memory backend, this can be implemented if needed, otherwise return empty.
        return {}


class TestEngineWithMemoryBackend:
    def test_align_clean_genesis(self, memory_engine: Engine):
        """测试在创世状态下的对齐。"""
~~~~~

~~~~~act
patch_file
tests/cli/test_view_model.py
~~~~~
~~~~~python
    def get_node_content(self, node: QuipuNode) -> str:
        # For simplicity, mock content is stored in the node's summary
        return node.summary
~~~~~
~~~~~python
    def get_node_content(self, node: QuipuNode) -> str:
        # For simplicity, mock content is stored in the node's summary
        return node.summary

    def get_node_blobs(self, commit_hash: str) -> Dict[str, bytes]:
        return {}
~~~~~

#### Acts 2: 修正底层逻辑和测试断言

现在，我们修复 `GitObjectHistoryReader` 中的调用错误，并更新 `test_git_db.py` 以正确处理二进制数据。

~~~~~act
patch_file
packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
            if not blob_hash:
                return ""  # No content found

            # 3. Read Blob (also raw binary)
            content_bytes = self.git_db.cat_file(blob_hash)
            content = content_bytes.decode("utf-8", errors="ignore")
~~~~~
~~~~~python
            if not blob_hash:
                return ""  # No content found

            # 3. Read Blob (also raw binary)
            content_bytes = self.git_db.cat_file(blob_hash, "blob")
            content = content_bytes.decode("utf-8", errors="ignore")
~~~~~

~~~~~act
patch_file
tests/engine/test_git_db.py
~~~~~
~~~~~python
        # 5. Verify Tree reading
        read_tree = db.cat_file(tree_hash, "tree")
        # cat-file -p tree_hash output format: "100644 blob <hash>\ttest_file"
        assert b"test_file" in read_tree
        assert blob_hash.encode() in read_tree
~~~~~
~~~~~python
        # 5. Verify Tree reading
        read_tree = db.cat_file(tree_hash, "tree")
        # The raw tree object contains the binary hash, not the hex representation.
        assert b"test_file" in read_tree
        assert bytes.fromhex(blob_hash) in read_tree
~~~~~

### 下一步建议
我们已经应用了所有必要的修复。现在，请重新运行测试套件。预期结果是所有测试都将通过，测试摘要中不再有 `FAILED` 或 `ERROR`。这将确认我们的重构是成功的，并且测试套件已经恢复到健康状态。
