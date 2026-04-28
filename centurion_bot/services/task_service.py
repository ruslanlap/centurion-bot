from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import PRIORITY_HIGH, PRIORITY_MEDIUM, Task


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_task(
        self,
        user_id: int,
        chat_id: int,
        owner_id: int,
        title: str,
        description: str = "",
        due: datetime | None = None,
        is_group_task: bool = False,
        priority: int = PRIORITY_MEDIUM,
        recurring_id: int | None = None,
    ) -> Task:
        task = Task(
            user_id=user_id,
            chat_id=chat_id,
            owner_id=owner_id,
            title=title,
            description=description,
            due=due,
            is_group_task=is_group_task,
            priority=priority,
            recurring_id=recurring_id,
        )
        self._s.add(task)
        await self._s.flush()
        return task

    async def get_task(self, task_id: int) -> Task | None:
        return await self._s.get(Task, task_id)

    async def get_tasks(self, user_id: int) -> list[Task]:
        result = await self._s.scalars(
            select(Task).where(Task.user_id == user_id).order_by(Task.due.nulls_last())
        )
        return list(result.all())

    async def get_owning_tasks(self, owner_id: int) -> list[Task]:
        result = await self._s.scalars(
            select(Task).where(Task.owner_id == owner_id).order_by(Task.due.nulls_last())
        )
        return list(result.all())

    async def get_tasks_for_chat(self, chat_id: int) -> list[Task]:
        result = await self._s.scalars(
            select(Task).where(Task.chat_id == chat_id).order_by(Task.due.nulls_last())
        )
        return list(result.all())

    async def get_due_today(self, user_id: int) -> list[Task]:
        today = datetime.now(tz=UTC).date()
        result = await self._s.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.done.is_(None),
                func.date(Task.due) == today,
            ).order_by(Task.due)
        )
        return list(result.all())

    async def get_due_this_week(self, user_id: int) -> list[Task]:
        today = datetime.now(tz=UTC).date()
        week_later = today + timedelta(days=7)
        result = await self._s.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.done.is_(None),
                func.date(Task.due) > today,
                func.date(Task.due) <= week_later,
            ).order_by(Task.due)
        )
        return list(result.all())

    async def get_due_later(self, user_id: int) -> list[Task]:
        week_later = datetime.now(tz=UTC).date() + timedelta(days=7)
        result = await self._s.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.done.is_(None),
                func.date(Task.due) > week_later,
            ).order_by(Task.due)
        )
        return list(result.all())

    async def get_due_past(self, user_id: int) -> list[Task]:
        today = datetime.now(tz=UTC).date()
        result = await self._s.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.done.is_(None),
                func.date(Task.due) < today,
            ).order_by(Task.due)
        )
        return list(result.all())

    async def get_due_undefined(self, user_id: int) -> list[Task]:
        result = await self._s.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.done.is_(None),
                Task.due.is_(None),
            )
        )
        return list(result.all())

    async def complete_task(self, task_id: int, user_id: int | None = None) -> bool:
        task = await self._s.get(Task, task_id)
        if not task or task.done is not None:
            return False
        task.done = datetime.now(tz=UTC)
        if task.is_group_task and user_id is not None:
            task.user_id = user_id
        await self._s.flush()
        return True

    async def update_due_date(self, task_id: int, due: datetime) -> None:
        task = await self._s.get(Task, task_id)
        if task:
            task.due = due
            await self._s.flush()

    async def remove_tasks_for_user_in_chat(self, user_id: int, chat_id: int) -> int:
        tasks = await self._s.scalars(
            select(Task).where(
                ((Task.user_id == user_id) | (Task.owner_id == user_id)),
                Task.chat_id == chat_id,
            )
        )
        count = 0
        for task in tasks.all():
            await self._s.delete(task)
            count += 1
        await self._s.flush()
        return count

    async def get_overdue_high_priority(self) -> list[Task]:
        today = datetime.now(tz=UTC).date()
        result = await self._s.scalars(
            select(Task).where(
                Task.done.is_(None),
                Task.priority == PRIORITY_HIGH,
                func.date(Task.due) < today,
            )
        )
        return list(result.all())

    async def get_user_stats(self, user_id: int) -> dict:
        owning = await self._s.scalars(select(Task).where(Task.owner_id == user_id))
        assigned = await self._s.scalars(select(Task).where(Task.user_id == user_id))
        return {
            "owning": self._compute_stats(list(owning.all())),
            "assigned": self._compute_stats(list(assigned.all())),
        }

    async def get_chat_stats(self, chat_id: int) -> dict:
        tasks = await self._s.scalars(select(Task).where(Task.chat_id == chat_id))
        return self._compute_stats(list(tasks.all()))

    async def get_all_stats(self) -> dict:
        tasks = await self._s.scalars(select(Task))
        return self._compute_stats(list(tasks.all()))

    async def get_period_stats(
        self, chat_id: int, date_from: datetime | None = None, date_to: datetime | None = None
    ) -> tuple[dict, dict]:
        query = select(Task).where(Task.chat_id == chat_id)
        created_q = query
        if date_from:
            created_q = created_q.where(Task.created > date_from)
        if date_to:
            created_q = created_q.where(Task.created <= date_to)
        created_tasks = list((await self._s.scalars(created_q)).all())

        done_q = query.where(Task.done.is_not(None))
        if date_from:
            done_q = done_q.where(Task.done > date_from)
        if date_to:
            done_q = done_q.where(Task.done <= date_to)
        done_tasks = list((await self._s.scalars(done_q)).all())

        return self._compute_stats(created_tasks), self._compute_stats(done_tasks)

    @staticmethod
    def _compute_stats(tasks: list[Task]) -> dict:
        today = datetime.now(tz=UTC).date()
        open_tasks = [t for t in tasks if t.done is None]
        done_tasks = [t for t in tasks if t.done is not None]

        open_on_time = sum(1 for t in open_tasks if t.due is None or t.due.date() >= today)
        open_late = sum(1 for t in open_tasks if t.due is not None and t.due.date() < today)

        done_on_time = sum(1 for t in done_tasks if t.due is None or t.done.date() <= t.due.date())  # type: ignore[union-attr]
        done_late = sum(1 for t in done_tasks if t.due is not None and t.done.date() > t.due.date())  # type: ignore[union-attr]
        done_pct = (100 * done_on_time / len(done_tasks)) if done_tasks else 0

        return {
            "count": len(tasks),
            "open": {"count": len(open_tasks), "onTime": open_on_time, "late": open_late},
            "done": {
                "count": len(done_tasks),
                "onTime": done_on_time,
                "late": done_late,
                "onTimePercent": done_pct,
            },
        }
