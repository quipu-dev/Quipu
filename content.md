Excellent catch. The `pytest` failure log provides all the clues we need to diagnose this deep and subtle issue. Your suspicion was close, but the problem is even more fundamental: **the tests are not properly isolated from each other**, leading to a state inconsistency that crashes the application.

## fix(tests): Enforce test isolation by changing fixture scope to "function"

### 错误分析
1.  **Assertion Failure**: The test fails with `AssertionError: User B should have at least 1 unique Quipu commit`. This means `user_b_only_commits` was empty. This can only happen if User B's `quipu run` command **failed to create a new commit**.

2.  **The Smoking Gun (from the logs)**: The detailed log reveals the true cause of the failure during User B's `run` command:
    *   `WARNING quipu.core.state_machine:state_machine.py:281 ⚠️ 丢失 HEAD 指针，自动回退到最新历史节点: 15cb1f8`
    *   `ERROR quipu.core.git_db:git_db.py:59 Git plumbing error: 致命错误：bad object 15cb1f8...`
    *   This sequence tells us exactly what happened:
        a. When User B ran `quipu run`, the `Engine` loaded its state. It read its `.quipu/history.sqlite` file.
        b. It found a reference to a commit (`15cb1f8`) and decided this was the most recent parent node.
        c. However, when it tried to perform a `git diff-tree` against this "parent", Git crashed because that commit object **did not exist** in User B's local Git repository.
        d. The `quipu run` command then failed and exited, **never creating the new node for `b1.md`**.

3.  **The Root Cause: Leaky State from Test Fixtures**:
    *   The `sync_test_environment` fixture is defined with `scope="module"`. This means the *same* set of temporary directories (`user_a`, `user_b`, etc.) is reused for **all tests within that file**.
    *   The test `test_collaboration_subscribe_and_fetch` runs before our failing test. In that test, User B successfully fetches User A's history and **populates its SQLite database**.
    *   When our failing test, `test_owner_id_integrity_after_sync`, starts, it receives a User B workspace that has a **stale, pre-populated SQLite database** referencing commits from User A.
    *   However, the Git repository for User B in this new test *hasn't yet fetched User A's objects*. The state between the Quipu cache (`history.sqlite`) and the physical storage (`.git/objects`) is dangerously inconsistent. This inconsistency is what directly causes the `bad object` crash.

### 用户需求
修复 `tests/integration/test_sync_workflow.py` to ensure that each test case runs in a completely clean, isolated environment, preventing state from one test from interfering with another.

### 评论
This is a classic testing pitfall. Discovering and fixing it is a sign of a maturing test suite. By ensuring true isolation, we make our tests more reliable, predictable, and easier to debug in the future.

### 目标
Change the `pytest` fixture scope for `sync_test_environment` from `module` to `function`, forcing `pytest` to create a fresh set of repositories for every single test case.

### 基本原理
By changing `@pytest.fixture(scope="module")` to `@pytest.fixture(scope="function")`, we instruct `pytest` that the setup and teardown logic for this fixture must be run before and after *each function* that uses it, not just once per module. This guarantees a clean slate for every test, eliminating the state leakage that caused the crash.

### 标签
#intent/fix #flow/ready #priority/critical #comp/tests #concept/sync #scope/core #ai/instruct #task/domain/testing #task/object/sync-workflow #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: Fix the Test Isolation

We will now apply the fix to the test file.

~~~~~act
patch_file
tests/integration/test_sync_workflow.py
~~~~~
~~~~~python
@pytest.fixture(scope="module")
def sync_test_environment(tmp_path_factory):
    """
    Sets up a full sync test environment:
~~~~~
~~~~~python
@pytest.fixture(scope="function")
def sync_test_environment(tmp_path_factory):
    """
    Sets up a full sync test environment:
~~~~~

### 下一步建议
1.  **应用修复**: 执行 `patch_file` 指令。
2.  **重新运行测试**: `pytest tests/integration/test_sync_workflow.py`
3.  **预期结果**: All tests, including `test_owner_id_integrity_after_sync`, should now pass. The crash will be gone, and the assertion will succeed because User B's `run` command will execute correctly in a clean environment.
4.  **提交代码**: 执行 `git add` 和 `git commit` 指令，将这个重要的修复固化到历史中。
