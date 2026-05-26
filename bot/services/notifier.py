import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from bot.config import settings
from bot.data import load_members
from bot.services.google_sheets import get_debtors
from bot.services.template import render_template

logger = logging.getLogger(__name__)


def _spreadsheet_link() -> str:
    """Return a clickable HTML link to the spreadsheet."""
    if settings.spreadsheet_url:
        return f'<a href="{settings.spreadsheet_url}">📊 Подробный расчет в таблице</a>'
    return ""


async def send_debt_reminders(bot: Bot) -> None:
    """Send DM to known users, group message for the rest."""
    debtors = get_debtors()

    if not debtors:
        logger.info("No debtors found, skipping reminders")
        return

    members = load_members()
    dm_sent = 0
    group_debtors = []

    spreadsheet_link = _spreadsheet_link()

    for debtor in debtors:
        name = debtor["name"]
        balance = debtor["balance"]
        user_id = members.get(name)

        if user_id:
            try:
                text = render_template(
                    "debt_dm",
                    name=name,
                    balance=f"{balance:.2f}",
                    spreadsheet_link=spreadsheet_link,
                )
                await bot.send_message(chat_id=user_id, text=text)
                dm_sent += 1
                continue
            except TelegramForbiddenError:
                logger.info(f"Cannot DM {name} (user_id={user_id}), will mention in group")
            except Exception as e:
                logger.warning(f"Failed to DM {name}: {e}")

        group_debtors.append(debtor)

    if group_debtors:
        debtor_lines = [
            f"{i}. {d['name']}: {d['balance']:.2f} BYN"
            for i, d in enumerate(group_debtors, 1)
        ]

        dm_info = f"✅ {dm_sent} человек получили личное сообщение." if dm_sent else ""

        text = render_template(
            "debt_group",
            debtors="\n".join(debtor_lines),
            dm_info=dm_info,
            spreadsheet_link=spreadsheet_link,
        )

        try:
            await bot.send_message(
                chat_id=settings.group_chat_id,
                text=text,
            )
            logger.info(
                f"Group reminder sent: {len(group_debtors)} in group, {dm_sent} in DM"
            )
        except Exception as e:
            logger.exception(f"Failed to send group reminder: {e}")
    else:
        logger.info(f"All {dm_sent} debtors received DM, no group message needed")
