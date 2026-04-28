from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import PRIORITY_HIGH, PRIORITY_MEDIUM
from centurion_bot.services.checkin_service import CheckInService
from centurion_bot.services.feedback_service import FeedbackService
from centurion_bot.services.recurring_service import RecurringService
from centurion_bot.services.task_service import TaskService
from centurion_bot.services.user_service import UserService


@pytest.mark.asyncio
async def test_user_service_upsert(session: AsyncSession):
    svc = UserService(session)
    added = await svc.upsert_user(111, first_name="Alice", username="alice")
    assert added is True
    added2 = await svc.upsert_user(111, first_name="Alice2")
    assert added2 is False

    user = await svc.get_user(111)
    assert user is not None
    assert user.first_name == "Alice2"


@pytest.mark.asyncio
async def test_user_chat_management(session: AsyncSession):
    svc = UserService(session)
    await svc.upsert_user(1)
    await svc.upsert_chat(-100)

    added = await svc.add_user_chat(1, -100)
    assert added is True
    added2 = await svc.add_user_chat(1, -100)
    assert added2 is False

    users = await svc.get_chat_user_ids(-100)
    assert 1 in users

    chats = await svc.get_user_chat_ids(1)
    assert -100 in chats

    removed = await svc.remove_user_chat(1, -100)
    assert removed is True
    users2 = await svc.get_chat_user_ids(-100)
    assert 1 not in users2


@pytest.mark.asyncio
async def test_task_service_lifecycle(session: AsyncSession):
    svc = TaskService(session)
    task = await svc.add_task(
        user_id=1, chat_id=-100, owner_id=2, title="Test task", due=datetime.now(tz=UTC) + timedelta(days=1)
    )
    assert task.id is not None
    assert task.done is None

    fetched = await svc.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Test task"

    completed = await svc.complete_task(task.id)
    assert completed is True

    completed2 = await svc.complete_task(task.id)
    assert completed2 is False


@pytest.mark.asyncio
async def test_task_due_queries(session: AsyncSession):
    svc = TaskService(session)
    now = datetime.now(tz=UTC)
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="Past", due=now - timedelta(days=2))
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="Today", due=now)
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="Future", due=now + timedelta(days=14))
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="No due")

    past = await svc.get_due_past(1)
    assert any(t.title == "Past" for t in past)

    undef = await svc.get_due_undefined(1)
    assert any(t.title == "No due" for t in undef)


@pytest.mark.asyncio
async def test_task_stats(session: AsyncSession):
    svc = TaskService(session)
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="T1")
    await svc.add_task(user_id=1, chat_id=-100, owner_id=2, title="T2")

    stats = await svc.get_user_stats(1)
    assert stats["assigned"]["count"] == 2


@pytest.mark.asyncio
async def test_feedback_service(session: AsyncSession):
    svc = FeedbackService(session)
    fb = await svc.add(user_id=1, text="Great bot!")
    assert fb.id is not None

    fetched = await svc.get(fb.id)
    assert fetched is not None
    assert fetched.text == "Great bot!"
    assert fetched.done is None

    await svc.set_resolved(fb.id)
    resolved = await svc.get(fb.id)
    assert resolved is not None
    assert resolved.done is not None

    stats = await svc.get_stats()
    assert stats["count"] == 1


# ---- Recurring tasks ----


@pytest.mark.asyncio
async def test_recurring_service_create_and_generate(session: AsyncSession):
    svc = RecurringService(session)
    rt = await svc.create(
        chat_id=-100, owner_id=1, title="Daily cleanup", schedule="daily", priority=PRIORITY_HIGH,
    )
    assert rt.id is not None
    assert rt.is_active is True

    active = await svc.get_active()
    assert len(active) == 1

    generated = await svc.generate_due_tasks()
    assert len(generated) == 1
    assert generated[0].title == "Daily cleanup"
    assert generated[0].priority == PRIORITY_HIGH
    assert generated[0].recurring_id == rt.id

    # Should NOT generate again immediately
    generated2 = await svc.generate_due_tasks()
    assert len(generated2) == 0


@pytest.mark.asyncio
async def test_recurring_service_deactivate(session: AsyncSession):
    svc = RecurringService(session)
    rt = await svc.create(
        chat_id=-100, owner_id=1, title="Weekly report", schedule="weekly",
    )
    stopped = await svc.deactivate(rt.id)
    assert stopped is True

    active = await svc.get_active()
    assert len(active) == 0

    # Double deactivate returns False
    stopped2 = await svc.deactivate(rt.id)
    assert stopped2 is False


# ---- Task priorities ----


@pytest.mark.asyncio
async def test_task_priority(session: AsyncSession):
    svc = TaskService(session)
    task = await svc.add_task(
        user_id=1, chat_id=-100, owner_id=2, title="Urgent", priority=PRIORITY_HIGH,
        due=datetime.now(tz=UTC) - timedelta(days=1),
    )
    assert task.priority == PRIORITY_HIGH

    overdue = await svc.get_overdue_high_priority()
    assert any(t.id == task.id for t in overdue)

    # Medium priority overdue should NOT appear
    task2 = await svc.add_task(
        user_id=1, chat_id=-100, owner_id=2, title="Normal", priority=PRIORITY_MEDIUM,
        due=datetime.now(tz=UTC) - timedelta(days=1),
    )
    overdue2 = await svc.get_overdue_high_priority()
    assert not any(t.id == task2.id for t in overdue2)


# ---- Check-ins ----


@pytest.mark.asyncio
async def test_checkin_service(session: AsyncSession):
    svc = CheckInService(session)
    ci = await svc.add(
        user_id=1, chat_id=-100, done_text="Fixed bugs", plan_text="Deploy", blockers_text="",
    )
    assert ci.id is not None

    today = await svc.get_today(-100)
    assert len(today) == 1
    assert today[0].done_text == "Fixed bugs"

    checked_in = await svc.get_today_user_ids(-100)
    assert 1 in checked_in

    stats = await svc.get_stats(-100)
    assert stats["total_checkins"] == 1
    assert stats["unique_users"] == 1


@pytest.mark.asyncio
async def test_checkin_streak(session: AsyncSession):
    svc = CheckInService(session)
    # Add a check-in for today
    await svc.add(user_id=1, chat_id=-100, done_text="Today work")

    streak = await svc.get_user_streak(1, -100)
    assert streak == 1
