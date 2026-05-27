import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Any

from bot.models import Training

logger = logging.getLogger(__name__)

TRAININGS_PATH = Path(__file__).parent.parent.parent / "resources" / "data" / "trainings.json"

WEEKDAY_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def load_trainings() -> List[Training]:
    """Load training schedule from resources/data/trainings.json."""
    if not TRAININGS_PATH.exists():
        logger.warning(f"trainings.json not found at {TRAININGS_PATH}")
        return []

    with open(TRAININGS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    trainings = [Training.model_validate(t) for t in data if t.get("enabled", True)]
    logger.info(f"Loaded {len(trainings)} enabled training schedules")
    return trainings


def get_next_training_date(day_of_week: int, from_date: date | None = None) -> date:
    """Get the next occurrence of a given weekday."""
    if from_date is None:
        from_date = date.today()

    days_ahead = day_of_week - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7

    return from_date + timedelta(days=days_ahead)


def generate_upcoming_trainings(days: int = 14, from_date: date | None = None) -> List[Dict[str, Any]]:
    """Generate list of upcoming trainings with dates for the next N days."""
    if from_date is None:
        from_date = date.today()

    trainings = load_trainings()
    result = []

    for training in trainings:
        current = from_date
        end = from_date + timedelta(days=days)

        while current <= end:
            next_date = get_next_training_date(training.day_of_week, current)
            if next_date > end:
                break

            result.append({
                "date": next_date,
                "date_str": next_date.strftime("%d.%m"),
                "weekday_short": WEEKDAY_SHORT[next_date.weekday()],
                "time": training.time,
                "location": training.location,
                "day_of_week": training.day_of_week,
            })

            current = next_date + timedelta(days=1)

    # Sort by date
    result.sort(key=lambda x: x["date"])
    return result
