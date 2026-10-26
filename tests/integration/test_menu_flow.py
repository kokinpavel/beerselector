from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import Chat, Document, Message, PhotoSize, Update, User

from src.application.recognize_menu import RecognizeMenu
from src.modules.menu_recognition.contracts import OcrUnavailable
from src.telegram.menu import create_menu_router


async def send(dispatcher, bot, text=None, photo=False, user=42, document=False):
    await dispatcher.feed_update(
        bot,
        Update(
            update_id=1,
            message=Message(
                message_id=1,
                date=datetime.now(UTC),
                chat=Chat(id=user, type="private"),
                from_user=User(id=user, is_bot=False, first_name="Test"),
                text=text,
                photo=[
                    PhotoSize(file_id="test-photo", file_unique_id="photo", width=800, height=600)
                ]
                if photo
                else None,
                caption="крепкое типа бельгия" if photo or document else None,
                document=Document(file_id="file", file_unique_id="file", mime_type="image/png")
                if document
                else None,
            ),
        ),
    )


def replies(bot):
    return [call.args[1].text for call in bot.session.call_args_list]


@pytest.mark.parametrize("as_document", [False, True])
async def test_photo_returns_list_without_confirmation_and_optional_editing(
    monkeypatch, as_document
):
    reader = SimpleNamespace(
        read=AsyncMock(return_value="BEER MENU\nWest Tripel 8.5%\nLocal IPA 6%")
    )
    cleaner = SimpleNamespace(
        clean=AsyncMock(
            side_effect=[["West Tripel", "Local IPA"], ["Corrected Tripel", "Unknown Beer"]]
        )
    )
    dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())
    dispatcher.include_router(create_menu_router(RecognizeMenu(reader, cleaner)))
    bot = Bot(token="123456:test-token", session=AsyncMock())

    async def download(file, destination, **kwargs):
        destination.write(b"synthetic-image")

    monkeypatch.setattr(bot, "download", download)
    key = StorageKey(bot_id=bot.id, chat_id=42, user_id=42)
    try:
        await send(dispatcher, bot, photo=not as_document, document=as_document)
        reader.read.assert_awaited_once_with(b"synthetic-image")
        data = await dispatcher.storage.get_data(key)
        assert data["draft"]["caption"] == "крепкое типа бельгия"
        assert "confirmed" not in data["draft"]
        assert await dispatcher.storage.get_state(key) is None
        assert all("/confirm" not in text for text in replies(bot))
        assert any("West Tripel" in text for text in replies(bot))
        assert not any("8.5%" in text or "BEER MENU" in text for text in replies(bot))
        await send(dispatcher, bot, "/menu", user=99)
        assert "Пришли фото" in replies(bot)[-1]
        await send(dispatcher, bot, "крепкое бельгийское")
        assert (await dispatcher.storage.get_data(key))["draft"] == data["draft"]
        await send(dispatcher, bot, "/editmenu")
        await send(dispatcher, bot, "Corrected Tripel 9%\nUnknown Beer")
        data = await dispatcher.storage.get_data(key)
        assert data["draft"]["raw_text"].startswith("BEER MENU")
        assert data["draft"]["items"][0]["text"] == "Corrected Tripel"
        assert data["draft"]["items"][0]["abv"] is None
        assert await dispatcher.storage.get_state(key) is None
        assert all("/confirm" not in text for text in replies(bot))
        await send(dispatcher, bot, "/cancel")
        assert await dispatcher.storage.get_data(key) == {}
    finally:
        await dispatcher.storage.close()
        await bot.session.close()


async def test_missing_ocr_allows_manual_entry(monkeypatch):
    reader = SimpleNamespace(read=AsyncMock(side_effect=OcrUnavailable()))
    cleaner = SimpleNamespace(clean=AsyncMock(return_value=["Beer"]))
    dispatcher = Dispatcher()
    dispatcher.include_router(create_menu_router(RecognizeMenu(reader, cleaner)))
    bot = Bot(token="123456:test-token", session=AsyncMock())

    async def download(file, destination, **kwargs):
        destination.write(b"image")

    monkeypatch.setattr(bot, "download", download)
    try:
        await send(dispatcher, bot, photo=True)
        assert "нужен Tesseract" in replies(bot)[-1]
        await send(dispatcher, bot, "/editmenu")
        await send(dispatcher, bot, "Beer 8%")
        assert any("Распознано позиций: 1" in text for text in replies(bot))
    finally:
        await dispatcher.storage.close()
        await bot.session.close()


async def test_blank_ocr_reports_empty_result_without_confirmation(monkeypatch):
    reader = SimpleNamespace(read=AsyncMock(return_value=""))
    cleaner = SimpleNamespace(clean=AsyncMock(return_value=[]))
    dispatcher = Dispatcher()
    dispatcher.include_router(create_menu_router(RecognizeMenu(reader, cleaner)))
    bot = Bot(token="123456:test-token", session=AsyncMock())

    async def download(file, destination, **kwargs):
        destination.write(b"image")

    monkeypatch.setattr(bot, "download", download)
    try:
        await send(dispatcher, bot, photo=True)
        assert "Не удалось выделить" in replies(bot)[-1]
        assert all("/confirm" not in text for text in replies(bot))
    finally:
        await dispatcher.storage.close()
        await bot.session.close()


async def test_llm_failure_never_sends_raw_ocr(monkeypatch):
    from src.modules.menu_recognition.contracts import CleanupError

    reader = SimpleNamespace(read=AsyncMock(return_value="SECRET RAW MENU 500 руб 8%"))
    cleaner = SimpleNamespace(clean=AsyncMock(side_effect=CleanupError()))
    dispatcher = Dispatcher()
    dispatcher.include_router(create_menu_router(RecognizeMenu(reader, cleaner)))
    bot = Bot(token="123456:test-token", session=AsyncMock())

    async def download(file, destination, **kwargs):
        destination.write(b"image")

    monkeypatch.setattr(bot, "download", download)
    try:
        await send(dispatcher, bot, photo=True)
        assert "Не удалось выделить названия" in replies(bot)[-1]
        assert all("SECRET" not in text and "500" not in text for text in replies(bot))
    finally:
        await dispatcher.storage.close()
        await bot.session.close()
