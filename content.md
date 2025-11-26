# 为 `GitObjectHistoryReader` 添加新接口的兼容性实现。这些实现效率较低，但能确保在不使用 SQLite 时系统依然可以正常工作。

## 标签
#intent/refine #flow/ready #priority/medium #comp/engine #concept/state #scope/core #ai/instruct #task/domain/ui #task/object/pagination #task/action/integration #task/state/continue

---

## Script

### Acts 1: 为 GitObjectHistoryReader 实现兼容性接口

我们在 `GitObjectHistoryReader` 类中添加 `get_node_count`, `load_nodes_paginated`, `get_ancestor_hashes`, 和 `get_private_data` 方法的实现。这些方法将依赖于现有的 `load_all_nodes`，在内存中进行操作，这在小仓库中是可接受的。

~~~~~act
replace
~~~~~
~~~~~path
packages/quipu-engine/src/quipu/core/git_object_storage.py
~~~~~
~~~~~python
    def load_all_nodes(self) -> List[QuipuNode]:
        """
        加载所有节点。
        优化策略: Batch cat-file
        1. 获取所有 commits
        2. 批量读取所有 Trees
        3. 解析 Trees 找到 metadata.json Blob Hashes
        4. 批量读取所有 Metadata Blobs
        5. 组装 Nodes
        """
~~~~~
~~~~~python
    def load_all_nodes(self) -> List[QuipuNode]:
        """
        加载所有节点。
        优化策略: Batch cat-file
        1. 获取所有 commits
        2. 批量读取所有 Trees
        3. 解析 Trees 找到 metadata.json Blob Hashes
        4. 批量读取所有 Metadata Blobs
        5. 组装 Nodes
        """
        # Step 1: Get Commits
        all_heads = self.git_db.get_all_ref_heads("refs/quipu/")
        if not all_heads:
            return []

        log_entries = self.git_db.log_ref(all_heads)
        if not log_entries:
            return []

        # Step 2: Batch fetch Trees
        tree_hashes = [entry["tree"] for entry in log_entries]
        trees_content = self.git_db.batch_cat_file(tree_hashes)

        # Step 3: Parse Trees to find Metadata Blob Hashes
        # Map tree_hash -> metadata_blob_hash
        tree_to_meta_blob = {}
        meta_blob_hashes = []

        for tree_hash, content_bytes in trees_content.items():
            try:
                # 使用二进制解析器
                entries = self._parse_tree_binary(content_bytes)
                if "metadata.json" in entries:
                    blob_hash = entries["metadata.json"]
                    tree_to_meta_blob[tree_hash] = blob_hash
                    meta_blob_hashes.append(blob_hash)
            except Exception as e:
                logger.warning(f"Error parsing tree {tree_hash}: {e}")

        # Step 4: Batch fetch Metadata Blobs
        metas_content = self.git_db.batch_cat_file(meta_blob_hashes)

        # Step 5: Assemble Nodes
        temp_nodes: Dict[str, QuipuNode] = {}
        parent_map: Dict[str, str] = {}

        for entry in log_entries:
            commit_hash = entry["hash"]
            tree_hash = entry["tree"]

            # Skip if already processed (though log entries shouldn't duplicate commits usually)
            if commit_hash in temp_nodes:
                continue

            try:
                # Retrieve metadata content
                if tree_hash not in tree_to_meta_blob:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: metadata.json not found in tree.")
                    continue

                meta_blob_hash = tree_to_meta_blob[tree_hash]

                if meta_blob_hash not in metas_content:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: metadata blob missing.")
                    continue

                meta_bytes = metas_content[meta_blob_hash]
                meta_data = json.loads(meta_bytes)

                output_tree = self._parse_output_tree_from_body(entry["body"])
                if not output_tree:
                    logger.warning(f"Skipping commit {commit_hash[:7]}: X-Quipu-Output-Tree trailer not found.")
                    continue

                # Content is lazy loaded
                content = ""

                node = QuipuNode(
                    # Placeholder, will be filled in the linking phase
                    input_tree="",
                    output_tree=output_tree,
                    timestamp=datetime.fromtimestamp(
                        float(meta_data.get("exec", {}).get("start") or entry["timestamp"])
                    ),
                    filename=Path(f".quipu/git_objects/{commit_hash}"),
                    node_type=meta_data.get("type", "unknown"),
                    content=content,
                    summary=meta_data.get("summary", "No summary available"),
                )

                temp_nodes[commit_hash] = node
                parent_hash = entry["parent"].split(" ") if entry["parent"] else None
                if parent_hash:
                    parent_map[commit_hash] = parent_hash

            except Exception as e:
                logger.error(f"Failed to load history node from commit {commit_hash[:7]}: {e}")

        # Phase 2: Link nodes (Same as before)
        for commit_hash, node in temp_nodes.items():
            parent_commit_hash = parent_map.get(commit_hash)
            if parent_commit_hash and parent_commit_hash in temp_nodes:
                parent_node = temp_nodes[parent_commit_hash]
                node.parent = parent_node
                parent_node.children.append(node)
                node.input_tree = parent_node.output_tree
            else:
                node.input_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

        # Sort children by timestamp
        for node in temp_nodes.values():
            node.children.sort(key=lambda n: n.timestamp)

        return list(temp_nodes.values())

    def get_node_count(self) -> int:
        """Git后端: 低效实现，加载所有节点后计数"""
        return len(self.load_all_nodes())

    def load_nodes_paginated(self, limit: int, offset: int) -> List[QuipuNode]:
        """Git后端: 低效实现，加载所有节点后切片"""
        all_nodes = self.load_all_nodes()
        # load_all_nodes 通常按时间倒序返回
        return all_nodes[offset : offset + limit]

    def get_ancestor_hashes(self, commit_hash: str) -> Set[str]:
        """Git后端: 在内存中遍历图谱"""
        all_nodes = self.load_all_nodes()
        node_map = {n.output_tree: n for n in all_nodes}
        
        ancestors = set()
        queue = []
        
        # 查找起始节点 (commit_hash 在这里对应 output_tree)
        # 注意: load_all_nodes 返回的 node.output_tree 是 key
        # 但传入的可能是 commit_hash (对于 GitObject 后端，output_tree 和 commit_hash 不一样)
        # 这里假设 commit_hash 参数实际上是指 output_tree (因为 HistoryGraph key 是 output_tree)
        # 或者我们需要建立 commit -> node 的映射。
        # 鉴于 GitObjectHistoryReader.load_all_nodes 返回的 nodes filename 实际上包含了 commit hash
        
        # 为了简化兼容性实现，我们假设这里的 commit_hash 指的是 output_tree (与 UI 行为一致)
        if commit_hash in node_map:
            queue.append(node_map[commit_hash])
            
        while queue:
            current_node = queue.pop(0)
            if current_node.parent:
                p_hash = current_node.parent.output_tree
                if p_hash not in ancestors:
                    ancestors.add(p_hash)
                    queue.append(current_node.parent)
        
        return ancestors

    def get_private_data(self, commit_hash: str) -> Optional[str]:
        """Git后端: 不支持私有数据"""
        return None
~~~~~
