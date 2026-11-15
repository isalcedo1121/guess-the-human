"""Local environment configuration. Loading settings opens no cloud connections."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Reserved for later stages; none is required to run the frontend.
    firebase_project_id: str | None = None
    firebase_service_account_json: SecretStr | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
