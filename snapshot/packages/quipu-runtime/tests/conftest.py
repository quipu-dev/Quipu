from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyquipu.acts.basic import register as register_basic_acts
from pyquipu.runtime.executor import Executor


@pytest.fixture(autouse=True)
def mock_runtime_bus(monkeypatch):
    """
    自动 patch 所有 runtime 模块中导入的 'bus' 实例。
    """
    m_bus = MagicMock()
    m_bus.get.side_effect = lambda msg_id, **kwargs: msg_id
    patch_targets = [
        "pyquipu.runtime.executor.bus",
        "pyquipu.runtime.plugin_loader.bus",
        "pyquipu.acts.basic.bus",
        "pyquipu.acts.check.bus",
        "pyquipu.acts.git.bus",
        "pyquipu.acts.memory.bus",
        "pyquipu.acts.read.bus",
        "pyquipu.acts.refactor.bus",
        "pyquipu.acts.shell.bus",
    ]
    for target in patch_targets:
        monkeypatch.setattr(target, m_bus, raising=False)
    return m_bus


@pytest.fixture
def executor(tmp_path: Path) -> Executor:
    """
    为运行时测试提供一个隔离的 Executor 实例。
    """
    instance = Executor(root_dir=tmp_path, yolo=True)
    register_basic_acts(instance)
    return instance


@pytest.fixture
def isolated_vault(executor: Executor) -> Path:
    """
    提供 Executor 实例的根工作目录。
    """
    return executor.root_dir