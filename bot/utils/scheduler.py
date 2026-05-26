import logging
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.services.notifier import send_debt_reminders

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.timezone)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configure and start APScheduler with weekly debt reminders."""
    
    # Weekly debt reminders: Sunday at 19:00
    scheduler.add_job(
        send_debt_reminders,
        trigger=CronTrigger(
            day_of_week=settings.reminder_day_of_week,
            hour=settings.reminder_hour,
            minute=settings.reminder_minute,
        ),
        args=[bot],
        id="weekly_debt_reminder",
        name="Weekly debt reminders",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info(
        f"Scheduler started. Debt reminders set for "
        f"day_of_week={settings.reminder_day_of_week} "
        f"({settings.reminder_hour:02d}:{settings.reminder_minute:02d})"
    )
    
    return scheduler
