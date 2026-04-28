import re
from collections import Counter
from datetime import UTC, datetime, timedelta

import structlog
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot import texts
from centurion_bot.db.models import PRIORITY_EMOJI, PRIORITY_MEDIUM
from centurion_bot.handlers.recurring import _parse_priority_flag
from centurion_bot.keyboards.calendar import (
    CALLBACK_PREFIX,
    create_calendar,
    parse_calendar_callback,
)
from centurion_bot.services.task_service import TaskService
from centurion_bot.services.user_service import UserService

router = Router(name="task")
log = structlog.get_logger()

# Temporary in-memory store for multi-step task creation (per-user).
# In production you might use FSM / aiogram states or Redis,
# but for simplicity a dict is fine for a single-instance bot.
_user_data: dict[int, dict] = {}

DATE_FMT = "%Y-%m-%d"


# ---- helpers ----

def _mention(user_id: int, name: str) -> str:
    if user_id == 0:
        return "anyone in here"
    return f'<a href="tg://user?id={user_id}">{name}</a>'


async def _get_user_name(bot: Bot, chat_id: int, user_id: int) -> str:
    if user_id == 0:
        return "anyone"
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return (member.user.username or member.user.first_name or "unknown").lstrip("@")
    except Exception:
        return "unknown"


def _task_markup(task_id: int, show_complete: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    if show_complete:
        buttons.append(InlineKeyboardButton(text=texts.BTN_COMPLETE, callback_data=f"complete:{task_id}"))
    buttons.append(InlineKeyboardButton(text=texts.BTN_EDIT_DATE, callback_data=f"edit-date:{task_id}"))
    buttons.append(InlineKeyboardButton(text=texts.BTN_SHOW_TASK, callback_data=f"show-task:{task_id}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def _stats_text(stats: dict) -> str:
    d, o = stats["done"], stats["open"]
    return (
        texts.STATS_DONE.format(count=d["count"], on_time=d["onTime"], late=d["late"])
        + "\n"
        + texts.STATS_OPEN.format(count=o["count"], on_time=o["onTime"], late=o["late"])
    )


# ---- /do command ----

@router.message(Command("do"))
async def cmd_do(message: Message, bot: Bot, session: AsyncSession) -> None:
    user = message.from_user
    if not user:
        return

    raw = (message.text or "")[len("/do"):].strip()
    # Remove bot mention if present
    raw = re.sub(r"^@\S+\s*", "", raw)

    if not raw:
        await message.answer(texts.MISSING_TITLE.format(name=user.first_name), parse_mode="HTML")
        return

    # Parse priority flag
    raw, priority = _parse_priority_flag(raw)

    is_private = message.chat.type == "private"
    user_svc = UserService(session)

    if not is_private:
        await _do_inline_group(message, bot, session, raw, user.id, priority)
        return

    # Private chat: multi-step flow
    lines = raw.split("\n", 1)
    title = lines[0].strip()
    description = lines[1].strip() if len(lines) > 1 else ""

    chat_ids = await user_svc.get_user_chat_ids(user.id)
    if not chat_ids:
        await message.answer(texts.ADD_TO_GROUP, parse_mode="HTML")
        return

    _user_data[user.id] = {
        "title": title, "description": description, "owner_id": user.id, "priority": priority,
    }

    chats: list[list[InlineKeyboardButton]] = []
    for cid in chat_ids:
        try:
            chat_obj = await bot.get_chat(cid)
            chat_title = chat_obj.title or str(cid)
        except Exception:
            chat_title = str(cid)
        chats.append([InlineKeyboardButton(text=chat_title, callback_data=f"chat_id:{cid}")])

    await message.answer(texts.SELECT_CHAT, reply_markup=InlineKeyboardMarkup(inline_keyboard=chats), parse_mode="HTML")


async def _do_inline_group(
    message: Message, bot: Bot, session: AsyncSession, text: str, owner_id: int, priority: int = PRIORITY_MEDIUM,
) -> None:
    """Parse /do @user title in N days in a group chat."""
    pattern = r"([^@]*)@?(\S*)\s+in\s+(\d+)\s+(\w+)"
    match = re.match(pattern, text)
    if not match:
        await message.answer(texts.DO_GROUP_FORMAT, parse_mode="HTML")
        return

    title_raw, username_raw, count_str, unit_raw = match.groups()
    title = title_raw.strip() or username_raw.strip()
    username = username_raw.strip()

    unit = unit_raw.rstrip("s") + "s" if not unit_raw.endswith("s") else unit_raw
    try:
        due = datetime.now() + relativedelta(**{unit: int(count_str)})  # type: ignore[arg-type]
    except (TypeError, ValueError):
        await message.answer(texts.DO_GROUP_FORMAT, parse_mode="HTML")
        return

    user_svc = UserService(session)
    chat_id = message.chat.id

    # Resolve user
    mention_entity = next((e for e in (message.entities or []) if e.type == "text_mention"), None)

    if mention_entity and mention_entity.user:
        assignee_id = mention_entity.user.id
    elif username:
        # Look up by username among registered chat users
        user_ids = await user_svc.get_chat_user_ids(chat_id)
        assignee_id = 0
        for uid in user_ids:
            name = await _get_user_name(bot, chat_id, uid)
            if name.lower() == username.lower():
                assignee_id = uid
                break
        if assignee_id == 0 and username:
            await message.answer(texts.USER_NOT_REGISTERED.format(user_name=username), parse_mode="HTML")
            return
    else:
        assignee_id = 0  # group task

    task_svc = TaskService(session)
    is_group_task = assignee_id == 0

    # Use the full text before @user as the title
    if mention_entity:
        raw_title = (message.text or "")[len("/do"):mention_entity.offset].strip()
        title = raw_title or title

    await task_svc.add_task(
        user_id=assignee_id,
        chat_id=chat_id,
        owner_id=owner_id,
        title=title,
        due=due,
        is_group_task=is_group_task,
        priority=priority,
    )

    owner_name = await _get_user_name(bot, chat_id, owner_id)
    user_name = await _get_user_name(bot, chat_id, assignee_id) if not is_group_task else "anyone"
    due_text = f", due {due.date()}" if due else ""
    prio_emoji = PRIORITY_EMOJI.get(priority, "")
    prio_text = f" {prio_emoji}" if priority != PRIORITY_MEDIUM else ""

    await message.answer(
        texts.ADDED_TASK_GROUP.format(
            owner_name=_mention(owner_id, owner_name),
            user_name=_mention(assignee_id, user_name),
            title=title,
            due_text=due_text,
        ) + prio_text,
        parse_mode="HTML",
    )


# ---- inline callbacks for task creation flow ----

@router.callback_query(F.data.startswith("chat_id:"))
async def cb_select_chat(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    user_id = cq.from_user.id
    data = _user_data.get(user_id, {})
    if not data:
        await cq.answer("Session expired. Please start again with /do.")
        return

    chat_id = int(cq.data.split(":")[1])  # type: ignore[union-attr]
    data["chat_id"] = chat_id

    # Show user selection
    user_svc = UserService(session)
    user_ids = await user_svc.get_chat_user_ids(chat_id)
    buttons: list[list[InlineKeyboardButton]] = []
    for uid in user_ids:
        name = await _get_user_name(bot, chat_id, uid)
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"user_id:{uid}")])
    buttons.append([InlineKeyboardButton(text="Anyone", callback_data="user_id:0")])

    if cq.message:
        await cq.message.edit_text(
            texts.SELECT_USER.format(title=data.get("title", ""), name=cq.from_user.first_name),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML",
        )
    await cq.answer()


@router.callback_query(F.data.startswith("user_id:"))
async def cb_select_user(cq: CallbackQuery) -> None:
    user_id = cq.from_user.id
    data = _user_data.get(user_id, {})
    if not data:
        await cq.answer("Session expired.")
        return

    data["user_id"] = int(cq.data.split(":")[1])  # type: ignore[union-attr]

    if cq.message:
        await cq.message.edit_text(texts.SELECT_DATE, reply_markup=create_calendar(), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith(CALLBACK_PREFIX))
async def cb_calendar(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    data_str = cq.data or ""
    handled, selected_date, show_new = parse_calendar_callback(data_str)
    if not handled:
        await cq.answer()
        return

    user_id = cq.from_user.id

    if show_new:
        parts = data_str.split(":")
        year, month = int(parts[2]), int(parts[3])
        if cq.message:
            await cq.message.edit_reply_markup(reply_markup=create_calendar(year, month))
        await cq.answer()
        return

    data = _user_data.get(user_id, {})

    # Handle "no date" (selected_date is None, but not show_new)
    if data_str.endswith("nodate"):
        due = None
    else:
        due = datetime.combine(selected_date, datetime.min.time()) if selected_date else None

    # Check if this is an edit-due flow
    if "task_id" in data:
        if due is not None:
            task_svc = TaskService(session)
            task = await task_svc.get_task(data["task_id"])
            if task:
                if task.is_group_task:
                    await task_svc.update_due_date(task.id, due)
                    if cq.message:
                        await cq.message.edit_text(texts.DUE_UPDATED, parse_mode="HTML")
                else:
                    requestor_id = user_id
                    requestee_id = task.user_id if user_id == task.owner_id else task.owner_id
                    date_str = due.strftime(DATE_FMT)
                    cb_data = f":{task.id}\nuser_id:{requestor_id}\ndate:{date_str}"

                    markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [
                                InlineKeyboardButton(text=texts.BTN_ACCEPT, callback_data=f"edit-due-accept{cb_data}"),
                                InlineKeyboardButton(text=texts.BTN_DENY, callback_data=f"edit-due-deny{cb_data}"),
                            ]
                        ]
                    )
                    requestor_name = await _get_user_name(bot, task.chat_id, requestor_id)
                    await bot.send_message(
                        requestee_id,
                        texts.UPDATE_DUE_REQUEST.format(
                            user_name=_mention(requestor_id, requestor_name),
                            title=task.title,
                            prev_due=task.due.date() if task.due else "none",
                            new_due=due.date(),
                        ),
                        parse_mode="HTML",
                        reply_markup=markup,
                    )
                    requestee_name = await _get_user_name(bot, task.chat_id, requestee_id)
                    if cq.message:
                        await cq.message.edit_text(
                            texts.UPDATED_TASK_REQUESTED.format(user_name=_mention(requestee_id, requestee_name)),
                            parse_mode="HTML",
                        )
        _user_data.pop(user_id, None)
        await cq.answer()
        return

    # Normal task creation flow
    if not data or "chat_id" not in data:
        _user_data.pop(user_id, None)
        await cq.answer("Session expired.")
        return

    data["due"] = due
    task_svc = TaskService(session)
    assignee_id = data.get("user_id", 0)
    is_group_task = assignee_id == 0

    task = await task_svc.add_task(
        user_id=assignee_id,
        chat_id=data["chat_id"],
        owner_id=data["owner_id"],
        title=data["title"],
        description=data.get("description", ""),
        due=due,
        is_group_task=is_group_task,
        priority=data.get("priority", PRIORITY_MEDIUM),
    )

    user_name = await _get_user_name(bot, data["chat_id"], assignee_id)
    owner_name = await _get_user_name(bot, data["chat_id"], data["owner_id"])
    due_text = f", due {due.date()}" if due else ""

    if cq.message:
        await cq.message.edit_text(
            texts.ADDED_TASK.format(title=data["title"], user_name=_mention(assignee_id, user_name)),
            parse_mode="HTML",
        )

    # Notify group
    try:
        await bot.send_message(
            data["chat_id"],
            texts.ADDED_TASK_GROUP.format(
                owner_name=_mention(data["owner_id"], owner_name),
                user_name=_mention(assignee_id, user_name),
                title=data["title"],
                due_text=due_text,
            ),
            parse_mode="HTML",
        )
    except Exception:
        log.warning("group_notify_failed", chat_id=data["chat_id"], exc_info=True)

    _user_data.pop(user_id, None)
    await cq.answer()


