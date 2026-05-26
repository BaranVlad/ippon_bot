import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

logger = logging.getLogger(__name__)


def _load_config() -> None:
    """Load configuration from multiple sources into os.environ.
    
    Priority (high to low):
    1. System environment variables
    2. sensitive_dir/.env (secrets)
    3. config.json (non-sensitive settings)
    4. Pydantic defaults
    """
    # Step 1: Load root .env (meta variables: SENSITIVE_DIR, CONFIG_PATH)
    root_env = Path(__file__).parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=False)
    else:
        logger.warning(f"Root .env not found at {root_env}, using system env")

    sensitive_dir = os.getenv("SENSITIVE_DIR", "./secrets")
    config_path = os.getenv("CONFIG_PATH", "./config/config.json")

    # Step 2: Load secrets .env
    secrets_env = Path(sensitive_dir) / ".env"
    if secrets_env.exists():
        load_dotenv(secrets_env, override=True)
        logger.info(f"Loaded secrets from {secrets_env}")
    else:
        logger.warning(
            f"Secrets .env not found at {secrets_env}. "
            f"Copy secrets/.env.example → {secrets_env} and fill in values."
        )

    # Step 3: Load config.json (non-sensitive, lower priority than env vars)
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key, value in config.items():
            env_key = key.upper()
            if env_key not in os.environ:
                os.environ[env_key] = str(value)
        logger.info(f"Loaded config from {config_file}")
    else:
        logger.warning(
            f"Config file not found at {config_file}. "
            f"Copy config/config.json.example → {config_file} and adjust."
        )


# Run once on module import
_load_config()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,  # Already loaded manually above
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths (loaded from root .env or system env)
    sensitive_dir: str = "./secrets"
    config_path: str = "./config/config.json"

    # Secrets (loaded from sensitive_dir/.env)
    bot_token: str = ""
    google_sheets_spreadsheet_key: str = ""
    polls_spreadsheet_key: str = ""
    spreadsheet_url: str = ""

    # Group settings
    group_chat_id: int = 0
    polls_message_thread_id: Optional[int] = None
    admins: str = ""

    # Config (loaded from config.json or sensitive_dir/.env)
    debt_threshold: float = -20.0
    reminder_day_of_week: int = 0
    reminder_hour: int = 19
    reminder_minute: int = 0
    timezone: str = "Europe/Moscow"
    google_sheets_debts_range: str = "J2:K15"

    @property
    def credentials_path(self) -> str:
        return str(Path(self.sensitive_dir) / "credentials.json")

    @property
    def members_path(self) -> str:
        return str(Path(self.sensitive_dir) / "members.json")

    def is_admin(self, identifier: str | int) -> bool:
        if not self.admins:
            return False
        allowed = {a.strip() for a in self.admins.split(",")}
        return str(identifier) in allowed


settings = Settings()
