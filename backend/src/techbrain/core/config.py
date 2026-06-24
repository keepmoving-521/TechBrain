"""Environment-aware application settings."""

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[3]


class Environment(StrEnum):
    """Supported runtime environments."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


def _environment_files() -> tuple[Path, Path]:
    environment = os.getenv("TECHBRAIN_ENVIRONMENT", Environment.LOCAL.value).lower()
    return BACKEND_DIR / ".env", BACKEND_DIR / f".env.{environment}"


class Settings(BaseSettings):
    """TechBrain settings loaded from environment variables and dotenv files."""

    model_config = SettingsConfigDict(
        env_prefix="TECHBRAIN_",
        env_file=_environment_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    app_name: str = "TechBrain API"
    app_version: str = "0.1.0"
    environment: Environment = Environment.LOCAL
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False
    docs_enabled: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        """Reject unsafe production logging and debug configuration."""
        if self.environment is Environment.PRODUCTION:
            if self.debug:
                raise ValueError("生产环境禁止启用 debug")
            if self.log_level == "DEBUG":
                raise ValueError("生产环境禁止使用 DEBUG 日志级别")
            if self.log_format != "json":
                raise ValueError("生产环境必须使用 JSON 日志")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
