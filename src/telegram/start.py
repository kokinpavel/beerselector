import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.exc import SQLAlchemyError

from src.application.start import StartUser

logger = logging.getLogger(__name__)


def create_start_router(start_user: StartUser) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        if message.from_user is None:
            return
        try:
            await start_user.execute(message.from_user.id)
        except SQLAlchemyError:
            logger.error("User registration failed")
            await message.answer("Не удалось запустить бота. Попробуйте /start ещё раз чуть позже.")
            return
        await message.answer(
            "Привет! Твой профиль сохранён.\nУкажи свой Untappd: /untappd username"
        )

    return router
