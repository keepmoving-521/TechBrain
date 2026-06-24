"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from techbrain.app import create_app
from techbrain.core.config import Environment, Settings


@pytest.fixture
def settings() -> Settings:
    """Return deterministic test settings."""
    return Settings(
        environment=Environment.TEST,
        debug=False,
        docs_enabled=True,
        log_level="INFO",
        log_format="console",
    )


@pytest.fixture
def app(settings: Settings):
    """Return a configured test application."""
    return create_app(settings)


@pytest.fixture
def client(app) -> TestClient:
    """Return a client that captures server-side failures as responses."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
