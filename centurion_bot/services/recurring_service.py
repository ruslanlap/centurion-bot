from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import RecurringTask, Task


class RecurringService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        chat_id: int,
        owner_id: int,
        title: str,
        schedule: str,
        user_id: int = 0,
        description: str = "",
        is_group_task: bool = False,
        priority: int = 1,
        due_in_days: int = 1,
    ) -> RecurringTask:
        rt = RecurringTask(
            chat_id=chat_id,
            owner_id=owner_id,
            user_id=user_id,
            title=title,
            description=description,
            is_group_task=is_group_task,
            priority=priority,
            schedule=schedule,
            due_in_days=due_in_days,
        )
        self._s.add(rt)
        await self._s.flush()
        return rt

    async def get(self, recurring_id: int) -> RecurringTask | None:
        return await self._s.get(RecurringTask, recurring_id)

    async def get_active(self) -> list[RecurringTask]:
        result = await self._s.scalars(
            select(RecurringTask).where(RecurringTask.is_active.is_(True))
        )
        return list(result.all())

    async def get_for_chat(self, chat_id: int) -> list[RecurringTask]:
        result = await self._s.scalars(
            select(RecurringTask).where(
                RecurringTask.chat_id == chat_id,
                RecurringTask.is_active.is_(True),
            )
        )
        return list(result.all())

    async def deactivate(self, recurring_id: int) -> bool:
        rt = await self._s.get(RecurringTask, recurring_id)
        if not rt or not rt.is_active:
            return False
        rt.is_active = False
        await self._s.flush()
        return True

    async def generate_due_tasks(self) -> list[Task]:
        """Check all active recurring tasks and generate new tasks if due."""
        now = datetime.now(tz=UTC)
        active = await self.get_active()
        generated: list[Task] = []

        for rt in active:
            if self._should_generate(rt, now):
                due = now + timedelta(days=rt.due_in_days)
                task = Task(
                    user_id=rt.user_id,
                    chat_id=rt.chat_id,
                    owner_id=rt.owner_id,
                    title=rt.title,
                    description=rt.description,
                    is_group_task=rt.is_group_task,
                    priority=rt.priority,
                    due=due,
                    recurring_id=rt.id,
                )
                self._s.add(task)
                rt.last_generated = now
                generated.append(task)

        if generated:
            await self._s.flush()
        return generated

    @staticmethod
    def _should_generate(rt: RecurringTask, now: datetime) -> bool:
        if rt.last_generated is None:
            return True

        last = rt.last_generated
        schedule = rt.schedule.lower().strip()

        if schedule == "daily":
            return (now - last).days >= 1
        if schedule == "weekly":
            return (now - last).days >= 7
        if schedule == "monthly":
            return (now.year, now.month) != (last.year, last.month)
        if schedule.startswith("every_"):
            try:
                n = int(schedule.split("_")[1])
                return (now - last).days >= n
            except (IndexError, ValueError):
                pass

        return False
