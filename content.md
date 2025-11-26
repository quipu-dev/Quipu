# fix: 更新测试用例以匹配重构后的根目录发现函数

## 用户需求
在之前的重构中，`find_project_root` 被重命名为 `find_git_repository_root` 并统一放在了 `quipu.cli.utils` 模块中。相关的测试文件 (`tests/test_head_and_root.py` 和 `tests/test_plugins.py`) 没有被同步更新，导致了 `ImportError`。

## 评论
这是一个标准的重构后遗留问题。修复它很简单，只需要定位到错误的导入和函数调用，并将其更新为最新的版本即可。

## 目标
1.  修复 `tests/test_head_and_root.py` 中的导入错误和函数调用。
2.  修复 `tests/test_plugins.py` 中的导入错误和函数调用。
3.  确保所有测试都能成功收集并通过。

## 基本原理
通过 `replace` 指令，我们将错误的导入语句 `from quipu.cli.factory import find_project_root` 修正为正确的 `from quipu.cli.utils import find_git_repository_root`。同时，将测试代码中所有对旧函数名 `find_project_root` 的调用也更新为新函数名 `find_git_repository_root`。

## 标签
#intent/fix #flow/ready #priority/critical #comp/tests #scope/core #ai/instruct

---

## Script

### Acts 1: 修复 `test_head_and_root.py`

~~~~~act
replace
~~~~~
~~~~~path
tests/test_head_and_root.py
~~~~~
~~~~~python
from quipu.core.state_machine import Engine
from quipu.cli.factory import find_project_root
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
~~~~~
~~~~~python
from quipu.core.state_machine import Engine
from quipu.cli.utils import find_git_repository_root
from quipu.core.git_object_storage import GitObjectHistoryReader, GitObjectHistoryWriter
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
tests/test_head_and_root.py
~~~~~
~~~~~python
class TestRootDiscovery:
    def test_find_project_root(self, tmp_path):
        # /project/.git
        # /project/src/subdir
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()

        subdir = project / "src" / "subdir"
        subdir.mkdir(parents=True)

        # Case 1: From subdir
        assert find_project_root(subdir) == project.resolve()

        # Case 2: From root
        assert find_project_root(project) == project.resolve()

        # Case 3: Outside
        outside = tmp_path / "outside"
        outside.mkdir()
        assert find_project_root(outside) is None
~~~~~
~~~~~python
class TestRootDiscovery:
    def test_find_git_repository_root(self, tmp_path):
        # /project/.git
        # /project/src/subdir
        project = tmp_path / "project"
        project.mkdir()
        (project / ".git").mkdir()

        subdir = project / "src" / "subdir"
        subdir.mkdir(parents=True)

        # Case 1: From subdir
        assert find_git_repository_root(subdir) == project.resolve()

        # Case 2: From root
        assert find_git_repository_root(project) == project.resolve()

        # Case 3: Outside
        outside = tmp_path / "outside"
        outside.mkdir()
        assert find_git_repository_root(outside) is None
~~~~~

### Acts 2: 修复 `test_plugins.py`

~~~~~act
replace
~~~~~
~~~~~path
tests/test_plugins.py
~~~~~
~~~~~python
from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins
from quipu.cli.factory import find_project_root  # 从 Factory 导入辅助函数
~~~~~
~~~~~python
from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins
from quipu.cli.utils import find_git_repository_root  # 从 utils 导入辅助函数
~~~~~

~~~~~act
replace
~~~~~
~~~~~path
tests/test_plugins.py
~~~~~
~~~~~python
    def test_find_project_root(self, tmp_path):
        """测试 Git 项目根目录检测逻辑"""
        # 结构: root/.git, root/src/subdir
        root = tmp_path / "my_project"
        root.mkdir()
        (root / ".git").mkdir()

        subdir = root / "src" / "subdir"
        subdir.mkdir(parents=True)

        # 从子目录查找
        found = find_project_root(subdir)
        assert found == root.resolve()

        # 从根目录查找
        found_root = find_project_root(root)
        assert found_root == root.resolve()

        # 在非 git 目录查找
        orphan = tmp_path / "orphan"
        orphan.mkdir()
        assert find_project_root(orphan) is None
~~~~~
~~~~~python
    def test_find_git_repository_root(self, tmp_path):
        """测试 Git 项目根目录检测逻辑"""
        # 结构: root/.git, root/src/subdir
        root = tmp_path / "my_project"
        root.mkdir()
        (root / ".git").mkdir()

        subdir = root / "src" / "subdir"
        subdir.mkdir(parents=True)

        # 从子目录查找
        found = find_git_repository_root(subdir)
        assert found == root.resolve()

        # 从根目录查找
        found_root = find_git_repository_root(root)
        assert found_root == root.resolve()

        # 在非 git 目录查找
        orphan = tmp_path / "orphan"
        orphan.mkdir()
        assert find_git_repository_root(orphan) is None
~~~~~
