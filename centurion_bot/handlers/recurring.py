import re

import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.db.models import PRIORITY_EMOJI, PRIORITY_LABELS
from centurion_bot.services.recurring_service import RecurringService
from centurion_bot.services.user_service import UserService

router = Router(name="recurring")
log = structlog.get_logger()

VALID_SCHEDULES = {"daily", "weekly", "monthly"}


def _parse_priority_flag(text: str) -> tuple[str, int]:
    """Extract !high, !low, !medium from text, return (cleaned_text, priority)."""
    from centurion_bot.db.models import PRIORITY_HIGH, PRIORITY_LOW, PRIORITY_MEDIUM

    mapping = {"!high": PRIORITY_HIGH, "!low": PRIORITY_LOW, "!medium": PRIORITY_MEDIUM}
    for flag, prio in mapping.items():
        if flag in text.lower():
            cleaned = re.sub(re.escape(flag), "", text, flags=re.IGNORECASE).strip()
            return cleaned, prio
    return text, PRIORITY_MEDIUM


@router.message(Command("repeat"))
async def cmd_repeat(message: Message, bot: Bot, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    raw = (message.text or "")[len("/repeat"):].strip()
    raw = re.sub(r"^@\S+\s*", "", raw)

    if not raw:
        await message.answer(texts.REPEAT_USAGE, parse_mode="HTML")
        return

    raw, priority = _parse_priority_flag(raw)

    pattern = r"(.+?)\s+(daily|weekly|monthly)\s*$"
    match = re.match(pattern, raw, re.IGNORECASE)
    if not match:
        await message.answer(texts.REPEAT_USAGE, parse_mode="HTML")
        return

    title = match.group(1).strip()
    schedule = match.group(2).lower()

    chat_id = message.chat.id
    is_private = message.chat.type == "private"

    if is_private:
        user_svc = UserService(session)
        chat_ids = await user_svc.get_user_chat_ids(user.id)
        if not chat_ids:
            await message.answer(texts.ADD_TO_GROUP, parse_mode="HTML")
            return
        chat_id = chat_ids[0]

    svc = RecurringService(session)
    rt = await svc.create(
        chat_id=chat_id,
        owner_id=user.id,
        title=title,
        schedule=schedule,
        is_group_task=True,
        priority=priority,
    )

    emoji = PRIORITY_EMOJI.get(priority, "")
    await message.answer(
        texts.REPEAT_CREATED.format(
            title=title,
            schedule=schedule,
            priority=f"{emoji} {PRIORITY_LABELS.get(priority, 'medium')}",
            id=rt.id,
        ),
        parse_mode="HTML",
    )


@router.message(Command("repeats"))
async def cmd_repeats(message: Message, session: AsyncSession) -> None:
    chat_id = message.chat.id
    is_private = message.chat.type == "private"

    if is_private:
        user_svc = UserService(session)
        user_id = message.from_user.id if message.from_user else 0
        chat_ids = await user_svc.get_user_chat_ids(user_id)
        if not chat_ids:
            await message.answer(texts.NO_RECURRING, parse_mode="HTML")
            return
        chat_id = chat_ids[0]

    svc = RecurringService(session)
    recurring = await svc.get_for_chat(chat_id)

    if not recurring:
        await message.answer(texts.NO_RECURRING, parse_mode="HTML")
        return

    lines = [f"<b>{texts.RECURRING_LIST_HEADER}:</b>"]
    for rt in recurring:
        emoji = PRIORITY_EMOJI.get(rt.priority, "")
        lines.append(f"  {emoji} #{rt.id} — {rt.title} ({rt.schedule})")

    buttons = [
        [InlineKeyboardButton(
            text=f"Stop #{rt.id} — {rt.title}",
            callback_data=f"stop_repeat:{rt.id}",
        )]
        for rt in recurring
    ]

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("stop_repeat:"))
async def cb_stop_repeat(cq: CallbackQuery, session: AsyncSession) -> None:
    recurring_id = int((cq.data or "").split(":")[1])
    svc = RecurringService(session)
    stopped = await svc.deactivate(recurring_id)

    if stopped:
        if cq.message:
            await cq.message.edit_text(
                texts.REPEAT_STOPPED.format(id=recurring_id), parse_mode="HTML"
            )
    else:
        await cq.answer("Already stopped or not found.")
    await cq.answer()
