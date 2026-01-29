好的，我们已经解决了核心代码中的类型错误。现在，`pyright` 指出了测试套件中的一系列问题。这些问题主要集中在测试代码的类型正确性上，包括模拟对象（Mock）的初始化、测试逻辑中对内部状态的不正确访问，以及测试数据缺乏明确的类型注解。

我将生成一个计划来修复所有这些测试文件中的类型错误。

## [WIP] fix: 解决测试套件中的 pyright 类型错误

### 用户需求

修复 `pyright` 在 `packages/**/tests` 目录下报告的所有 20 个类型检查错误。

### 评论

一个类型安全的测试套件和生产代码同样重要。修复这些测试中的类型问题可以防止因测试设置错误而导致的假阳性或假阴性结果，并确保测试代码能够随着核心代码的演进而保持健壮。

### 目标

1.  **修正模拟对象**: 调整 `MockHistoryReader` 的构造函数，使其能够正确处理可选参数，消除 `None` 类型不匹配的错误。
2.  **修正测试逻辑**: 在 TUI 测试中，移除对 `QuipuUiApp` 已不存在属性的访问，改为通过 `GraphViewModel` 的公共 API 进行状态切换和断言。
3.  **统一 `act` 调用**: 在 `test_git.py` 中，确保所有对 `act` 函数的调用都通过 `ActContext` 对象，而不是直接传递 `Executor` 实例。
4.  **明确测试数据类型**: 为所有测试中用作 `executor.execute` 参数的语句列表添加显式的 `List[Statement]` 类型注解。

### 基本原理

我们将系统地解决每一类错误。首先，修复 `MockHistoryReader` 的定义将解决多个测试文件中的连锁问题。接着，重构 `test_tui_reachability.py` 中的测试逻辑，使其与 `ViewModel` 的实际设计保持一致。最后，通过在所有相关的 `act` 测试中添加正确的上下文对象和显式类型注解，来解决剩下的类型不匹配问题。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/type-checking #task/action/bug-fix #task/state/continue #task/status/active

---

### Script

#### Acts 1: 修正 `MockHistoryReader` 和 TUI 测试

我们将首先修复位于 `pyquipu-cli` 测试中的模拟对象和 TUI 测试逻辑。

~~~~~act
patch_file
packages/pyquipu-cli/tests/unit/test_view_model.py
~~~~~
~~~~~python.old
class MockHistoryReader(HistoryReader):
    def __init__(
        self,
        nodes: List[QuipuNode],
        ancestors: Set[str] = None,
        descendants: Set[str] = None,
        private_data: dict[str, str] = None,
    ):
        self._nodes = sorted(nodes, key=lambda n: n.timestamp, reverse=True)
        self._ancestors = ancestors or set()
        self._descendants = descendants or set()
        self._private_data = private_data or {}
~~~~~
~~~~~python.new
class MockHistoryReader(HistoryReader):
    def __init__(
        self,
        nodes: List[QuipuNode],
        ancestors: Optional[Set[str]] = None,
        descendants: Optional[Set[str]] = None,
        private_data: Optional[dict[str, str]] = None,
    ):
        self._nodes = sorted(nodes, key=lambda n: n.timestamp, reverse=True)
        self._ancestors = ancestors or set()
        self._descendants = descendants or set()
        self._private_data = private_data or {}
~~~~~

~~~~~act
patch_file
packages/pyquipu-cli/tests/unit/test_tui_reachability.py
~~~~~
~~~~~python.old
        ancestors = {"a", "root"}
        view_model = view_model_factory([node_root, node_a, node_b], current_hash="a", ancestors=ancestors)
        app = QuipuUiApp(work_dir=Path("."))
        app.view_model = view_model
        app.show_unreachable = False

        nodes_on_page = view_model.load_page(1)
        rendered_nodes = [
            node for node in nodes_on_page if app.show_unreachable or app.view_model.is_reachable(node.output_tree)
        ]

        assert node_b not in rendered_nodes
~~~~~
~~~~~python.new
        ancestors = {"a", "root"}
        view_model = view_model_factory([node_root, node_a, node_b], current_hash="a", ancestors=ancestors)
        
        # 模拟 TUI 切换视图以隐藏不可达节点
        # ViewModel 默认 show_unreachable=True
        view_model.toggle_unreachable()
        assert view_model.show_unreachable is False

        view_model.load_page(1)
        rendered_nodes = view_model.get_nodes_to_render()

        assert node_b not in rendered_nodes
~~~~~

#### Acts 2: 修正 `pyquipu-runtime` 中的 `act` 测试

现在，我们来修复 `git` 相关的测试，并为所有测试中的语句列表添加明确的类型注解。

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_git.py
~~~~~
~~~~~python.old
import shutil
import subprocess
from pathlib import Path

import pytest
from quipu.acts.git import register as register_git_acts
from quipu.runtime.executor import Executor


