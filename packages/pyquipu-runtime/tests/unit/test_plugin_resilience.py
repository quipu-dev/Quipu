from pathlib import Path

import pytest
from quipu.runtime.executor import Executor
from quipu.runtime.plugin_loader import load_plugins


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
        from quipu.acts.basic import register as register_basic_acts

        # 1. 创建一个有语法错误的插件
        bad_plugin_file = plugin_dir / "bad_syntax.py"
        bad_plugin_file.write_text("def register(executor):\n  print('unbalanced parentheses'", encoding="utf-8")

        # 2. 注册核心 Acts
        register_basic_acts(executor)
        num_acts_before = len(executor.get_registered_acts())

        # 3. 加载插件
        load_plugins(executor, plugin_dir)

        # 4. 验证错误日志被记录
        assert "加载插件 bad_syntax.py 失败" in caplog.text

        num_acts_after = len(executor.get_registered_acts())
        assert num_acts_after == num_acts_before, "不应注册任何新 Act"
        assert "write_file" in executor.get_registered_acts(), "核心 Act 应该仍然存在"

    def test_load_plugin_with_registration_error(self, executor: Executor, plugin_dir: Path, caplog):
        # 1. 创建一个在注册时会失败的插件
        bad_plugin_file = plugin_dir / "fail_on_register.py"
        plugin_content = """
def register(executor):
    raise ValueError("Something went wrong during registration")
"""
        bad_plugin_file.write_text(plugin_content, encoding="utf-8")

        # 2. 加载插件
        load_plugins(executor, plugin_dir)

        # 3. 验证错误日志被记录
        assert "加载插件 fail_on_register.py 失败" in caplog.text
        assert len(executor.get_registered_acts()) == 0
