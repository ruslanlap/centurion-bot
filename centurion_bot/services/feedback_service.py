from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import Feedback


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, user_id: int, text: str) -> Feedback:
        fb = Feedback(user_id=user_id, text=text)
        self._s.add(fb)
        await self._s.flush()
        return fb

    async def get(self, feedback_id: int) -> Feedback | None:
        return await self._s.get(Feedback, feedback_id)

    async def set_resolved(self, feedback_id: int) -> None:
        fb = await self._s.get(Feedback, feedback_id)
        if fb:
            fb.done = datetime.now(tz=UTC)
            await self._s.flush()

    async def get_all(self) -> list[Feedback]:
        result = await self._s.scalars(select(Feedback))
        return list(result.all())

    async def get_stats(self) -> dict[str, int]:
        all_fb = await self.get_all()
        return {"count": len(all_fb)}