@pytest.mark.skipif(not shutil.which("git"), reason="Git 命令未找到，跳过 Git 测试")
class TestGitActs:
    @pytest.fixture(autouse=True)
    def setup_git_env(self, executor: Executor, isolated_vault: Path):
        register_git_acts(executor)

        # 执行初始化
        func, _, _ = executor._acts["git_init"]
        func(executor, [])

        # 配置测试用的 user，防止 CI/Test 环境报错
        subprocess.run(["git", "config", "user.email", "quipu@test.com"], cwd=isolated_vault, check=True)
~~~~~
~~~~~python.new
import shutil
import subprocess
from pathlib import Path
from typing import List

import pytest
from quipu.acts.git import register as register_git_acts
from quipu.runtime.executor import Executor
from quipu.spec.protocols.runtime import ActContext, Statement


@pytest.mark.skipif(not shutil.which("git"), reason="Git 命令未找到，跳过 Git 测试")
class TestGitActs:
    @pytest.fixture(autouse=True)
    def setup_git_env(self, executor: Executor, isolated_vault: Path):
        register_git_acts(executor)

        # 执行初始化
        func, _, _ = executor._acts["git_init"]
        ctx = ActContext(executor)
        func(ctx, [])

        # 配置测试用的 user，防止 CI/Test 环境报错
        subprocess.run(["git", "config", "user.email", "quipu@test.com"], cwd=isolated_vault, check=True)
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_git.py
~~~~~
~~~~~python.old
        # 2. Git Add
        git_add, _, _ = executor._acts["git_add"]
        git_add(executor, ["README.md"])
        mock_runtime_bus.success.assert_called_with("acts.git.success.added", targets=["README.md"])

        # 验证状态 (porcelain 输出 ?? 代表未追踪，A 代表已添加)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=isolated_vault, text=True)
        assert "A  README.md" in status

        # 3. Git Commit
        git_commit, _, _ = executor._acts["git_commit"]
        git_commit(executor, ["Initial commit"])
        mock_runtime_bus.success.assert_called_with("acts.git.success.committed", message="Initial commit")

        # 验证提交日志
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=isolated_vault, text=True)
~~~~~
~~~~~python.new
        # 2. Git Add
        git_add, _, _ = executor._acts["git_add"]
        ctx = ActContext(executor)
        git_add(ctx, ["README.md"])
        mock_runtime_bus.success.assert_called_with("acts.git.success.added", targets=["README.md"])

        # 验证状态 (porcelain 输出 ?? 代表未追踪，A 代表已添加)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=isolated_vault, text=True)
        assert "A  README.md" in status

        # 3. Git Commit
        git_commit, _, _ = executor._acts["git_commit"]
        git_commit(ctx, ["Initial commit"])
        mock_runtime_bus.success.assert_called_with("acts.git.success.committed", message="Initial commit")

        # 验证提交日志
        log = subprocess.check_output(["git", "log", "--oneline"], cwd=isolated_vault, text=True)
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_git.py
~~~~~
~~~~~python.old
    def test_git_init_idempotent(self, executor: Executor, mock_runtime_bus):
        # setup_git_env 已经 init 过了，再次 init 应该提示跳过
        func, _, _ = executor._acts["git_init"]
        func(executor, [])
        mock_runtime_bus.warning.assert_called_with("acts.git.warning.repoExists")

    def test_git_status_output_stream(self, executor: Executor, isolated_vault: Path, mock_runtime_bus):
        # 1. 制造一些状态变更
        (isolated_vault / "untracked.txt").write_text("new file")

        # 2. 我们通过 executor.execute 来模拟完整的执行流程
        stmts = [{"act": "git_status", "contexts": []}]
        executor.execute(stmts)

        # 3. 验证 bus 调用
        # 验证执行器日志
~~~~~
~~~~~python.new
    def test_git_init_idempotent(self, executor: Executor, mock_runtime_bus):
        # setup_git_env 已经 init 过了，再次 init 应该提示跳过
        func, _, _ = executor._acts["git_init"]
        ctx = ActContext(executor)
        func(ctx, [])
        mock_runtime_bus.warning.assert_called_with("acts.git.warning.repoExists")

    def test_git_status_output_stream(self, executor: Executor, isolated_vault: Path, mock_runtime_bus):
        # 1. 制造一些状态变更
        (isolated_vault / "untracked.txt").write_text("new file")

        # 2. 我们通过 executor.execute 来模拟完整的执行流程
        stmts: List[Statement] = [{"act": "git_status", "contexts": []}]
        executor.execute(stmts)

        # 3. 验证 bus 调用
        # 验证执行器日志
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_shell.py
~~~~~
~~~~~python.old
import pytest
from quipu.acts.shell import register as register_shell_acts
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext
from quipu.runtime.executor import Executor
~~~~~
~~~~~python.new
from typing import List

