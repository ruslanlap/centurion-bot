import contextlib

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.services.feedback_service import FeedbackService

router = Router(name="feedback")


@router.message(Command("feedback"))
async def cmd_feedback(message: Message, bot: Bot, session: AsyncSession) -> None:
    from centurion_bot.config import settings

    user = message.from_user
    if not user:
        return

    text = (message.text or "")[len("/feedback"):].strip()
    if not text:
        await message.answer(texts.MISSING_TEXT.format(name=user.first_name), parse_mode="HTML")
        return

    svc = FeedbackService(session)
    await svc.add(user.id, text)
    await message.answer(texts.FEEDBACK_THANKS, parse_mode="HTML")

    if settings.admin_id:
        with contextlib.suppress(Exception):
            await bot.send_message(settings.admin_id, texts.FEEDBACK_NEW)
