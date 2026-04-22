"""Root conftest — marker registration and session-wide configuration."""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: integration tests requiring external services")
