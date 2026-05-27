import logging

from aiogram import Router, types
from aiogram.filters import Command

from bot.config import settings
from bot.data_loaders.members import get_member_name_by_id
from bot.data_loaders.payment import get_payment_methods, get_payment_contact
from bot.integrations.gsheets.debts import get_member_balance
from bot.services.feature_request import create_feature_issue

logger = logging.getLogger(__name__)
router = Router()


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

    name = get_member_name_by_id(user.id)
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
        lines.append(f"\n{i}. {method.name}")
        lines.append(f"{method.details}")

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


@router.message(Command("feature"))
async def cmd_feature(message: types.Message) -> None:
    user = message.from_user
    if not user:
        return

    # Extract text after command (handle both /feature and /feature@bot_name)
    text = message.text or ""
    command_prefix = "/feature"
    if user.username and f"@{user.username}" in text:
        text = text.split("@")[0] + text.split("@", 1)[1].split(" ", 1)[1] if " " in text else ""
    text = text.replace(command_prefix, "", 1).strip()

    if not text:
        await message.answer(
            "📝 Опиши фичу после команды.\n"
            "Пример: <code>/feature Добавить напоминания о сборах</code>"
        )
        return

    try:
        issue_url = await create_feature_issue(text)
        await message.answer(f"✅ Запрос на фичу создан:\n{issue_url}")
    except RuntimeError as e:
        logger.warning(f"Feature request failed for user {user.id}: {e}")
        await message.answer("⚙️ Функция предложения фичей пока не настроена.")
    except Exception as e:
        logger.exception(f"Failed to create feature issue for user {user.id}: {e}")
        await message.answer("❌ Не удалось создать запрос. Попробуй позже.")
