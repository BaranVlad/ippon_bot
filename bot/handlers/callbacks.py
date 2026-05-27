import logging
from datetime import date, datetime

from aiogram import Router, types, Bot
from aiogram.filters.callback_data import CallbackData

from bot.integrations.gsheets.polls import get_active_polls, get_all_poll_dates
from bot.services.poll_manager import create_training_poll, send_poll_reminders

logger = logging.getLogger(__name__)
router = Router()


class CreatePollCallback(CallbackData, prefix="create_poll", sep="|"):
    date_str: str
    time: str
    location: str


class RemindPollCallback(CallbackData, prefix="remind_poll", sep="|"):
    poll_id: str


@router.callback_query(RemindPollCallback.filter())
async def on_remind_poll(
    callback: types.CallbackQuery,
    callback_data: RemindPollCallback,
    bot: Bot,
) -> None:
    # Answer immediately to avoid timeout
    await callback.answer("⏳ Отправляю напоминания...")

    # Find poll by id
    polls = get_active_polls()
    poll = None
    for p in polls:
        if p.poll_id == callback_data.poll_id:
            poll = p
            break

    if not poll:
        await callback.answer("Опрос не найден!", show_alert=True)
        return

    try:
        await send_poll_reminders(bot, poll)
        await callback.message.edit_text(
            f"✅ Напоминания отправлены для тренировки {poll.date} {poll.time}!"
        )
    except Exception as e:
        logger.exception(f"Failed to send poll reminders: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(CreatePollCallback.filter())
async def on_create_poll(
    callback: types.CallbackQuery,
    callback_data: CreatePollCallback,
    bot: Bot,
) -> None:
    date_str = callback_data.date_str
    time = callback_data.time
    location = callback_data.location

    # Parse date and resolve correct year
    try:
        day, month = map(int, date_str.split("."))
        year = datetime.now().year
        training_date = datetime(year, month, day).date()
        # If the date has already passed this year, assume next year
        if training_date < date.today():
            year += 1
            training_date = datetime(year, month, day).date()
    except ValueError:
        await callback.answer("Ошибка в формате даты", show_alert=True)
        return

    # Check again if poll exists
    if date_str in get_all_poll_dates():
        await callback.answer("Опрос для этой тренировки уже создан!", show_alert=True)
        return

    # Answer callback immediately to avoid timeout
    await callback.answer("⏳ Создаю опрос...")

    try:
        await create_training_poll(bot, time, location, training_date)
        await callback.message.edit_text(
            f"✅ Опрос для тренировки {date_str} {time}, {location} создан."
        )
    except Exception as e:
        logger.exception(f"Failed to create poll via callback: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
