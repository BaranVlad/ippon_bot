import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

import gspread
from gspread import Worksheet
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from bot.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def _check_credentials() -> None:
    """Raise a clear error if credentials file is missing."""
    if not os.path.exists(settings.credentials_path):
        raise RuntimeError(
            f"Google Sheets API недоступен: не найден {settings.credentials_path}\n"
            f"Скопируйте credentials.json из Google Cloud Console в {settings.credentials_path}"
        )


def _get_client() -> gspread.Client:
    _check_credentials()
    creds = Credentials.from_service_account_file(
        settings.credentials_path,
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def _get_spreadsheet(key: str) -> gspread.Spreadsheet:
    client = _get_client()
    return client.open_by_key(key)


def _get_or_create_worksheet(spreadsheet: gspread.Spreadsheet, title: str, rows: int = 100, cols: int = 20) -> Worksheet:
    """Get worksheet by title or create it if not exists."""
    try:
        return spreadsheet.worksheet(title)
    except WorksheetNotFound:
        logger.info(f"Creating worksheet '{title}'")
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


# ============================================================
# Debts (main spreadsheet)
# ============================================================

def _get_debts_worksheet() -> Worksheet:
    spreadsheet = _get_spreadsheet(settings.google_sheets_spreadsheet_key)
    try:
        return spreadsheet.get_worksheet(0)
    except Exception as e:
        available = [ws.title for ws in spreadsheet.worksheets()]
        raise WorksheetNotFound(
            f"Could not open worksheet. Available sheets: {available}. Error: {e}"
        )


def _read_debts_range() -> List[List[str]]:
    """Read raw values from the configured range (default J2:K15)."""
    sheet = _get_debts_worksheet()
    values = sheet.get_values(settings.google_sheets_debts_range)
    logger.debug(f"Read {len(values)} rows from range {settings.google_sheets_debts_range}")
    return values


def get_debtors() -> List[Dict[str, float]]:
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
            debtors.append({"name": name, "balance": balance})
    
    logger.info(f"Found {len(debtors)} debtors out of {len(rows)} rows")
    return debtors


def get_member_balance(name: str) -> Optional[float]:
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


# ============================================================
# Polls & Votes (separate spreadsheet)
# ============================================================

POLL_HEADERS = ["poll_id", "message_id", "date", "time", "location", "thread_id", "status"]
VOTE_HEADERS = ["poll_id", "name", "vote", "voted_at"]

# Simple module-level cache to avoid repeated API calls
_polls_sheet_cache: Worksheet | None = None
_votes_sheet_cache: Worksheet | None = None


def _get_polls_spreadsheet() -> gspread.Spreadsheet:
    key = settings.polls_spreadsheet_key or settings.google_sheets_spreadsheet_key
    return _get_spreadsheet(key)


def _init_polls_sheet() -> Worksheet:
    global _polls_sheet_cache
    if _polls_sheet_cache is not None:
        return _polls_sheet_cache
    
    spreadsheet = _get_polls_spreadsheet()
    sheet = _get_or_create_worksheet(spreadsheet, "Опросы")
    values = sheet.get_all_values()
    if not values or values == [[]]:
        sheet.append_row(POLL_HEADERS)
    
    _polls_sheet_cache = sheet
    return sheet


def _init_votes_sheet() -> Worksheet:
    global _votes_sheet_cache
    if _votes_sheet_cache is not None:
        return _votes_sheet_cache
    
    spreadsheet = _get_polls_spreadsheet()
    sheet = _get_or_create_worksheet(spreadsheet, "Голоса")
    values = sheet.get_all_values()
    if not values or values == [[]]:
        sheet.append_row(VOTE_HEADERS)
    
    _votes_sheet_cache = sheet
    return sheet


def get_all_poll_dates() -> set[str]:
    """Return a set of all training dates that already have a poll."""
    sheet = _init_polls_sheet()
    values = sheet.get_all_values()
    if len(values) < 2:
        return set()
    
    headers = values[0]
    date_idx = headers.index("date") if "date" in headers else 2
    return {row[date_idx].strip() for row in values[1:] if len(row) > date_idx}


def get_poll_by_date(training_date: str) -> Optional[Dict[str, str]]:
    """Check if a poll already exists for a given training date."""
    sheet = _init_polls_sheet()
    values = sheet.get_all_values()
    if len(values) < 2:
        return None
    
    headers = values[0]
    for row in values[1:]:
        record = dict(zip(headers, row))
        if str(record.get("date", "")).strip() == training_date:
            return record
    
    return None


def save_poll(
    poll_id: str,
    message_id: int,
    date: str,
    time: str,
    location: str,
    thread_id: Optional[int],
    status: str = "active",
) -> None:
    """Append a new poll record to the 'Опросы' sheet."""
    sheet = _init_polls_sheet()
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


def save_vote(poll_id: str, name: str, vote: str) -> None:
    """Append or update a vote in the 'Голоса' sheet."""
    sheet = _init_votes_sheet()
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
    sheet = _init_votes_sheet()
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


def get_active_polls() -> List[Dict[str, str]]:
    """Return all polls with status='active'."""
    sheet = _init_polls_sheet()
    values = sheet.get_all_values()
    
    if len(values) < 2:
        return []
    
    headers = values[0]
    active = []
    for row in values[1:]:
        record = dict(zip(headers, row))
        if str(record.get("status", "")).strip().lower() == "active":
            active.append(record)
    
    return active
