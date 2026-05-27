import logging
from datetime import date

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from bot.config import settings
from bot.constants import POLL_OPTIONS
from bot.data_loaders.members import load_members
from bot.data_loaders.trainings import WEEKDAY_SHORT
from bot.integrations.gsheets.polls import get_poll_by_date, save_poll
from bot.integrations.gsheets.votes import get_votes_by_poll
from bot.models import PollRecord

logger = logging.getLogger(__name__)


async def _get_username(bot: Bot, user_id: int) -> str | None:
    """Try to get user's @username. Falls back to first_name if no username."""
    try:
        chat = await bot.get_chat(user_id)
        if chat.username:
            return f"@{chat.username}"
        return chat.first_name or str(user_id)
    except Exception:
        logger.warning(f"Could not get chat info for user_id={user_id}")
        return None


async def create_training_poll(bot: Bot, time: str, location: str, training_date: date) -> None:
    """Create a native Telegram poll for a training session."""
    date_str = training_date.strftime("%d.%m")
    weekday = WEEKDAY_SHORT[training_date.weekday()]
    question = f"Тренировка {weekday} {date_str} {time}, {location}"

    # Check if poll already exists
    existing = get_poll_by_date(date_str)
    if existing:
        logger.info(f"Poll for {date_str} already exists (poll_id={existing.poll_id})")
        return

    logger.info(f"Creating poll: {question}")

    try:
        kwargs = {
            "chat_id": settings.group_chat_id,
            "question": question,
            "options": POLL_OPTIONS,
            "is_anonymous": False,
            "allows_multiple_answers": False,
        }
        if settings.polls_message_thread_id:
            kwargs["message_thread_id"] = settings.polls_message_thread_id

        msg = await bot.send_poll(**kwargs)

        save_poll(
            poll_id=msg.poll.id,
            message_id=msg.message_id,
            date=date_str,
            time=time,
            location=location,
            thread_id=settings.polls_message_thread_id,
            status="active",
        )

        logger.info(f"Poll created: poll_id={msg.poll.id}, message_id={msg.message_id}")

    except Exception as e:
        logger.exception(f"Failed to create poll for {date_str}: {e}")


async def remind_non_voters(bot: Bot, training_date: str) -> None:
    """Send a group reminder mentioning members who haven't voted yet."""
    poll = get_poll_by_date(training_date)
    if not poll:
        logger.warning(f"No poll found for {training_date}, skipping reminder")
        return

    await send_poll_reminders(bot, poll)


async def send_poll_reminders(bot: Bot, poll: PollRecord) -> None:
    """Send DM with forwarded poll to known users, group reply for the rest."""
    poll_id = poll.poll_id
    message_id = poll.message_id
    date_str = poll.date
    time = poll.time
    location = poll.location

    votes = get_votes_by_poll(poll_id)
    members = load_members()

    dm_sent = 0
    group_non_voters = []

    for name in members.keys():
        if name in votes and votes[name] != "Отменил":
            continue

        user_id = members.get(name)
        if user_id:
            try:
                # Forward poll to DM
                await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=settings.group_chat_id,
                    message_id=message_id,
                )
                # Send reminder text
                text = (
                    f"Привет! Не забудь проголосовать за тренировку "
                    f"{date_str} {time}, {location}!"
                )
                await bot.send_message(chat_id=user_id, text=text)
                dm_sent += 1
                continue
            except TelegramForbiddenError:
                logger.info(f"Cannot DM {name} (user_id={user_id})")
            except Exception as e:
                logger.warning(f"Failed to DM {name}: {e}")

        group_non_voters.append(name)

    if group_non_voters:
        mentions = []
        for name in group_non_voters:
            user_id = members.get(name)
            if user_id:
                try:
                    chat = await bot.get_chat(user_id)
                    if chat.username:
                        mentions.append(f"@{chat.username}")
                        continue
                except Exception:
                    pass
            mentions.append(name)

        text = (
            f"📢 Напоминание проголосовать за тренировку "
            f"{date_str} {time}, {location}!\n\n"
            f"Ещё не проголосовали: {', '.join(mentions)}\n\n"
            f"📝 Выберите свой вариант в опросе выше!"
        )

        kwargs = {
            "chat_id": settings.group_chat_id,
            "text": text,
            "reply_to_message_id": message_id,
        }
        # Poll reminders go to General (no thread_id)

        await bot.send_message(**kwargs)
        logger.info(
            f"Poll reminder: {dm_sent} DM, {len(group_non_voters)} group reply "
            f"for poll {poll_id}"
        )
    else:
        logger.info(f"All non-voters received DM for poll {poll_id}")
