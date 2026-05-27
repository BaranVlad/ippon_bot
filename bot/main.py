import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChatAdministrators

from bot.config import settings
from bot.handlers import common, admin, callbacks, polls
from bot.middlewares.membership import MembershipMiddleware
from bot.schedulers.debt_scheduler import setup_scheduler
from bot.schedulers.training_scheduler import setup_training_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def setup_bot_commands(bot: Bot) -> None:
    """Set up bot command menu hints for users and admins."""
    common_commands = [
        BotCommand(command="start", description="Приветствие"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="status", description="Показать свой баланс"),
    ]
    
    # Common commands for everyone
    await bot.set_my_commands(common_commands, scope=BotCommandScopeDefault())
    
    # Admin commands in the group chat
    if settings.group_chat_id:
        admin_commands = common_commands + [
            BotCommand(command="payment", description="Реквизиты для оплаты"),
            BotCommand(command="links", description="Полезные ссылки"),
            BotCommand(command="remind_debts", description="Напомнить о долгах"),
            BotCommand(command="remind_training", description="Напомнить не проголосовавшим"),
            BotCommand(command="new_training", description="Создать опрос для тренировки"),
        ]
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChatAdministrators(chat_id=settings.group_chat_id),
            )
            logger.info("Admin commands registered for group admins")
        except Exception as e:
            logger.warning(f"Could not set admin commands: {e}")


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    
    # Member filter: only known users can use commands
    common.router.message.middleware(MembershipMiddleware())
    common.router.callback_query.middleware(MembershipMiddleware())
    
    # Polls are open to everyone in the group
    dp.include_router(polls.router)
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(callbacks.router)
    return dp


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = create_dispatcher()
    
    logger.info("Starting bot...")
    
    # Setup command hints
    await setup_bot_commands(bot)
    
    # Start scheduler
    scheduler = setup_scheduler(bot)
    setup_training_scheduler(bot, scheduler)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
