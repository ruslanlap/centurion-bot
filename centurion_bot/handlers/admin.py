import structlog
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.config import settings
from centurion_bot.services.feedback_service import FeedbackService
from centurion_bot.services.task_service import TaskService
from centurion_bot.services.user_service import UserService

router = Router(name="admin")
log = structlog.get_logger()


def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    task_svc = TaskService(session)
    user_svc = UserService(session)
    fb_svc = FeedbackService(session)

    task_stats = await task_svc.get_all_stats()
    user_stats = await user_svc.get_stats()
    fb_stats = await fb_svc.get_stats()

    msg = "<b>Tasks:</b>\n"
    total, opened, done = task_stats["count"], task_stats["open"]["count"], task_stats["done"]["count"]
    msg += f"  Total: {total}, Open: {opened}, Done: {done}\n\n"
    msg += "<b>Users:</b>\n"
    msg += "\n".join(f"  {k}: {v}" for k, v in user_stats.items()) + "\n\n"
    msg += "<b>Feedback:</b>\n"
    msg += "\n".join(f"  {k}: {v}" for k, v in fb_stats.items())

    await message.answer(msg, parse_mode="HTML")


@router.message(Command("admin_announce"))
async def cmd_admin_announce(message: Message, bot: Bot, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    text = (message.text or "")[len("/admin_announce"):].strip()
    if not text:
        await message.answer(texts.MISSING_TEXT.format(name=message.from_user.first_name), parse_mode="HTML")
        return

    user_svc = UserService(session)
    user_ids = await user_svc.get_all_user_ids()

    announcement = f"<b>{texts.ANNOUNCEMENT_PREFIX}</b>\n{text}\n\n{texts.FEEDBACK_REPLY_POSTFIX}"
    success = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, announcement, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

    await message.answer(texts.ANNOUNCEMENT_SENT.format(success=success, failed=failed), parse_mode="HTML")


@router.message(Command("admin_feedback_show"))
async def cmd_admin_feedback_show(message: Message, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    svc = FeedbackService(session)
    all_fb = await svc.get_all()
    open_fb = [fb for fb in all_fb if fb.done is None]

    if not open_fb:
        await message.answer(texts.FEEDBACK_NONE, parse_mode="HTML")
        return

    lines = [f"{fb.id} / {fb.created.date()} / {fb.text}" for fb in open_fb]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("admin_feedback_reply"))
async def cmd_admin_feedback_reply(message: Message, bot: Bot, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    text = (message.text or "")[len("/admin_feedback_reply"):].strip()
    parts = text.split(" ", 1)
    if len(parts) < 2:
        await message.answer(texts.FEEDBACK_INCLUDE_ID, parse_mode="HTML")
        return

    try:
        feedback_id = int(parts[0])
    except ValueError:
        await message.answer(texts.FEEDBACK_INCLUDE_ID, parse_mode="HTML")
        return
    reply_text = parts[1]

    svc = FeedbackService(session)
    fb = await svc.get(feedback_id)
    if not fb:
        await message.answer(texts.FEEDBACK_NOT_FOUND, parse_mode="HTML")
        return

    try:
        await bot.send_message(
            fb.user_id,
            f"{texts.FEEDBACK_REPLY_PREFIX}\n{reply_text}\n\n{texts.FEEDBACK_REPLY_POSTFIX}",
            parse_mode="HTML",
        )
    except Exception:
        log.warning("feedback_reply_failed", user_id=fb.user_id, exc_info=True)

    await message.answer("Reply sent!", parse_mode="HTML")


@router.message(Command("admin_feedback_close"))
async def cmd_admin_feedback_close(message: Message, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        return

    text = (message.text or "")[len("/admin_feedback_close"):].strip()
    if not text:
        await message.answer(texts.FEEDBACK_INCLUDE_ID, parse_mode="HTML")
        return

    try:
        feedback_id = int(text)
    except ValueError:
        await message.answer(texts.FEEDBACK_INCLUDE_ID, parse_mode="HTML")
        return

    svc = FeedbackService(session)
    await svc.set_resolved(feedback_id)
    await message.answer(texts.FEEDBACK_CLOSED, parse_mode="HTML")
