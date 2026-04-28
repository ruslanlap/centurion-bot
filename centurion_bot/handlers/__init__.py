from aiogram import Router

from centurion_bot.handlers.admin import router as admin_router
from centurion_bot.handlers.checkin import router as checkin_router
from centurion_bot.handlers.common import router as common_router
from centurion_bot.handlers.feedback import router as feedback_router
from centurion_bot.handlers.recurring import router as recurring_router
from centurion_bot.handlers.task import router as task_router
from centurion_bot.handlers.user import router as user_router


def get_main_router() -> Router:
    router = Router(name="main")
    router.include_router(common_router)
    router.include_router(task_router)
    router.include_router(recurring_router)
    router.include_router(checkin_router)
    router.include_router(feedback_router)
    router.include_router(admin_router)
    router.include_router(user_router)  # user router last — catches all text messages
    return router
