import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from bot.config import settings

logger = logging.getLogger(__name__)

_payment_cache: Dict[str, Any] | None = None


def load_payment_config() -> Dict[str, Any]:
    """Load payment info from sensitive_dir/payment.json (cached)."""
    global _payment_cache
    if _payment_cache is not None:
        return _payment_cache

    path = Path(settings.sensitive_dir) / "payment.json"
    if not path.exists():
        logger.warning(
            f"payment.json не найден: {path}\n"
            f"Скопируйте secrets/payment.json.example → {path} и заполните"
        )
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _payment_cache = data
    logger.info(f"Loaded payment config from {path}")
    return data


def get_payment_methods() -> List[Dict[str, str]]:
    """Return list of payment methods."""
    config = load_payment_config()
    return config.get("methods", [])


def get_payment_contact() -> tuple[int | None, str]:
    """Return (user_id, name) of the person responsible for payments."""
    config = load_payment_config()
    user_id = config.get("contact_user_id")
    name = config.get("contact_name", "капитан")
    return (user_id, name)
