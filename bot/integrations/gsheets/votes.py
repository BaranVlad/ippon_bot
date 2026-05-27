import logging
from datetime import datetime
from typing import Dict

from bot.integrations.gsheets.client import get_votes_sheet

logger = logging.getLogger(__name__)


def save_vote(poll_id: str, name: str, vote: str) -> None:
    """Append or update a vote in the 'Голоса' sheet."""
    sheet = get_votes_sheet()
    values = sheet.get_all_values()

    if len(values) >= 2:
        headers = values[0]
        # Check if vote already exists for this poll + name
        for idx, row in enumerate(values[1:], start=2):
            record = dict(zip(headers, row))
            if (
                str(record.get("poll_id", "")).strip() == poll_id
                and str(record.get("name", "")).strip().lower() == name.lower()
            ):
                # Update existing vote
                sheet.update_cell(idx, 3, vote)
                sheet.update_cell(idx, 4, datetime.now().strftime("%Y-%m-%d %H:%M"))
                logger.info(f"Updated vote for {name} in poll {poll_id}: {vote}")
                return

    # Append new vote
    sheet.append_row([
        poll_id,
        name,
        vote,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
    ])
    logger.info(f"Saved vote for {name} in poll {poll_id}: {vote}")


def get_votes_by_poll(poll_id: str) -> Dict[str, str]:
    """Return a dict {name: vote} for a given poll."""
    sheet = get_votes_sheet()
    values = sheet.get_all_values()

    votes = {}
    if len(values) < 2:
        return votes

    headers = values[0]
    for row in values[1:]:
        record = dict(zip(headers, row))
        if str(record.get("poll_id", "")).strip() == poll_id:
            name = str(record.get("name", "")).strip()
            vote = str(record.get("vote", "")).strip()
            if name:
                votes[name] = vote

    return votes
