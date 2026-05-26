import logging

from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

from bot.config import settings
from bot.data import load_members
from bot.services.google_sheets import get_member_balance, get_all_poll_dates
from bot.services.notifier import send_debt_reminders
from bot.services.payment import get_payment_methods, get_payment_contact
from bot.services.poll_service import create_training_poll, send_poll_reminders
from bot.services.training_config import generate_upcoming_trainings
from bot.services import google_sheets as sheets

logger = logging.getLogger(__name__)
router = Router()


class CreatePollCallback(CallbackData, prefix="create_poll", sep="|"):
    date_str: str
    time: str
    location: str


class RemindPollCallback(CallbackData, prefix="remind_poll", sep="|"):
    poll_id: str


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    user = message.from_user
    name = user.first_name if user else "друг"
    
    await message.answer(
        f"Привет, {name}! 👋\n\n"
        f"Я бот команды Иппон. Напиши /help для списка команд."
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    user = message.from_user
    is_admin_user = user is not None and settings.is_admin(user.id)
    
    text = (
        "📋 Команды:\n\n"
        "/start — Приветствие\n"
        "/help — Показать это сообщение\n"
        "/status — Показать свой текущий баланс\n"
        "/payment — Реквизиты для оплаты\n"
        "/links — Полезные ссылки\n"
    )
    
    if is_admin_user:
        text += (
            "\n👑 Администраторские команды:\n"
            "/remind_debts — Отправить напоминание о долгах\n"
            "/remind_training — Напомнить не проголосовавшим\n"
            "/new_training — Создать опрос для тренировки\n"
        )
    
    text += "\nНапоминания о долгах приходят каждое воскресенье в 19:00."
    await message.answer(text)


@router.message(Command("status"))
async def cmd_status(message: types.Message) -> None:
    user = message.from_user
    if not user:
        return
    
    members = load_members()
    
    # Find member name by user_id
    name = None
    for member_name, member_id in members.items():
        if member_id == user.id:
            name = member_name
            break
    
    if not name:
        await message.answer(
            "Я не нашёл тебя в списке команды. "
            "Попроси капитана добавить тебя в data/members.json."
        )
        return
    
    balance = get_member_balance(name)
    if balance is None:
        await message.answer("Не удалось получить баланс из таблицы. Попробуй позже.")
        return
    
    if balance < settings.debt_threshold:
        text = (
            f"{name}, твой баланс: {balance:.2f} BYN\n\n"
            f"⚠️ У тебя есть долг. Пожалуйста, погаси его как можно скорее."
        )
    elif balance < 0:
        text = (
            f"{name}, твой баланс: {balance:.2f} BYN\n\n"
            f"💡 Небольшой минус, но пока в пределах нормы."
        )
    else:
        text = (
            f"{name}, твой баланс: {balance:.2f} BYN\n\n"
            f"✅ Всё в порядке, долгов нет!"
        )
    
    await message.answer(text)


@router.message(Command("payment"))
async def cmd_payment(message: types.Message) -> None:
    methods = get_payment_methods()
    contact_id, contact_name = get_payment_contact()
    
    if not methods:
        await message.answer(
            "💳 Реквизиты пока не настроены. "
            "Обратитесь к капитану команды."
        )
        return
    
    lines = ["💳 Способы оплаты:"]
    for i, method in enumerate(methods, 1):
        lines.append(f"\n{i}. {method['name']}")
        lines.append(f"{method['details']}")
    
    if contact_id:
        lines.append(
            f"\n📌 По вопросам оплаты обращайтесь к "
            f'<a href="tg://user?id={contact_id}">{contact_name}</a>'
        )
    else:
        lines.append(f"\n📌 По вопросам оплаты обращайтесь к {contact_name}")
    
    await message.answer("\n".join(lines))


@router.message(Command("links"))
async def cmd_links(message: types.Message) -> None:
    text = "📚 Полезные ссылки:\n\n"
    
    if settings.spreadsheet_url:
        text += f'📊 <a href="{settings.spreadsheet_url}">Таблица с расчётами и балансом</a>\n'
    else:
        text += "📊 Таблица с расчётами пока не настроена\n"
    
    await message.answer(text)


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
    
    polls = sheets.get_active_polls()
    if not polls:
        await message.answer("Нет активных опросов.")
        return
    
    buttons = []
    for poll in polls:
        label = f"Тренировка {poll['date']} {poll['time']}, {poll['location']}"
        callback = RemindPollCallback(poll_id=poll["poll_id"])
        buttons.append([InlineKeyboardButton(text=label, callback_data=callback.pack())])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "Выберите опрос для напоминания:",
        reply_markup=keyboard,
    )


@router.callback_query(RemindPollCallback.filter())
async def on_remind_poll(
    callback: types.CallbackQuery,
    callback_data: RemindPollCallback,
    bot: Bot,
) -> None:
    # Answer immediately to avoid timeout
    await callback.answer("⏳ Отправляю напоминания...")
    
    # Find poll by id
    polls = sheets.get_active_polls()
    poll = None
    for p in polls:
        if p["poll_id"] == callback_data.poll_id:
            poll = p
            break
    
    if not poll:
        await callback.answer("Опрос не найден!", show_alert=True)
        return
    
    try:
        await send_poll_reminders(bot, poll)
        await callback.message.edit_text(
            f"✅ Напоминания отправлены для тренировки {poll['date']} {poll['time']}!"
        )
    except Exception as e:
        logger.exception(f"Failed to send poll reminders: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.message(Command("new_training"))
async def cmd_new_training(message: types.Message) -> None:
    user = message.from_user
    if not user or not settings.is_admin(user.id):
        await message.answer("⛔ Эта команда только для администраторов.")
        return
    
    upcoming = generate_upcoming_trainings(days=14)
    
    if not upcoming:
        await message.answer("Нет предстоящих тренировок в расписании.")
        return
    
    # Filter out already created polls (single API call)
    existing_dates = get_all_poll_dates()
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


@router.callback_query(CreatePollCallback.filter())
async def on_create_poll(
    callback: types.CallbackQuery,
    callback_data: CreatePollCallback,
    bot: Bot,
) -> None:
    from datetime import datetime
    
    date_str = callback_data.date_str
    time = callback_data.time
    location = callback_data.location
    
    # Parse date
    try:
        day, month = map(int, date_str.split("."))
        year = datetime.now().year
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
    
    training = {
        "time": time,
        "location": location,
    }
    
    try:
        await create_training_poll(bot, training, training_date)
        await callback.message.edit_text(
            f"✅ Опрос для тренировки {date_str} {time}, {location} создан."
        )
    except Exception as e:
        logger.exception(f"Failed to create poll via callback: {e}")
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)
