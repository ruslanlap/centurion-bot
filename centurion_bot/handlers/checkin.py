import structlog
from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.config import settings
from centurion_bot.services.checkin_service import CheckInService
from centurion_bot.services.user_service import UserService

router = Router(name="checkin")
log = structlog.get_logger()


async def _get_user_name(bot: Bot, chat_id: int, user_id: int) -> str:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.user.first_name or member.user.username or "unknown"
    except Exception:
        return "unknown"


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, bot: Bot, session: AsyncSession) -> None:
    """Submit a check-in report.

    Format: /checkin
    done: what I completed
    plan: what I will do
    blockers: what blocks me
    """
    user = message.from_user
    if not user:
        return

    raw = (message.text or "")[len("/checkin"):].strip()
    if not raw:
        await message.answer(texts.CHECKIN_USAGE, parse_mode="HTML")
        return

    done_text = ""
    plan_text = ""
    blockers_text = ""

    lines = raw.split("\n")
    current_section = "done"

    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("done:"):
            current_section = "done"
            done_text += lower[len("done:"):].strip() + "\n"
        elif lower.startswith("plan:"):
            current_section = "plan"
            plan_text += lower[len("plan:"):].strip() + "\n"
        elif lower.startswith(("blockers:", "blocker:", "blocked:")):
            current_section = "blockers"
            colon_idx = lower.index(":") + 1
            blockers_text += line[colon_idx:].strip() + "\n"
        else:
            if current_section == "done":
                done_text += line.strip() + "\n"
            elif current_section == "plan":
                plan_text += line.strip() + "\n"
            else:
                blockers_text += line.strip() + "\n"

    done_text = done_text.strip()
    plan_text = plan_text.strip()
    blockers_text = blockers_text.strip()

    if not done_text and not plan_text:
        done_text = raw.strip()

    chat_id = message.chat.id
    is_private = message.chat.type == "private"

    if is_private:
        user_svc = UserService(session)
        chat_ids = await user_svc.get_user_chat_ids(user.id)
        if not chat_ids:
            await message.answer(texts.ADD_TO_GROUP, parse_mode="HTML")
            return
        chat_id = chat_ids[0]

    svc = CheckInService(session)
    await svc.add(
        user_id=user.id,
        chat_id=chat_id,
        done_text=done_text,
        plan_text=plan_text,
        blockers_text=blockers_text,
    )

    streak = await svc.get_user_streak(user.id, chat_id)
    streak_text = f" (streak: {streak} day(s))" if streak > 1 else ""

    await message.answer(
        texts.CHECKIN_SAVED.format(name=user.first_name, streak=streak_text),
        parse_mode="HTML",
    )

    if blockers_text and settings.admin_id:
        try:
            name = user.first_name or user.username or "unknown"
            await bot.send_message(
                settings.admin_id,
                texts.CHECKIN_BLOCKER_ALERT.format(
                    name=name, blockers=blockers_text
                ),
                parse_mode="HTML",
            )
        except Exception:
            log.warning("blocker_alert_failed", exc_info=True)


@router.message(Command("checkin_report"))
async def cmd_checkin_report(
    message: Message, bot: Bot, session: AsyncSession
) -> None:
    chat_id = message.chat.id
    is_private = message.chat.type == "private"

    if is_private:
        user_svc = UserService(session)
        user_id = message.from_user.id if message.from_user else 0
        chat_ids = await user_svc.get_user_chat_ids(user_id)
        if not chat_ids:
            await message.answer(texts.ADD_TO_GROUP, parse_mode="HTML")
            return
        chat_id = chat_ids[0]

    svc = CheckInService(session)
    user_svc = UserService(session)

    today_checkins = await svc.get_today(chat_id)
    checked_in_ids = await svc.get_today_user_ids(chat_id)
    all_user_ids = set(await user_svc.get_chat_user_ids(chat_id))

    missing_ids = all_user_ids - checked_in_ids

    msg = f"<b>{texts.CHECKIN_REPORT_HEADER}:</b>\n\n"

    if today_checkins:
        for ci in today_checkins:
            name = await _get_user_name(bot, chat_id, ci.user_id)
            msg += f"<b>{name}:</b>\n"
            if ci.done_text:
                msg += f"  Done: {ci.done_text}\n"
            if ci.plan_text:
                msg += f"  Plan: {ci.plan_text}\n"
            if ci.blockers_text:
                msg += f"  Blockers: {ci.blockers_text}\n"
            msg += "\n"
    else:
        msg += "No check-ins yet today.\n\n"

    if missing_ids:
        missing_names = [
            await _get_user_name(bot, chat_id, uid) for uid in missing_ids
        ]
        msg += f"<b>{texts.CHECKIN_MISSING}:</b> {', '.join(missing_names)}\n"

    stats = await svc.get_stats(chat_id)
    msg += (
        f"\n<i>Last {stats['days']} days: "
        f"{stats['total_checkins']} check-ins from {stats['unique_users']} user(s), "
        f"{stats['with_blockers']} with blockers</i>"
    )

    await message.answer(msg, parse_mode="HTML")
