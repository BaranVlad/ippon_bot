import json
import logging
from pathlib import Path
from typing import Optional

from bot.config import settings
from bot.models import PaymentConfig, PaymentMethod

logger = logging.getLogger(__name__)

_payment_cache: Optional[PaymentConfig] = None


def load_payment_config() -> PaymentConfig:
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
        _payment_cache = PaymentConfig()
        return _payment_cache

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _payment_cache = PaymentConfig.model_validate(data)
    logger.info(f"Loaded payment config from {path}")
    return _payment_cache


def get_payment_methods() -> list[PaymentMethod]:
    """Return list of payment methods."""
    config = load_payment_config()
    return config.methods


def get_payment_contact() -> tuple[Optional[int], str]:
    """Return (user_id, name) of the person responsible for payments."""
    config = load_payment_config()
    return config.contact_user_id, config.contact_name
