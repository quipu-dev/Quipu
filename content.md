# fix: 修复测试失败并增强插件加载健壮性

## 用户需求
根据测试报告，修复三个失败的测试用例，涉及 `quipu save` 命令在创世状态下的行为以及插件加载的容错性测试。

## 评论
这三个失败暴露了两个独立的逻辑缺陷：
1.  `save` 命令对“干净”状态的定义不够完整，未能覆盖初始空仓库的场景。
2.  插件加载的容错性测试未能正确触发被测代码路径。

修复这些问题将使 `save` 命令的行为更符合用户预期，并确保插件系统的健壮性得到有效验证。

## 目标
1.  修改 `quipu save` 命令的实现，使其在空仓库且无文件变更的初始状态下，能正确识别为“干净”状态，避免创建不必要的快照。
2.  修正 `test_plugin_resilience.py` 中的两个测试用例，确保它们能够正确地测试到加载损坏插件时的错误处理和日志记录逻辑。

## 基本原理
通过对 `main.py` 中 `save` 函数的逻辑进行增强，并调整 `test_plugin_resilience.py` 的测试设置以直接调用 `load_plugins` 函数，我们可以精确地修复已发现的问题。这遵循了单元测试和集成测试的最佳实践，即确保测试代码准确地隔离并验证目标行为。

## 标签
#intent/fix #flow/ready #priority/critical
#comp/cli #comp/runtime #comp/tests
#concept/state #concept/executor
#scope/core
#ai/instruct
#task/domain/testing #task/object/bug-fix #task/action/fix
#task/state/continue #task/status/active

---

## Script

### Acts 1: 修复 `save` 命令的创世状态检测逻辑

我们将在 `packages/quipu-cli/src/quipu/cli/main.py` 中更新 `save` 命令，使其能够正确处理空仓库的初始状态。

~~~~~act
replace packages/quipu-cli/src/quipu/cli/main.py
~~~~~
~~~~~python
    # 判断是否 clean
    status = "DIRTY"
    if engine.current_node:
        current_tree_hash = engine.git_db.get_tree_hash()
        if engine.current_node.output_tree == current_tree_hash:
            status = "CLEAN"

    if status == "CLEAN":
        typer.secho("✅ 工作区状态未发生变化，无需创建快照。", fg=typer.colors.GREEN, err=True)
        ctx.exit(0)
~~~~~
~~~~~python
    # 判断是否 clean
    current_tree_hash = engine.git_db.get_tree_hash()

    # 1. 正常 Clean: current_node 存在且与当前 hash 一致
    is_node_clean = (engine.current_node is not None) and (
        engine.current_node.output_tree == current_tree_hash
    )

    # 2. 创世 Clean: 历史为空 且 当前是空树
    EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    is_genesis_clean = (not engine.history_graph) and (current_tree_hash == EMPTY_TREE_HASH)

    if is_node_clean or is_genesis_clean:
        typer.secho("✅ 工作区状态未发生变化，无需创建快照。", fg=typer.colors.GREEN, err=True)
        ctx.exit(0)
~~~~~

### Acts 2: 修正插件容错性测试

现在，我们将修改 `tests/test_plugin_resilience.py`，使其直接调用 `load_plugins` 函数，从而正确测试其错误处理能力。

~~~~~act
write_file tests/test_plugin_resilience.py
~~~~~
~~~~~python
import pytest
import logging
from pathlib import Path

from quipu.core.executor import Executor
from quipu.core.plugin_loader import load_plugins


class TestPluginResilience:
    @pytest.fixture
    def executor(self, tmp_path) -> Executor:
        return Executor(root_dir=tmp_path, yolo=True)

    @pytest.fixture
    def plugin_dir(self, tmp_path) -> Path:
        p_dir = tmp_path / "plugins"
        p_dir.mkdir()
        return p_dir

    def test_load_plugin_with_syntax_error(self, executor: Executor, plugin_dir: Path, caplog):
        """验证加载有语法错误的插件不会使程序崩溃。"""
        from quipu.acts.basic import register as register_basic_acts

        # 1. 创建一个有语法错误的插件
        bad_plugin_file = plugin_dir / "bad_syntax.py"
        bad_plugin_file.write_text("def register(executor):\n  print('unbalanced parentheses'", encoding="utf-8")

        # 2. 注册核心 Acts
        register_basic_acts(executor)
        num_acts_before = len(executor.get_registered_acts())

        # 3. 加载插件
        caplog.set_level(logging.ERROR)
        # 直接调用 loader，而不是通过 manager，以确保文件被处理
        load_plugins(executor, plugin_dir)

        # 4. 验证
        assert "加载插件 bad_syntax.py 失败" in caplog.text
        num_acts_after = len(executor.get_registered_acts())
        assert num_acts_after == num_acts_before, "不应注册任何新 Act"
        assert "write_file" in executor.get_registered_acts(), "核心 Act 应该仍然存在"

    def test_load_plugin_with_registration_error(self, executor: Executor, plugin_dir: Path, caplog):
        """验证插件在 register() 函数中抛出异常不会使程序崩溃。"""
        # 1. 创建一个在注册时会失败的插件
        bad_plugin_file = plugin_dir / "fail_on_register.py"
        plugin_content = """
def register(executor):
    raise ValueError("Something went wrong during registration")
"""
        bad_plugin_file.write_text(plugin_content, encoding="utf-8")

        # 2. 加载插件
        caplog.set_level(logging.ERROR)
        # 直接调用 loader
        load_plugins(executor, plugin_dir)

        # 3. 验证
        assert "加载插件 fail_on_register.py 失败" in caplog.text
        assert "ValueError: Something went wrong" in caplog.text
        assert len(executor.get_registered_acts()) == 0
~~~~~
