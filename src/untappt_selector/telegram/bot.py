import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from untappt_selector.core.config import get_settings

async def main():
    token = get_settings().telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start polling")
    bot = Bot(token=token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer("UntapptSelector готов к работе. Распознавание меню скоро появится.")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
