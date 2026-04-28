import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from centurion_bot.config import settings
from centurion_bot.db.session import init_db
from centurion_bot.handlers import get_main_router
from centurion_bot.middlewares.db import DbSessionMiddleware
from centurion_bot.scheduler import setup_scheduler


def _configure_logging() -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
    )


async def _on_startup(bot: Bot) -> None:
    await init_db()
    structlog.get_logger().info("database_initialised")
    if settings.webhook_url:
        await bot.set_webhook(
            url=f"{settings.webhook_url}/webhook",
            secret_token=settings.webhook_secret or None,
        )


async def _on_shutdown(bot: Bot) -> None:
    if settings.webhook_url:
        await bot.delete_webhook()


def _build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(get_main_router())
    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)
    return dp


async def _run_polling() -> None:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _build_dispatcher()
    scheduler = await setup_scheduler(bot)
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"],
        )
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


def _run_webhook() -> None:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = _build_dispatcher()

    app = web.Application()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.webhook_secret or None)
    handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    web.run_app(app, host=settings.webhook_host, port=settings.webhook_port)


def main() -> None:
    _configure_logging()

    if settings.webhook_url:
        _run_webhook()
    else:
        asyncio.run(_run_polling())


if __name__ == "__main__":
    main()
