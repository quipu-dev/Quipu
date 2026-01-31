import subprocess

import pytest
from quipu.engine.git_db import GitDB
from quipu.engine.git_object_storage import GitObjectHistoryWriter
from quipu.engine.sqlite_db import DatabaseManager
from quipu.engine.sqlite_storage import SQLiteHistoryWriter
from quipu.spec.constants import EMPTY_TREE_HASH
from needle.pointer import L


@pytest.fixture
def repo_with_sqlite_db(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", L.user.email, "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", L.user.name, "Test User"], cwd=tmp_path, check=True)

    git_db = GitDB(tmp_path)
    db_manager = DatabaseManager(tmp_path)
    db_manager.init_schema()

    yield db_manager, git_db

    db_manager.close()


def test_writer_handles_idempotent_operations_correctly(repo_with_sqlite_db):
    db_manager, git_db = repo_with_sqlite_db

    # 1. Initialize the stack
    git_writer = GitObjectHistoryWriter(git_db)
    sqlite_writer = SQLiteHistoryWriter(git_writer, db_manager)

    # 2. Get initial state (Genesis)
    genesis_tree = EMPTY_TREE_HASH

    # 3. Create Node 1 (State A)
    # Since we are not actually changing files in the workdir, we manually specify input/output trees.
    # We simulate a "change" by creating a tree manually.

    # Create a dummy file blob
    blob_hash = git_db.hash_object(b"some content")
    # Create a tree containing that blob
    tree_hash_a = git_db.mktree(f"100644 blob {blob_hash}\tfile.txt")

    node_1 = sqlite_writer.create_node(
        node_type="plan",
        input_tree=genesis_tree,
        output_tree=tree_hash_a,
        content="Plan 1",
        summary_override="First Operation",
    )
    commit_1 = node_1.filename.name

    # 4. Create Node 2 (State A -> State A) - Idempotent!
    # Input tree is Node 1's output. Output tree is STILL Node 1's output.
    node_2 = sqlite_writer.create_node(
        node_type="plan",
        input_tree=tree_hash_a,
        output_tree=tree_hash_a,  # Same tree!
        content="Plan 2 (Idempotent)",
        summary_override="Second Operation (Idempotent)",
    )
    commit_2 = node_2.filename.name

    assert commit_1 != commit_2, "Two distinct commits should be created even if trees are identical"

    # 5. Verify edges in SQLite
    conn = db_manager._get_conn()
    cursor = conn.execute("SELECT parent_hash FROM edges WHERE child_hash = ?", (commit_2,))
    row = cursor.fetchone()

    assert row is not None, "Edge for Node 2 should exist"
    parent_hash_in_db = row[0]

    # 6. Assertions
    assert parent_hash_in_db != commit_2, "CRITICAL: Node 2 should NOT be its own parent (Self-Loop detected!)"
    assert parent_hash_in_db == commit_1, "Node 2 should point to Node 1 as parent"

    print(f"\nVerified: {commit_2[:7]} (parent: {parent_hash_in_db[:7]}) -> {commit_1[:7]}")
