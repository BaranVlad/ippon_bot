import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

logger = logging.getLogger(__name__)


class JsonConfigSource(PydanticBaseSettingsSource):
    """Pydantic-settings source that reads a JSON config file.

    Priority: lower than env vars / dotenv, higher than field defaults.
    """

    def __init__(self, settings_cls: type[BaseSettings], json_path: Path):
        self.json_path = json_path
        super().__init__(settings_cls)

    def get_field_value(self, field, field_name: str) -> tuple[Any, str, bool]:
        # Required override — not used when __call__ is overridden
        return None, "", False  # type: ignore[return-value]

    def __call__(self) -> dict[str, Any]:
        if not self.json_path.exists():
            logger.warning(f"Config file not found: {self.json_path}")
            return {}
        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)
            return {k.lower(): v for k, v in data.items()}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Meta paths (loaded from root .env or defaults)
    # ------------------------------------------------------------------
    sensitive_dir: Path = Path("./secrets")
    config_path: Path = Path("./resources/config/config.json")

    # ------------------------------------------------------------------
    # Secrets (loaded from secrets/.env or system env vars)
    # ------------------------------------------------------------------
    bot_token: str = Field(..., min_length=1)  # единственный обязательный секрет
    google_sheets_spreadsheet_key: str = ""
    polls_spreadsheet_key: str = ""
    spreadsheet_url: str = ""

    # ------------------------------------------------------------------
    # Group settings
    # ------------------------------------------------------------------
    group_chat_id: int = 0
    polls_message_thread_id: Optional[int] = None
    admins: str = ""

    # ------------------------------------------------------------------
    # Runtime config (base = config.json, overridable by env vars)
    # ------------------------------------------------------------------
    debt_threshold: float = -20.0
    reminder_day_of_week: int = 0
    reminder_hour: int = 19
    reminder_minute: int = 0
    timezone: str = "Europe/Moscow"
    google_sheets_debts_range: str = "J2:K15"
    training_check_hour: int = 10
    training_check_minute: int = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def credentials_path(self) -> Path:
        return self.sensitive_dir / "credentials.json"

    @property
    def members_path(self) -> Path:
        return self.sensitive_dir / "members.json"

    @model_validator(mode="after")
    def _warn_empty_optional_secrets(self) -> "Settings":
        """Log warnings for optional secrets that are not configured."""
        optional_fields = {
            "google_sheets_spreadsheet_key": self.google_sheets_spreadsheet_key,
            "polls_spreadsheet_key": self.polls_spreadsheet_key,
            "spreadsheet_url": self.spreadsheet_url,
            "admins": self.admins,
        }
        for name, value in optional_fields.items():
            if not value:
                logger.warning(f"Config/secret '{name}' is empty. Related features may not work.")

        if self.group_chat_id == 0:
            logger.warning("Config 'group_chat_id' is not set. Group features will not work.")

        return self

    def is_admin(self, identifier: str | int) -> bool:
        if not self.admins:
            return False
        allowed = {a.strip() for a in self.admins.split(",")}
        return str(identifier) in allowed

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define config source priority.

        1. Constructor kwargs  (highest)
        2. Environment variables
        3. Dotenv files (.env, secrets/.env)
        4. JSON config file (config.json)
        5. Defaults            (lowest)
        """
        json_path = cls.model_config.get("json_path", Path("./resources/config/config.json"))
        json_source = JsonConfigSource(settings_cls, json_path)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            json_source,
            file_secret_settings,
        )


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
@lru_cache
def get_settings() -> Settings:
    """Build Settings instance with dynamic env-file discovery.

    Checks ``os.environ`` first (for exported vars), then falls back to
    root ``.env`` file to discover ``SENSITIVE_DIR``, then appends
    ``secrets/.env`` if it exists.
    """
    root_env = dotenv_values(".env")

    # Support both exported env vars and root .env file
    sensitive_dir = Path(
        os.environ.get("SENSITIVE_DIR")
        or root_env.get("SENSITIVE_DIR")
        or "./secrets"
    )
    config_path = Path(
        os.environ.get("CONFIG_PATH")
        or root_env.get("CONFIG_PATH")
        or "./resources/config/config.json"
    )

    env_files: list[str | Path] = [".env"]
    secrets_env = sensitive_dir / ".env"
    if secrets_env.exists():
        env_files.append(secrets_env)

    # Inject discovered JSON path for the custom source
    Settings.model_config["json_path"] = config_path

    return Settings(_env_file=env_files)


# Global singleton for convenience.  Lazy readers may call ``get_settings()``
# directly; module-level consumers can keep importing ``settings``.
settings = get_settings()
