from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import CheckIn


class CheckInService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(
        self,
        user_id: int,
        chat_id: int,
        done_text: str = "",
        plan_text: str = "",
        blockers_text: str = "",
    ) -> CheckIn:
        ci = CheckIn(
            user_id=user_id,
            chat_id=chat_id,
            done_text=done_text,
            plan_text=plan_text,
            blockers_text=blockers_text,
        )
        self._s.add(ci)
        await self._s.flush()
        return ci

    async def get_today(self, chat_id: int) -> list[CheckIn]:
        today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self._s.scalars(
            select(CheckIn).where(
                CheckIn.chat_id == chat_id,
                CheckIn.created_at >= today_start,
            ).order_by(CheckIn.created_at)
        )
        return list(result.all())

    async def get_for_period(
        self, chat_id: int, date_from: datetime, date_to: datetime
    ) -> list[CheckIn]:
        result = await self._s.scalars(
            select(CheckIn).where(
                CheckIn.chat_id == chat_id,
                CheckIn.created_at >= date_from,
                CheckIn.created_at <= date_to,
            ).order_by(CheckIn.created_at)
        )
        return list(result.all())

    async def get_user_streak(self, user_id: int, chat_id: int) -> int:
        """Count consecutive days with check-ins ending today."""
        today = datetime.now(tz=UTC).date()
        streak = 0
        day = today
        while True:
            day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=UTC)
            day_end = day_start + timedelta(days=1)
            count = await self._s.scalar(
                select(func.count(CheckIn.id)).where(
                    CheckIn.user_id == user_id,
                    CheckIn.chat_id == chat_id,
                    CheckIn.created_at >= day_start,
                    CheckIn.created_at < day_end,
                )
            )
            if count and count > 0:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    async def get_today_user_ids(self, chat_id: int) -> set[int]:
        today_start = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self._s.scalars(
            select(CheckIn.user_id).where(
                CheckIn.chat_id == chat_id,
                CheckIn.created_at >= today_start,
            ).distinct()
        )
        return set(result.all())

    async def get_stats(self, chat_id: int, days: int = 7) -> dict:
        now = datetime.now(tz=UTC)
        start = now - timedelta(days=days)
        checkins = await self.get_for_period(chat_id, start, now)
        unique_users = len({c.user_id for c in checkins})
        total = len(checkins)
        blockers = sum(1 for c in checkins if c.blockers_text.strip())
        return {
            "total_checkins": total,
            "unique_users": unique_users,
            "with_blockers": blockers,
            "days": days,
        }
