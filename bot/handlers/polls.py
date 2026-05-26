import logging

from aiogram import Router, types
from aiogram.types import PollAnswer

from bot.data import load_members
from bot.services import google_sheets as sheets

logger = logging.getLogger(__name__)
router = Router()

VOTE_MAP = ["Буду", "Не буду", "Не знаю"]


@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer) -> None:
    """Handle vote (or vote retraction) in a training poll."""
    poll_id = poll_answer.poll_id
    user = poll_answer.user
    option_ids = poll_answer.option_ids
    
    # Find member name by user_id
    members = load_members()
    name = None
    for member_name, member_id in members.items():
        if member_id == user.id:
            name = member_name
            break
    
    if not name:
        logger.warning(f"Unknown user voted: id={user.id}, poll={poll_id}")
        name = user.first_name or str(user.id)
    
    if not option_ids:
        # User retracted their vote
        sheets.save_vote(poll_id, name, "Отменил")
        logger.info(f"Vote retracted: {name} (poll={poll_id})")
        return
    
    vote = VOTE_MAP[option_ids[0]] if option_ids[0] < len(VOTE_MAP) else "Не знаю"
    
    sheets.save_vote(poll_id, name, vote)
    logger.info(f"Vote recorded: {name} -> {vote} (poll={poll_id})")
