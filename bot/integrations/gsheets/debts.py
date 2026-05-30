import asyncio
import logging
from typing import List, Optional

from bot.config import settings
from bot.integrations.gsheets.client import get_debts_worksheet
from bot.models import Debtor

logger = logging.getLogger(__name__)


def _read_debts_range() -> List[List[str]]:
    """Read raw values from the configured range (default J2:K15)."""
    sheet = get_debts_worksheet()
    values = sheet.get_values(settings.google_sheets_debts_range)
    logger.debug(f"Read {len(values)} rows from range {settings.google_sheets_debts_range}")
    return values


def _get_debtors_sync() -> List[Debtor]:
    """Return members whose balance is below the threshold."""
    rows = _read_debts_range()
    debtors = []

    for row in rows:
        if len(row) < 2:
            continue

        name = str(row[0]).strip()
        if not name:
            continue

        try:
            balance = float(str(row[1]).replace(" ", "").replace(",", "."))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse balance for '{name}': '{row[1]}'")
            continue

        if balance < settings.debt_threshold:
            debtors.append(Debtor(name=name, balance=balance))

    logger.info(f"Found {len(debtors)} debtors out of {len(rows)} rows")
    return debtors


async def get_debtors() -> List[Debtor]:
    """Async wrapper for _get_debtors_sync to avoid blocking the event loop."""
    return await asyncio.to_thread(_get_debtors_sync)


def _get_member_balance_sync(name: str) -> Optional[float]:
    """Get balance for a specific member by name."""
    rows = _read_debts_range()

    for row in rows:
        if len(row) < 2:
            continue
        row_name = str(row[0]).strip()
        if row_name.lower() == name.lower():
            try:
                return float(str(row[1]).replace(" ", "").replace(",", "."))
            except (ValueError, TypeError):
                return None

    return None


async def get_member_balance(name: str) -> Optional[float]:
    """Async wrapper for _get_member_balance_sync."""
    return await asyncio.to_thread(_get_member_balance_sync, name)
