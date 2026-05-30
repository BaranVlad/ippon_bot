import asyncio
import logging
from typing import List, Optional

from bot.integrations.gsheets.client import get_polls_sheet
from bot.models import PollRecord

logger = logging.getLogger(__name__)


def _get_all_poll_dates_sync() -> set[str]:
    sheet = get_polls_sheet()
    values = sheet.get_all_values()
    if len(values) < 2:
        return set()

    headers = values[0]
    date_idx = headers.index("date") if "date" in headers else 2
    return {row[date_idx].strip() for row in values[1:] if len(row) > date_idx}


async def get_all_poll_dates() -> set[str]:
    return await asyncio.to_thread(_get_all_poll_dates_sync)


def _get_poll_by_date_sync(training_date: str) -> Optional[PollRecord]:
    sheet = get_polls_sheet()
    values = sheet.get_all_values()
    if len(values) < 2:
        return None

    headers = values[0]
    for row in values[1:]:
        record = dict(zip(headers, row))
        if str(record.get("date", "")).strip() == training_date:
            return _row_to_poll_record(record)

    return None


async def get_poll_by_date(training_date: str) -> Optional[PollRecord]:
    return await asyncio.to_thread(_get_poll_by_date_sync, training_date)


def _save_poll_sync(
    poll_id: str,
    message_id: int,
    date: str,
    time: str,
    location: str,
    thread_id: Optional[int],
    status: str = "active",
) -> None:
    sheet = get_polls_sheet()
    sheet.append_row([
        poll_id,
        str(message_id),
        date,
        time,
        location,
        str(thread_id) if thread_id else "",
        status,
    ])
    logger.info(f"Saved poll {poll_id} for {date} {time}")


async def save_poll(
    poll_id: str,
    message_id: int,
    date: str,
    time: str,
    location: str,
    thread_id: Optional[int],
    status: str = "active",
) -> None:
    return await asyncio.to_thread(
        _save_poll_sync, poll_id, message_id, date, time, location, thread_id, status
    )


def _get_active_polls_sync() -> List[PollRecord]:
    sheet = get_polls_sheet()
    values = sheet.get_all_values()

    if len(values) < 2:
        return []

    headers = values[0]
    active = []
    for row in values[1:]:
        record = dict(zip(headers, row))
        if str(record.get("status", "")).strip().lower() == "active":
            active.append(_row_to_poll_record(record))

    return active


async def get_active_polls() -> List[PollRecord]:
    return await asyncio.to_thread(_get_active_polls_sync)


def _row_to_poll_record(record: dict) -> PollRecord:
    """Convert a raw dict row to PollRecord."""
    return PollRecord(
        poll_id=record.get("poll_id", ""),
        message_id=int(record["message_id"]) if record.get("message_id") else 0,
        date=record.get("date", ""),
        time=record.get("time", ""),
        location=record.get("location", ""),
        thread_id=int(record["thread_id"]) if record.get("thread_id") else None,
        status=record.get("status", "active"),
    )
