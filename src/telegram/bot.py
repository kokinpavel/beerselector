import asyncio

from aiogram import Bot, Dispatcher

from src.application.start import StartUser
from src.application.untappd import ManageUntappdProfile
from src.core.config import get_settings
from src.infrastructure.database.external_accounts import (
    PostgresExternalAccountRepository,
)
from src.infrastructure.database.session import SessionLocal, engine
from src.infrastructure.database.users import PostgresUserRepository
from src.telegram.start import create_start_router
from src.telegram.untappd import create_untappd_router


async def main() -> None:
    token = get_settings().telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start polling")
    bot = Bot(token=token)
    dp = Dispatcher()

    start_user = StartUser(PostgresUserRepository(SessionLocal))
    dp.include_router(create_start_router(start_user))
    dp.include_router(
        create_untappd_router(
            ManageUntappdProfile(start_user, PostgresExternalAccountRepository(SessionLocal))
        )
    )

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
