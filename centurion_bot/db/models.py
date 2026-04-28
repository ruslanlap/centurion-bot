from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from centurion_bot.db.base import Base

# Priority constants
PRIORITY_LOW = 0
PRIORITY_MEDIUM = 1
PRIORITY_HIGH = 2

PRIORITY_LABELS = {PRIORITY_LOW: "low", PRIORITY_MEDIUM: "medium", PRIORITY_HIGH: "high"}
PRIORITY_EMOJI = {PRIORITY_LOW: "🟢", PRIORITY_MEDIUM: "🟡", PRIORITY_HIGH: "🔴"}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    chats: Mapped[list["UserChat"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list["UserChat"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class UserChat(Base):
    __tablename__ = "user_chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), index=True)

    user: Mapped["User"] = relationship(back_populates="chats")
    chat: Mapped["Chat"] = relationship(back_populates="users")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    is_group_task: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=PRIORITY_MEDIUM)
    created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recurring_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recurring_tasks.id"), nullable=True)


class RecurringTask(Base):
    __tablename__ = "recurring_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, default=0)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    is_group_task: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=PRIORITY_MEDIUM)
    # Cron-like schedule: "daily", "weekly", "monthly", or cron expression
    schedule: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_generated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # How many days before the schedule to set the due date
    due_in_days: Mapped[int] = mapped_column(Integer, default=1)


class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    done_text: Mapped[str] = mapped_column(Text, default="")
    plan_text: Mapped[str] = mapped_column(Text, default="")
    blockers_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    done: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
