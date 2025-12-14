好的，我将把这个修复提交。提交信息会说明这是为了修复因 Git 默认分支名变更导致的集成测试失败问题。

~~~~~act
git_add
tests/integration/conftest.py
~~~~~
~~~~~act
git_commit
~~~~~
~~~~~
fix(tests): Use 'HEAD' to avoid hardcoding default branch name

The integration test setup for sync functionality previously hardcoded
'git push origin master'. This causes tests to fail in environments
where the default branch is 'main' or another name.

This commit replaces 'master' with 'HEAD' to ensure the tests push the
current branch, making the test suite resilient to different Git
default branch configurations.
~~~~~