# ---- Task action callbacks ----

@router.callback_query(F.data.startswith("complete:"))
async def cb_complete(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    task_id = int(cq.data.split(":")[1])  # type: ignore[union-attr]
    task_svc = TaskService(session)
    task = await task_svc.get_task(task_id)

    if not task:
        await cq.answer("Task not found.")
        return

    completed = await task_svc.complete_task(task_id, user_id=cq.from_user.id)
    if not completed:
        await cq.answer("Already completed.")
        return

    completer_id = cq.from_user.id
    completer_name = await _get_user_name(bot, task.chat_id, completer_id)
    owner_name = await _get_user_name(bot, task.chat_id, task.owner_id) if not task.is_group_task else "Everyone"

    if cq.message:
        await cq.message.edit_text(texts.TASK_DONE.format(title=task.title), parse_mode="HTML")

    try:
        await bot.send_message(
            task.chat_id,
            texts.TASK_DONE_GROUP.format(
                owner_name=_mention(task.owner_id, owner_name),
                user_name=_mention(completer_id, completer_name),
                title=task.title,
            ),
            parse_mode="HTML",
        )
    except Exception:
        log.warning("complete_notify_failed", exc_info=True)

    await cq.answer()


@router.callback_query(F.data.startswith("edit-date:"))
async def cb_edit_date(cq: CallbackQuery) -> None:
    task_id = int(cq.data.split(":")[1])  # type: ignore[union-attr]
    _user_data[cq.from_user.id] = {"task_id": task_id}
    if cq.message:
        await cq.message.edit_text(texts.SELECT_DATE, reply_markup=create_calendar(), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("show-task:"))
async def cb_show_task(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    task_id = int(cq.data.split(":")[1])  # type: ignore[union-attr]
    task_svc = TaskService(session)
    task = await task_svc.get_task(task_id)
    if task and task.description:
        await bot.send_message(task.owner_id, task.description, parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("edit-due-accept"))
async def cb_edit_due_accept(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    parts = (cq.data or "").split("\n")
    task_id = int(parts[0].split(":")[1])
    date_str = parts[2].split(":")[1]
    requestor_id = int(parts[1].split(":")[1])

    task_svc = TaskService(session)
    task = await task_svc.get_task(task_id)
    if not task:
        await cq.answer("Task not found.")
        return

    new_due = datetime.strptime(date_str, DATE_FMT)
    prev_due = task.due
    await task_svc.update_due_date(task_id, new_due)

    requestee_name = await _get_user_name(bot, task.chat_id, cq.from_user.id)
    requestor_name = await _get_user_name(bot, task.chat_id, requestor_id)

    try:
        await bot.send_message(
            task.chat_id,
            texts.UPDATE_DUE_ACCEPTED.format(
                requestee=_mention(cq.from_user.id, requestee_name),
                requestor=_mention(requestor_id, requestor_name),
                title=task.title,
                prev_due=prev_due.date() if prev_due else "none",
                new_due=new_due.date(),
            ),
            parse_mode="HTML",
        )
    except Exception:
        log.warning("due_accept_notify_failed", exc_info=True)

    if cq.message:
        await cq.message.edit_text(texts.UPDATE_GRANTED, parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("edit-due-deny"))
async def cb_edit_due_deny(cq: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    parts = (cq.data or "").split("\n")
    task_id = int(parts[0].split(":")[1])
    date_str = parts[2].split(":")[1]
    requestor_id = int(parts[1].split(":")[1])

    task_svc = TaskService(session)
    task = await task_svc.get_task(task_id)
    if not task:
        await cq.answer("Task not found.")
        return

    new_due = datetime.strptime(date_str, DATE_FMT)
    requestee_name = await _get_user_name(bot, task.chat_id, cq.from_user.id)
    requestor_name = await _get_user_name(bot, task.chat_id, requestor_id)

    try:
        await bot.send_message(
            task.chat_id,
            texts.UPDATE_DUE_DENIED.format(
                requestee=_mention(cq.from_user.id, requestee_name),
                requestor=_mention(requestor_id, requestor_name),
                title=task.title,
                prev_due=task.due.date() if task.due else "none",
                new_due=new_due.date(),
            ),
            parse_mode="HTML",
        )
    except Exception:
        log.warning("due_deny_notify_failed", exc_info=True)

    if cq.message:
        await cq.message.edit_text(texts.UPDATE_DENIED, parse_mode="HTML")
    await cq.answer()


# ---- /tasks ----

@router.message(Command("tasks"))
async def cmd_tasks(message: Message, bot: Bot, session: AsyncSession) -> None:
    task_svc = TaskService(session)
    is_private = message.chat.type == "private"

    if not is_private:
        tasks = [t for t in await task_svc.get_tasks_for_chat(message.chat.id) if not t.done]
        if not tasks:
            await message.answer(texts.NO_TASKS, parse_mode="HTML")
            return
        lines = []
        for t in tasks:
            user_name = await _get_user_name(bot, t.chat_id, t.user_id)
            owner_name = await _get_user_name(bot, t.chat_id, t.owner_id)
            due_str = f"{t.due.date()} - " if t.due else ""
            lines.append(f"  {due_str}{t.title} from {owner_name} for {user_name}")
        text = "\n".join(lines)

        group_tasks = [t for t in tasks if t.is_group_task]
        for t in group_tasks:
            await message.answer(
                f"{t.title}",
                reply_markup=_task_markup(t.id, show_complete=True),
                parse_mode="HTML",
            )

        await message.answer(text + f"\n\n{texts.TASK_OVERVIEW_PRIVATE}", parse_mode="HTML")
        return

    user_id = message.from_user.id  # type: ignore[union-attr]

    assigned = [t for t in await task_svc.get_tasks(user_id) if not t.done]
    msg = f"<b>{texts.TASK_HEADLINE_ASSIGNED}:</b>\n"
    if not assigned:
        msg += texts.NO_TASKS + "\n"
    for t in assigned:
        owner_name = await _get_user_name(bot, t.chat_id, t.owner_id)
        due_str = f"{t.due.date()} - " if t.due else ""
        try:
            chat_obj = await bot.get_chat(t.chat_id)
            chat_title = chat_obj.title or str(t.chat_id)
        except Exception:
            chat_title = str(t.chat_id)
        msg += f"  {due_str}{chat_title} - {t.title} ({owner_name})\n"
    await message.answer(msg, parse_mode="HTML")
    for t in assigned:
        await message.answer(
            t.title,
            reply_markup=_task_markup(t.id, show_complete=True),
            parse_mode="HTML",
        )

    owning = [t for t in await task_svc.get_owning_tasks(user_id) if not t.done]
    msg2 = f"\n<b>{texts.TASK_HEADLINE_OWNING}:</b>\n"
    if not owning:
        msg2 += texts.NO_TASKS + "\n"
    for t in owning:
        user_name = await _get_user_name(bot, t.chat_id, t.user_id)
        due_str = f"{t.due.date()} - " if t.due else ""
        try:
            chat_obj = await bot.get_chat(t.chat_id)
            chat_title = chat_obj.title or str(t.chat_id)
        except Exception:
            chat_title = str(t.chat_id)
        msg2 += f"  {due_str}{chat_title} - {t.title} ({user_name})\n"
    await message.answer(msg2, parse_mode="HTML")
    for t in owning:
        await message.answer(
            t.title,
            reply_markup=_task_markup(t.id, show_complete=False),
            parse_mode="HTML",
        )


# ---- /stats ----

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    task_svc = TaskService(session)
    is_private = message.chat.type == "private"

    if is_private:
        user_id = message.from_user.id  # type: ignore[union-attr]
        stats = await task_svc.get_user_stats(user_id)
        owning_msg = _stats_text(stats["owning"])
        assigned_msg = _stats_text(stats["assigned"])
        msg = (
            f"You have been assigned to {stats['assigned']['count']} tasks:\n{assigned_msg}\n\n"
            f"You assigned others to {stats['owning']['count']} tasks:\n{owning_msg}"
        )
    else:
        stats = await task_svc.get_chat_stats(message.chat.id)
        msg = _stats_text(stats)

    await message.answer(msg, parse_mode="HTML")


# ---- /due — daily task overview ----

@router.message(Command("due"))
async def cmd_due(message: Message, bot: Bot, session: AsyncSession) -> None:
    await _show_task_overviews(bot, session, show_near_future=True)
    await message.answer("Daily task overview sent!", parse_mode="HTML")


# ---- /weekly — weekly review ----

@router.message(Command("weekly"))
async def cmd_weekly(message: Message, bot: Bot, session: AsyncSession) -> None:
    await _show_weekly_review(bot, session)
    await message.answer("Weekly review sent!", parse_mode="HTML")


# ---- Scheduled jobs ----

async def job_daily_tasks(bot: Bot, session: AsyncSession) -> None:
    await _show_task_overviews(bot, session, show_near_future=True)


async def job_weekly_review(bot: Bot, session: AsyncSession) -> None:
    await _show_weekly_review(bot, session)


async def _show_task_overviews(bot: Bot, session: AsyncSession, show_near_future: bool = False) -> None:
    user_svc = UserService(session)
    task_svc = TaskService(session)

    for user_id in await user_svc.get_all_user_ids():
        summary = await _build_task_summary(bot, task_svc, user_id, show_near_future)
        if summary:
            try:
                await bot.send_message(user_id, summary, parse_mode="HTML")
            except Exception:
                log.warning("daily_send_failed", user_id=user_id, exc_info=True)

    for chat_id in await user_svc.get_all_chat_ids():
        chat_tasks = await task_svc.get_tasks_for_chat(chat_id)
        today = datetime.now(tz=UTC).date()
        due_today = [t for t in chat_tasks if not t.done and t.is_group_task and t.due and t.due.date() <= today]
        if due_today:
            lines = [f"<b>{texts.SUMMARY_DUE_TODAY}:</b>"]
            for t in due_today:
                owner_name = await _get_user_name(bot, chat_id, t.owner_id)
                lines.append(f"  {t.title} (from {owner_name})")
            try:
                await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
            except Exception:
                log.warning("daily_chat_send_failed", chat_id=chat_id, exc_info=True)


async def _build_task_summary(bot: Bot, task_svc: TaskService, user_id: int, show_near_future: bool) -> str:
    due_past = await task_svc.get_due_past(user_id)
    due_today = await task_svc.get_due_today(user_id)

    parts = []
    if due_past:
        lines = [await _task_line(bot, t) for t in due_past]
        parts.append(f"<b>{texts.SUMMARY_OVERDUE}:</b>\n" + "\n".join(lines))
    if due_today:
        lines = [await _task_line(bot, t) for t in due_today]
        parts.append(f"<b>{texts.SUMMARY_DUE_TODAY}:</b>\n" + "\n".join(lines))
    if show_near_future:
        due_week = await task_svc.get_due_this_week(user_id)
        if due_week:
            lines = [await _task_line(bot, t) for t in due_week]
            parts.append(f"<b>{texts.SUMMARY_DUE_THIS_WEEK}:</b>\n" + "\n".join(lines))
    due_undef = await task_svc.get_due_undefined(user_id)
    if due_undef:
        lines = [await _task_line(bot, t) for t in due_undef]
        parts.append(f"<b>{texts.SUMMARY_DUE_UNDEFINED}:</b>\n" + "\n".join(lines))

    if parts:
        return f"<b>{texts.SUMMARY_HEADLINE}:</b>\n\n" + "\n\n".join(parts)
    return ""


async def _task_line(bot: Bot, task) -> str:
    try:
        chat_obj = await bot.get_chat(task.chat_id)
        chat_title = chat_obj.title or str(task.chat_id)
    except Exception:
        chat_title = str(task.chat_id)
    owner_name = await _get_user_name(bot, task.chat_id, task.owner_id)
    return f"  {chat_title}: {task.title} from {owner_name}"


async def _show_weekly_review(bot: Bot, session: AsyncSession) -> None:
    user_svc = UserService(session)
    task_svc = TaskService(session)

    now = datetime.now(tz=UTC)
    last_week = now - timedelta(days=7)
    week_before = last_week - timedelta(days=7)
    next_week = now + timedelta(days=7)

    for chat_id in await user_svc.get_all_chat_ids():
        try:
            chat_obj = await bot.get_chat(chat_id)
            chat_title = chat_obj.title or str(chat_id)
        except Exception:
            chat_title = str(chat_id)

        created_stats, done_stats = await task_svc.get_period_stats(chat_id, last_week, now)
        prev_created, prev_done = await task_svc.get_period_stats(chat_id, week_before, last_week)

        has_activity = created_stats["count"] > 0 or done_stats["count"] > 0

        msg = f"<b>{texts.REVIEW_HEADLINE.format(chat_title=chat_title)}:</b>\n\n"

        if has_activity:
            on_time_pct = done_stats["done"]["onTimePercent"]
            on_time_text = f" ({on_time_pct:.0f}% in time)" if done_stats["done"]["count"] > 0 else ""
            msg += texts.REVIEW_SUMMARY.format(
                created=created_stats["count"], done=done_stats["done"]["count"], on_time_text=on_time_text
            )

            created_diff = created_stats["count"] - prev_created["count"]
            done_diff = done_stats["done"]["count"] - prev_done["done"]["count"]
            msg += "\n" + texts.REVIEW_COMPARISON.format(
                created_dir="increased" if created_diff >= 0 else "decreased",
                created_diff=abs(created_diff),
                done_dir="increased" if done_diff >= 0 else "decreased",
                done_diff=abs(done_diff),
            )
            msg += "\n\n"

            # Done tasks
            all_tasks = await task_svc.get_tasks_for_chat(chat_id)
            done_tasks = [t for t in all_tasks if t.done and t.done > last_week]
            if done_tasks:
                msg += f"<b>{texts.REVIEW_DONE_TASKS}</b>\n"
                for t in done_tasks:
                    user_name = await _get_user_name(bot, chat_id, t.user_id)
                    owner_name = await _get_user_name(bot, chat_id, t.owner_id)
                    in_time = "in time!" if (t.due is None or t.done.date() <= t.due.date()) else "a little late."
                    msg += f"  {user_name} completed {t.title} from {owner_name} — {in_time}\n"

                # Most active user
                counter = Counter(t.user_id for t in done_tasks)
                most_count = counter.most_common(1)[0][1]
                most_users = [
                    await _get_user_name(bot, chat_id, uid)
                    for uid, c in counter.items()
                    if c == most_count
                ]
                msg += f"\nMost active: {' and '.join(most_users)}!\n\n"
        else:
            msg += "No activity this week.\n\n"

        # Open overdue tasks
        all_tasks = await task_svc.get_tasks_for_chat(chat_id)
        today = datetime.now(tz=UTC).date()
        overdue = [t for t in all_tasks if not t.done and t.due and t.due.date() <= today]
        if overdue:
            overdue.sort(key=lambda t: t.due)  # type: ignore[union-attr, arg-type]
            msg += f"<b>{texts.REVIEW_INCOMPLETE}</b>\n"
            for t in overdue:
                user_name = await _get_user_name(bot, chat_id, t.user_id)
                owner_name = await _get_user_name(bot, chat_id, t.owner_id)
                days_open = (today - t.due.date()).days
                msg += f"  {user_name} has {t.title} from {owner_name} open for {days_open} day(s)\n"
            msg += "\n"

        # Upcoming tasks
        upcoming = [t for t in all_tasks if not t.done and t.due and today < t.due.date() <= next_week.date()]
        if upcoming:
            upcoming.sort(key=lambda t: t.due)  # type: ignore[union-attr, arg-type]
            msg += f"<b>{texts.REVIEW_UPCOMING}</b>\n"
            for t in upcoming:
                user_name = await _get_user_name(bot, chat_id, t.user_id)
                owner_name = await _get_user_name(bot, chat_id, t.owner_id)
                days_left = (t.due.date() - today).days
                msg += f"  {user_name} has {days_left} day(s) to complete {t.title} from {owner_name}\n"
            msg += "\n"

        if not has_activity and not overdue and not upcoming:
            continue

        # Ranking
        user_ids = await user_svc.get_chat_user_ids(chat_id)
        if user_ids:
            rankings = []
            for uid in user_ids:
                _, user_done = await task_svc.get_period_stats(chat_id)
                name = await _get_user_name(bot, chat_id, uid)
                rankings.append((name, user_done["done"]["count"], user_done["done"]["onTimePercent"]))
            rankings.sort(key=lambda x: (x[1], x[2]), reverse=True)
            msg += f"<b>{texts.RANKING}:</b>\n"
            for name, done_count, on_time in rankings:
                msg += f"  {name}: {done_count} done, {on_time:.0f}% on time\n"

        msg += f"\n{texts.REVIEW_MOTIVATION}"

        try:
            await bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception:
            log.warning("weekly_review_send_failed", chat_id=chat_id, exc_info=True)
