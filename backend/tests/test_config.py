"""Configuration tests."""

import pytest
from pydantic import ValidationError

from techbrain.core.config import Environment, Settings


def test_settings_accept_environment_overrides() -> None:
    settings = Settings(
        environment="staging",
        host="0.0.0.0",
        port=9000,
        log_format="json",
    )

    assert settings.environment is Environment.STAGING
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000


@pytest.mark.parametrize(
    ("override", "expected_message"),
    [
        ({"debug": True, "log_format": "json"}, "生产环境禁止启用 debug"),
        ({"log_level": "DEBUG", "log_format": "json"}, "生产环境禁止使用 DEBUG"),
        ({"log_format": "console"}, "生产环境必须使用 JSON"),
    ],
)
def test_production_rejects_unsafe_settings(
    override: dict[str, object],
    expected_message: str,
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        Settings(environment="production", **override)
