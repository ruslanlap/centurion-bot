from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from centurion_bot.db.models import Chat, User, UserChat


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_user(self, user_id: int, first_name: str = "", username: str = "") -> bool:
        existing = await self._s.scalar(select(User).where(User.user_id == user_id))
        if existing:
            if first_name:
                existing.first_name = first_name
            if username:
                existing.username = username
            return False
        self._s.add(User(user_id=user_id, first_name=first_name, username=username))
        await self._s.flush()
        return True

    async def upsert_chat(self, chat_id: int, title: str = "") -> bool:
        existing = await self._s.scalar(select(Chat).where(Chat.chat_id == chat_id))
        if existing:
            if title:
                existing.title = title
            return False
        self._s.add(Chat(chat_id=chat_id, title=title))
        await self._s.flush()
        return True

    async def add_user_chat(self, user_id: int, chat_id: int) -> bool:
        existing = await self._s.scalar(
            select(UserChat).where(UserChat.user_id == user_id, UserChat.chat_id == chat_id)
        )
        if existing:
            return False
        self._s.add(UserChat(user_id=user_id, chat_id=chat_id))
        await self._s.flush()
        return True

    async def remove_user_chat(self, user_id: int, chat_id: int) -> bool:
        result = await self._s.execute(
            delete(UserChat).where(UserChat.user_id == user_id, UserChat.chat_id == chat_id)
        )
        return result.rowcount > 0  # type: ignore[union-attr]

    async def remove_chat(self, chat_id: int) -> bool:
        await self._s.execute(delete(UserChat).where(UserChat.chat_id == chat_id))
        result = await self._s.execute(delete(Chat).where(Chat.chat_id == chat_id))
        return result.rowcount > 0  # type: ignore[union-attr]

    async def get_chat_user_ids(self, chat_id: int) -> list[int]:
        rows = await self._s.scalars(select(UserChat.user_id).where(UserChat.chat_id == chat_id))
        return list(rows.all())

    async def get_user_chat_ids(self, user_id: int) -> list[int]:
        rows = await self._s.scalars(select(UserChat.chat_id).where(UserChat.user_id == user_id))
        return list(rows.all())

    async def get_all_user_ids(self) -> list[int]:
        rows = await self._s.scalars(select(UserChat.user_id).distinct())
        return list(rows.all())

    async def get_all_chat_ids(self) -> list[int]:
        rows = await self._s.scalars(select(UserChat.chat_id).distinct())
        return list(rows.all())

    async def get_user(self, user_id: int) -> User | None:
        return await self._s.scalar(select(User).where(User.user_id == user_id))

    async def count_chat_users(self, chat_id: int) -> int:
        rows = await self._s.scalars(select(UserChat.user_id).where(UserChat.chat_id == chat_id))
        return len(rows.all())

    async def get_stats(self) -> dict[str, int]:
        user_ids = await self.get_all_user_ids()
        chat_ids = await self.get_all_chat_ids()
        return {"num_users": len(set(user_ids)), "num_chats": len(set(chat_ids))}

    async def report_user_send_failure(self, user_id: int, error_msg: str) -> None:
        user = await self._s.scalar(select(User).where(User.user_id == user_id))
        if not user:
            self._s.add(
                User(user_id=user_id, is_active=False, error_message=error_msg, last_error_at=datetime.now(tz=UTC))
            )
        else:
            user.is_active = False
            user.error_message = error_msg
            user.last_error_at = datetime.now(tz=UTC)
        await self._s.flush()

    async def report_chat_send_failure(self, chat_id: int, error_msg: str) -> None:
        chat = await self._s.scalar(select(Chat).where(Chat.chat_id == chat_id))
        if not chat:
            self._s.add(
                Chat(chat_id=chat_id, is_active=False, error_message=error_msg, last_error_at=datetime.now(tz=UTC))
            )
        else:
            chat.is_active = False
            chat.error_message = error_msg
            chat.last_error_at = datetime.now(tz=UTC)
        await self._s.flush()
