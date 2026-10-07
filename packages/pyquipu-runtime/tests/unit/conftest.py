from quipu.test_utils.fixtures import executor, isolated_vault


def pytest_configure(config):
    config.addinivalue_line("markers", "timeout(seconds): kill test after a certain time")


__all__ = ["executor", "isolated_vault"]
