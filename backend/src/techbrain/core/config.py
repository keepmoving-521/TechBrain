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
    database_url: str = (
        "mysql+pymysql://techbrain:techbrain@127.0.0.1:3306/techbrain?charset=utf8mb4"
    )
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60)
    database_pool_pre_ping: bool = True
    knowledge_root: Path | None = None
    knowledge_file_encoding: Literal["utf-8", "utf-8-sig"] = "utf-8"
    knowledge_ignore_file_name: str = ".techbrainignore"
    knowledge_extra_ignore_patterns: str = ""
    knowledge_include_drafts: bool = False
    knowledge_include_archive: bool = False
    knowledge_sync_batch_size: int = Field(default=100, ge=1, le=1000)
    knowledge_max_file_size_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    knowledge_auto_sync_enabled: bool = False
    knowledge_auto_sync_interval_seconds: int = Field(default=3600, ge=60)

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
