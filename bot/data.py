import json
import logging
from pathlib import Path
from typing import Dict

from bot.config import settings

logger = logging.getLogger(__name__)

_members_cache: Dict[str, int] | None = None


def load_members() -> Dict[str, int]:
    """Load name -> user_id mapping from members.json (cached)."""
    global _members_cache
    if _members_cache is not None:
        return _members_cache

    path = Path(settings.members_path)
    if not path.exists():
        logger.warning(
            f"members.json не найден: {path}\n"
            f"Скопируйте secrets/members.json.example → {path} и заполните"
        )
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    _members_cache = {str(k): int(v) for k, v in data.items()}
    logger.info(f"Loaded {len(_members_cache)} members from {path}")
    return _members_cache


def reload_members() -> Dict[str, int]:
    """Force reload members.json from disk."""
    global _members_cache
    _members_cache = None
    return load_members()


def is_member(user_id: int) -> bool:
    """Check if a user_id is present in members.json."""
    members = load_members()
    if not members:
        # If no members.json, allow everyone (disabled filter)
        return True
    return user_id in members.values()
