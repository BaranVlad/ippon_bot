import logging
import os
from typing import Optional

import gspread
from gspread import Worksheet
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from bot.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

_client_cache: Optional[gspread.Client] = None


def _check_credentials() -> None:
    """Raise a clear error if credentials file is missing."""
    if not os.path.exists(settings.credentials_path):
        raise RuntimeError(
            f"Google Sheets API недоступен: не найден {settings.credentials_path}\n"
            f"Скопируйте credentials.json из Google Cloud Console в {settings.credentials_path}"
        )


def get_client() -> gspread.Client:
    """Get cached gspread client."""
    global _client_cache
    if _client_cache is None:
        _check_credentials()
        creds = Credentials.from_service_account_file(
            settings.credentials_path,
            scopes=SCOPES,
        )
        _client_cache = gspread.authorize(creds)
    return _client_cache


def get_spreadsheet(key: str) -> gspread.Spreadsheet:
    """Open spreadsheet by key."""
    return get_client().open_by_key(key)


def get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    rows: int = 100,
    cols: int = 20,
) -> Worksheet:
    """Get worksheet by title or create it if not exists."""
    try:
        return spreadsheet.worksheet(title)
    except WorksheetNotFound:
        logger.info(f"Creating worksheet '{title}'")
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


# ============================================================
# Debts (main spreadsheet)
# ============================================================

def get_debts_worksheet() -> Worksheet:
    """Get the first worksheet of the main spreadsheet."""
    spreadsheet = get_spreadsheet(settings.google_sheets_spreadsheet_key)
    try:
        return spreadsheet.get_worksheet(0)
    except Exception as e:
        available = [ws.title for ws in spreadsheet.worksheets()]
        raise WorksheetNotFound(
            f"Could not open worksheet. Available sheets: {available}. Error: {e}"
        )


# ============================================================
# Polls & Votes (separate spreadsheet)
# ============================================================

POLL_HEADERS = ["poll_id", "message_id", "date", "time", "location", "thread_id", "status"]
VOTE_HEADERS = ["poll_id", "name", "vote", "voted_at"]

_polls_sheet_cache: Optional[Worksheet] = None
_votes_sheet_cache: Optional[Worksheet] = None


def _get_polls_spreadsheet() -> gspread.Spreadsheet:
    key = settings.polls_spreadsheet_key or settings.google_sheets_spreadsheet_key
    return get_spreadsheet(key)


def get_polls_sheet() -> Worksheet:
    """Get or create 'Опросы' worksheet (cached)."""
    global _polls_sheet_cache
    if _polls_sheet_cache is not None:
        return _polls_sheet_cache

    spreadsheet = _get_polls_spreadsheet()
    sheet = get_or_create_worksheet(spreadsheet, "Опросы")
    values = sheet.get_all_values()
    if not values or values == [[]]:
        sheet.append_row(POLL_HEADERS)

    _polls_sheet_cache = sheet
    return sheet


def get_votes_sheet() -> Worksheet:
    """Get or create 'Голоса' worksheet (cached)."""
    global _votes_sheet_cache
    if _votes_sheet_cache is not None:
        return _votes_sheet_cache

    spreadsheet = _get_polls_spreadsheet()
    sheet = get_or_create_worksheet(spreadsheet, "Голоса")
    values = sheet.get_all_values()
    if not values or values == [[]]:
        sheet.append_row(VOTE_HEADERS)

    _votes_sheet_cache = sheet
    return sheet
