import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation

from src.application.recognize_menu import RecognizeMenu
from src.application.start import StartUser
from src.application.untappd import ManageUntappdProfile
from src.core.config import get_settings
from src.infrastructure.database.external_accounts import (
    PostgresExternalAccountRepository,
)
from src.infrastructure.database.session import SessionLocal, engine
from src.infrastructure.database.users import PostgresUserRepository
from src.infrastructure.llm.ollama import OllamaBeerNameCleaner
from src.infrastructure.ocr.tesseract import TesseractReader
from src.telegram.menu import create_menu_router
from src.telegram.start import create_start_router
from src.telegram.untappd import create_untappd_router


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start polling")
    bot = Bot(token=token)
    dp = Dispatcher(events_isolation=SimpleEventIsolation())

    start_user = StartUser(PostgresUserRepository(SessionLocal))
    dp.include_router(create_start_router(start_user))
    dp.include_router(
        create_untappd_router(
            ManageUntappdProfile(start_user, PostgresExternalAccountRepository(SessionLocal))
        )
    )
    dp.include_router(
        create_menu_router(
            RecognizeMenu(
                TesseractReader(
                    executable=settings.ocr_executable,
                    languages=settings.ocr_languages,
                    page_segmentation=settings.ocr_page_segmentation,
                ),
                OllamaBeerNameCleaner(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                ),
            )
        )
    )

    try:
        logging.getLogger(__name__).info(
            "Starting Telegram polling; OCR languages=%s", settings.ocr_languages
        )
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
