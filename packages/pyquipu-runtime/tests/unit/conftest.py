from quipu.test_utils.fixtures import executor, isolated_vault


def pytest_configure(config):
    """注册自定义标记以消除警告"""
    config.addinivalue_line("markers", "timeout(seconds): kill test after a certain time")


__all__ = ["executor", "isolated_vault"]
