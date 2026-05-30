import logging

from aiogram import Router, types
from aiogram.types import PollAnswer

from bot.constants import POLL_OPTIONS
from bot.data_loaders.members import get_member_name_by_id
from bot.integrations.gsheets.votes import save_vote

logger = logging.getLogger(__name__)
router = Router()


@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer) -> None:
    """Handle vote (or vote retraction) in a training poll."""
    poll_id = poll_answer.poll_id
    user = poll_answer.user
    option_ids = poll_answer.option_ids

    name = get_member_name_by_id(user.id)
    if not name:
        logger.warning(f"Unknown user voted: id={user.id}, poll={poll_id}")
        name = user.first_name or str(user.id)

    if not option_ids:
        # User retracted their vote
        await save_vote(poll_id, name, "Отменил")
        logger.info(f"Vote retracted: {name} (poll={poll_id})")
        return

    vote = POLL_OPTIONS[option_ids[0]] if option_ids[0] < len(POLL_OPTIONS) else "Не знаю"

    await save_vote(poll_id, name, vote)
    logger.info(f"Vote recorded: {name} -> {vote} (poll={poll_id})")
