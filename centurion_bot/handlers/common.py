from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.services.user_service import UserService

router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    svc = UserService(session)
    user = message.from_user
    if user:
        await svc.upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")
    await message.answer(texts.HELP, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP, parse_mode="HTML")
