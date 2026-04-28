import contextlib

import structlog
from aiogram import Bot, F, Router
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.services.task_service import TaskService
from centurion_bot.services.user_service import UserService

router = Router(name="user")
log = structlog.get_logger()


async def _auto_register_members(bot: Bot, chat_id: int, session: AsyncSession) -> int:
    """Try to register all admins/members we can discover via the API.

    Telegram only exposes ``get_chat_administrators`` — regular members
    are NOT returned.  So we register every admin we can see and rely on
    the ``chat_member`` handler + message handler for the rest.
    """
    svc = UserService(session)
    count = 0
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for member in admins:
            u = member.user
            if u.is_bot:
                continue
            await svc.upsert_user(u.id, first_name=u.first_name or "", username=u.username or "")
            added = await svc.add_user_chat(u.id, chat_id)
            if added:
                count += 1
    except Exception:
        log.warning("auto_register_failed", chat_id=chat_id, exc_info=True)
    return count


# --- My chat member (bot added/removed) ---

@router.my_chat_member()
async def on_bot_chat_member(event: ChatMemberUpdated, bot: Bot, session: AsyncSession) -> None:
    new_status = event.new_chat_member.status
    chat_id = event.chat.id

    svc = UserService(session)

    if new_status in ("member", "administrator"):
        await svc.upsert_chat(chat_id, title=event.chat.title or "")
        count = await _auto_register_members(bot, chat_id, session)
        msg = texts.WELCOME_BOT
        if count > 0:
            msg += f"\n\n{texts.AUTO_REGISTERED.format(count=count)}"
        try:
            await bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception:
            log.warning("welcome_send_failed", chat_id=chat_id, exc_info=True)

    elif new_status in ("left", "kicked"):
        await svc.remove_chat(chat_id)


# --- Chat member updates (user joined/left) ---

@router.chat_member()
async def on_chat_member(event: ChatMemberUpdated, session: AsyncSession) -> None:
    svc = UserService(session)
    user = event.new_chat_member.user
    chat_id = event.chat.id
    new_status = event.new_chat_member.status

    if user.is_bot:
        return

    if new_status in ("member", "administrator", "creator"):
        await svc.upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")
        await svc.upsert_chat(chat_id, title=event.chat.title or "")
        added = await svc.add_user_chat(user.id, chat_id)
        if added:
            with contextlib.suppress(Exception):
                await event.answer(
                    texts.USER_WELCOME.format(
                        chat_title=event.chat.title or "", name=user.first_name or "user"
                    ),
                    parse_mode="HTML",
                )

    elif new_status in ("left", "kicked"):
        removed = await svc.remove_user_chat(user.id, chat_id)
        if removed:
            task_svc = TaskService(session)
            await task_svc.remove_tasks_for_user_in_chat(user.id, chat_id)
            remaining = await svc.count_chat_users(chat_id)
            if remaining == 0:
                await svc.remove_chat(chat_id)


# --- Fallback: register user on any text message in a group ---

@router.message(F.text, F.chat.type.in_({"group", "supergroup"}))
async def on_group_message(message: Message, session: AsyncSession) -> None:
    user = message.from_user
    if not user or user.is_bot:
        return
    svc = UserService(session)
    await svc.upsert_user(user.id, first_name=user.first_name or "", username=user.username or "")
    await svc.upsert_chat(message.chat.id, title=message.chat.title or "")
    await svc.add_user_chat(user.id, message.chat.id)
