import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.exc import SQLAlchemyError

from src.application.untappd import ManageUntappdProfile
from src.modules.users.untappd import UntappdProfile

logger = logging.getLogger(__name__)
INSTRUCTIONS = (
    "Укажи свой профиль: /untappd username\nИли отправь /untappd https://untappd.com/user/username"
)


def create_untappd_router(profiles: ManageUntappdProfile) -> Router:
    router = Router()

    @router.message(Command("untappd"))
    async def untappd(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        if message.chat.type != "private":
            await message.answer("Укажи профиль Untappd в личном чате с ботом.")
            return
        profile: UntappdProfile | None
        try:
            if command.args:
                profile = await profiles.link(message.from_user.id, command.args)
            else:
                profile = await profiles.get(message.from_user.id)
        except ValueError:
            await message.answer("Не удалось разобрать имя или ссылку.\n" + INSTRUCTIONS)
            return
        except SQLAlchemyError, OSError:
            logger.error("Untappd profile persistence failed")
            await message.answer("Не удалось сохранить или загрузить профиль. Попробуй позже.")
            return
        if profile is None:
            await message.answer(INSTRUCTIONS)
            return
        await message.answer(
            f"Указанный профиль Untappd: {profile.url}\n"
            "Импорт истории оценок пока недоступен.\n"
            "Для смены профиля: /untappd другой_username"
        )

    return router