import pytest
from quipu.acts.shell import register as register_shell_acts
from quipu.spec.exceptions import ExecutionError
from quipu.spec.protocols.runtime import ActContext, Statement
from quipu.runtime.executor import Executor
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/acts/test_shell.py
~~~~~
~~~~~python.old
    def test_run_command_does_not_swallow_blocks(self, executor: Executor, mock_runtime_bus):
        # 模拟解析器输出两个独立的指令
        statements = [
            {"act": "run_command", "contexts": ["echo 'first'"]},
            {"act": "echo", "contexts": ["second"]},
        ]
        executor.execute(statements)

        # 验证 run_command 的输出
        mock_runtime_bus.data.assert_any_call("first")
~~~~~
~~~~~python.new
    def test_run_command_does_not_swallow_blocks(self, executor: Executor, mock_runtime_bus):
        # 模拟解析器输出两个独立的指令
        statements: List[Statement] = [
            {"act": "run_command", "contexts": ["echo 'first'"]},
            {"act": "echo", "contexts": ["second"]},
        ]
        executor.execute(statements)

        # 验证 run_command 的输出
        mock_runtime_bus.data.assert_any_call("first")
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/test_parser_and_basic_acts.py
~~~~~
~~~~~python.old
import pytest
from quipu.spec.protocols.runtime import ActContext
from quipu.runtime.executor import ExecutionError, Executor
from quipu.runtime.parser import BacktickParser, TildeParser, get_parser
~~~~~
~~~~~python.new
from typing import List

import pytest
from quipu.spec.protocols.runtime import ActContext, Statement
from quipu.runtime.executor import ExecutionError, Executor
from quipu.runtime.parser import BacktickParser, TildeParser, get_parser
~~~~~

~~~~~act
patch_file
packages/pyquipu-runtime/tests/unit/test_parser_and_basic_acts.py
~~~~~
~~~~~python.old
class TestHybridArgs:
    # These tests use executor.execute(), which correctly creates the context,
    # so they don't need changes.
    def test_inline_write_file(self, executor: Executor, isolated_vault: Path):
        stmts = [{"act": "write_file inline.txt", "contexts": ["Inline Content"]}]
        executor.execute(stmts)
        f = isolated_vault / "inline.txt"
        assert f.read_text(encoding="utf-8") == "Inline Content"

    def test_inline_quoted_args(self, executor: Executor, isolated_vault: Path):
        stmts = [{"act": 'write_file "name with spaces.txt"', "contexts": ["Hello"]}]
        executor.execute(stmts)
        f = isolated_vault / "name with spaces.txt"
        assert f.exists()

    def test_mixed_git_commit(self, executor: Executor):
        called_args = []

        def mock_commit(ctx, args):
            called_args.extend(args)

        executor.register("mock_commit", mock_commit)
        stmts = [{"act": 'mock_commit -m "fix bug"', "contexts": []}]
        executor.execute(stmts)
        assert called_args == ["-m", "fix bug"]

    def test_act_parsing_error(self, executor: Executor):
        stmts = [{"act": 'write_file "unclosed string', "contexts": []}]
        with pytest.raises(ExecutionError) as exc:
            executor.execute(stmts)
        assert "Error parsing Act command line" in str(exc.value)
~~~~~
~~~~~python.new
class TestHybridArgs:
    # These tests use executor.execute(), which correctly creates the context,
    # so they don't need changes.
    def test_inline_write_file(self, executor: Executor, isolated_vault: Path):
        stmts: List[Statement] = [{"act": "write_file inline.txt", "contexts": ["Inline Content"]}]
        executor.execute(stmts)
        f = isolated_vault / "inline.txt"
        assert f.read_text(encoding="utf-8") == "Inline Content"

    def test_inline_quoted_args(self, executor: Executor, isolated_vault: Path):
        stmts: List[Statement] = [{"act": 'write_file "name with spaces.txt"', "contexts": ["Hello"]}]
        executor.execute(stmts)
        f = isolated_vault / "name with spaces.txt"
        assert f.exists()

    def test_mixed_git_commit(self, executor: Executor):
        called_args = []

        def mock_commit(ctx, args):
            called_args.extend(args)

        executor.register("mock_commit", mock_commit)
        stmts: List[Statement] = [{"act": 'mock_commit -m "fix bug"', "contexts": []}]
        executor.execute(stmts)
        assert called_args == ["-m", "fix bug"]

    def test_act_parsing_error(self, executor: Executor):
        stmts: List[Statement] = [{"act": 'write_file "unclosed string', "contexts": []}]
        with pytest.raises(ExecutionError) as exc:
            executor.execute(stmts)
        assert "Error parsing Act command line" in str(exc.value)
~~~~~

### 下一步建议

我们已经修复了测试套件中的所有类型错误。现在整个代码库（包括生产代码和测试代码）都应该是类型安全的。

我建议你生成一个 `[COMMIT]` 计划，将这两次修复（核心代码和测试代码）合并为一个逻辑提交，标题可以是 `fix(typing): Resolve all pyright errors across the codebase`。
