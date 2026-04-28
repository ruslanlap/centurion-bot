import structlog
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from centurion_bot.config import settings
from centurion_bot.db.session import async_session_factory

log = structlog.get_logger()


async def _daily_job(bot: Bot) -> None:
    from centurion_bot.handlers.task import job_daily_tasks

    async with async_session_factory() as session:
        await job_daily_tasks(bot, session)
        await session.commit()


async def _weekly_job(bot: Bot) -> None:
    from centurion_bot.handlers.task import job_weekly_review

    async with async_session_factory() as session:
        await job_weekly_review(bot, session)
        await session.commit()


async def _recurring_job(bot: Bot) -> None:
    from centurion_bot import texts
    from centurion_bot.services.recurring_service import RecurringService

    async with async_session_factory() as session:
        svc = RecurringService(session)
        generated = await svc.generate_due_tasks()
        await session.commit()

        for task in generated:
            try:
                due_str = task.due.date() if task.due else "no date"
                await bot.send_message(
                    task.chat_id,
                    texts.RECURRING_GENERATED.format(title=task.title, due=due_str),
                    parse_mode="HTML",
                )
            except Exception:
                log.warning("recurring_notify_failed", chat_id=task.chat_id, exc_info=True)


async def _escalation_job(bot: Bot) -> None:
    from centurion_bot import texts
    from centurion_bot.services.task_service import TaskService

    async with async_session_factory() as session:
        svc = TaskService(session)
        overdue = await svc.get_overdue_high_priority()

        for task in overdue:
            try:
                assignee_name = "anyone" if task.is_group_task else str(task.user_id)
                due_str = task.due.date() if task.due else "—"
                msg = texts.ESCALATION_ALERT.format(
                    title=task.title,
                    user_name=assignee_name,
                    owner_name=str(task.owner_id),
                    due=due_str,
                )
                # Notify the group
                await bot.send_message(task.chat_id, msg, parse_mode="HTML")
                # Notify admin
                if settings.admin_id:
                    await bot.send_message(settings.admin_id, msg, parse_mode="HTML")
            except Exception:
                log.warning("escalation_notify_failed", task_id=task.id, exc_info=True)


async def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _daily_job,
        CronTrigger(hour=settings.daily_reminder_hour, minute=settings.daily_reminder_minute),
        args=[bot],
        id="daily_tasks",
        replace_existing=True,
    )
    scheduler.add_job(
        _weekly_job,
        CronTrigger(
            day_of_week=settings.weekly_review_weekday,
            hour=settings.weekly_review_hour,
            minute=settings.weekly_review_minute,
        ),
        args=[bot],
        id="weekly_review",
        replace_existing=True,
    )
    # Recurring task generation — runs every hour
    scheduler.add_job(
        _recurring_job,
        CronTrigger(minute=0),
        args=[bot],
        id="recurring_tasks",
        replace_existing=True,
    )
    # Escalation check — runs twice daily
    scheduler.add_job(
        _escalation_job,
        CronTrigger(hour="9,15", minute=0),
        args=[bot],
        id="escalation_check",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
