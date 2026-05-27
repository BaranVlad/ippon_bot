import logging

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


async def create_feature_issue(title: str) -> str:
    """Create a GitHub issue with the given title and return its URL.

    Raises:
        RuntimeError: if GitHub integration is not configured or API call fails.
    """
    if not settings.github_token or not settings.github_repo:
        raise RuntimeError("GitHub integration is not configured")

    url = f"https://api.github.com/repos/{settings.github_repo}/issues"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {
        "title": title,
        "labels": ["feature request"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 422:
                # Label may not exist; retry without label
                logger.warning("GitHub label 'feature request' not found, creating issue without label")
                payload.pop("labels", None)
                async with session.post(url, headers=headers, json=payload) as resp2:
                    resp2.raise_for_status()
                    data = await resp2.json()
                    return str(data["html_url"])

            resp.raise_for_status()
            data = await resp.json()
            return str(data["html_url"])
