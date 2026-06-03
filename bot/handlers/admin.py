import logging

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import settings
from bot.data_loaders.members import get_all_member_ids, load_members
from bot.data_loaders.trainings import generate_upcoming_trainings
from bot.handlers.callbacks import CreatePollCallback, RemindPollCallback
from bot.integrations.gsheets.polls import get_active_polls, get_all_poll_dates
from bot.services.debt_notifier import send_debt_reminders
from bot.services.poll_manager import send_poll_reminders

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("remind_debts"))
async def cmd_remind_debts(message: types.Message, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    if not settings.is_admin(user.id):
        await message.answer("⛔ Эта команда только для администраторов.")
        return

    await message.answer("📤 Отправляю напоминание...")

    try:
        await send_debt_reminders(bot)
        await message.answer("✅ Напоминание отправлено в группу.")
    except Exception as e:
        logger.exception(f"Admin {user.id} failed to send reminder: {e}")
        await message.answer(f"❌ Ошибка при отправке: {e}")


@router.message(Command("remind_training"))
async def cmd_remind_training(message: types.Message) -> None:
    user = message.from_user
    if not user or not settings.is_admin(user.id):
        await message.answer("⛔ Эта команда только для администраторов.")
        return

    polls = await get_active_polls()
    if not polls:
        await message.answer("Нет активных опросов.")
        return

    buttons = []
    for poll in polls:
        label = f"Тренировка {poll.date} {poll.time}, {poll.location}"
        callback = RemindPollCallback(poll_id=poll.poll_id)
        buttons.append([InlineKeyboardButton(text=label, callback_data=callback.pack())])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "Выберите опрос для напоминания:",
        reply_markup=keyboard,
    )


@router.message(Command("new_training"))
async def cmd_new_training(message: types.Message) -> None:
    user = message.from_user
    if not user or not settings.is_admin(user.id):
        await message.answer("⛔ Эта команда только для администраторов.")
        return

    upcoming = generate_upcoming_trainings(days=14, only_enabled=False)

    if not upcoming:
        await message.answer("Нет предстоящих тренировок в расписании.")
        return

    existing_dates = await get_all_poll_dates()
    new_trainings = [t for t in upcoming if t["date_str"] not in existing_dates]

    if not new_trainings:
        await message.answer("Все ближайшие тренировки уже имеют опросы.")
        return

    buttons = []
    for t in new_trainings:
        label = f"Тренировка {t['weekday_short']} {t['date_str']} {t['time']}, {t['location']}"
        callback = CreatePollCallback(
            date_str=t["date_str"],
            time=t["time"],
            location=t["location"],
        )
        buttons.append([InlineKeyboardButton(text=label, callback_data=callback.pack())])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "Выберите тренировку для создания опроса:",
        reply_markup=keyboard,
    )


@router.message(Command("all"))
async def cmd_all(message: types.Message, bot: Bot) -> None:
    """Reply with mentions of all team members.

    If used as a reply to another message, the bot replies to that message.
    Any text after /all is preserved and appended after the mentions.
    """
    user = message.from_user
    if not user or not settings.is_admin(user.id):
        await message.answer("⛔ Эта команда только для администраторов.")
        return

    # Extract optional text after the command
    text = message.text or ""
    command_prefix = "/all"
    if user.username and f"@{user.username}" in text:
        text = text.split("@")[0] + text.split("@", 1)[1].split(" ", 1)[1] if " " in text else ""
    extra_text = text.replace(command_prefix, "", 1).strip()

    members = load_members()
    if not members:
        await message.answer("Список участников пуст.")
        return

    # Build mentions list
    mentions: list[str] = []
    for name, user_id in members.items():
        try:
            chat = await bot.get_chat(user_id)
            if chat.username:
                mentions.append(f"@{chat.username}")
            else:
                mentions.append(f'<a href="tg://user?id={user_id}">{name}</a>')
        except Exception:
            mentions.append(f'<a href="tg://user?id={user_id}">{name}</a>')

    # Determine reply target
    reply_to = message.message_id
    if message.reply_to_message:
        reply_to = message.reply_to_message.message_id

    # Telegram has an implicit limit on mentions per message; stay safe with chunks of 50
    chunk_size = 50
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        chunk_text = " ".join(chunk)
        if extra_text and i == 0:
            chunk_text = f"{chunk_text}\n\n{extra_text}"

        try:
            await bot.send_message(
                chat_id=message.chat.id,
                text=chunk_text,
                reply_to_message_id=reply_to,
            )
        except Exception as e:
            logger.exception(f"Failed to send /all mention chunk: {e}")
            await message.answer(f"❌ Ошибка при отправке упоминаний: {e}")
