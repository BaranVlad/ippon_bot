import logging
from datetime import date

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.services.poll_service import create_training_poll, remind_non_voters
from bot.services.training_config import load_trainings, get_next_training_date

logger = logging.getLogger(__name__)

CHECK_HOUR = 10
CHECK_MINUTE = 0


def _date_str(d: date) -> str:
    return d.strftime("%d.%m")


async def _check_trainings(bot: Bot) -> None:
    """Daily check: create polls and send reminders for upcoming trainings."""
    trainings = load_trainings()
    today = date.today()
    
    for training in trainings:
        next_date = get_next_training_date(training["day_of_week"], today)
        days_until = (next_date - today).days
        date_str = _date_str(next_date)
        
        # Create poll if needed
        if days_until == training["poll_create_days_before"]:
            logger.info(f"Creating poll for training on {date_str}")
            await create_training_poll(bot, training, next_date)
        
        # Remind non-voters if needed
        if days_until == training["reminder_days_before"]:
            logger.info(f"Reminding non-voters for training on {date_str}")
            await remind_non_voters(bot, date_str)


def setup_training_scheduler(bot: Bot, scheduler: AsyncIOScheduler) -> None:
    """Add daily training checks to an existing scheduler."""
    scheduler.add_job(
        _check_trainings,
        trigger=CronTrigger(hour=CHECK_HOUR, minute=CHECK_MINUTE),
        args=[bot],
        id="daily_training_check",
        name="Daily training poll and reminder check",
        replace_existing=True,
    )
    logger.info(f"Training scheduler added: daily check at {CHECK_HOUR:02d}:{CHECK_MINUTE:02d}")
