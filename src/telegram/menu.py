import io
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Document, Message, PhotoSize

from src.application.recognize_menu import MAX_IMAGE_BYTES, RecognizeMenu
from src.modules.menu_recognition.contracts import CleanupError, OcrUnavailable, RecognitionError
from src.modules.menu_recognition.menu import MenuDraft

logger = logging.getLogger(__name__)


class MenuState(StatesGroup):
    review = State()


async def show_draft(message: Message, draft: MenuDraft) -> None:
    await message.answer(
        f"Распознано позиций: {len(draft.items)}.\n"
        "/editmenu — исправить список, /menu — показать снова, /cancel — удалить.",
        parse_mode=None,
    )
    if not draft.items:
        await message.answer(
            "Не удалось выделить позиции. Пришли другое фото или введи список текстом."
        )
    chunk = ""
    for index, item in enumerate(draft.items, start=1):
        line = f"{index}. {item.text}\n"
        if len(chunk) + len(line) > 3000:
            await message.answer(chunk, parse_mode=None)
            chunk = ""
        chunk += line
    if chunk:
        await message.answer(chunk, parse_mode=None)
    if draft.truncated:
        await message.answer("Часть текста не поместилась. Отправь меню меньшими фрагментами.")


def create_menu_router(recognize: RecognizeMenu) -> Router:
    router = Router()
    router.message.filter(F.chat.type == "private")

    @router.message(Command("cancel"))
    async def cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Черновик удалён. Пришли фото нового меню.")

    @router.message(Command("menu"))
    async def menu(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        if "draft" not in data:
            await message.answer("Пришли фото пивного меню, чтобы распознать список.")
            return
        await show_draft(message, MenuDraft.model_validate(data["draft"]))

    @router.message(F.photo | F.document.mime_type.in_({"image/jpeg", "image/png", "image/webp"}))
    async def photo(message: Message, state: FSMContext, bot: Bot) -> None:
        largest: PhotoSize | Document
        if message.photo:
            largest = message.photo[-1]
        elif message.document:
            largest = message.document
        else:
            return
        if largest.file_size and largest.file_size > MAX_IMAGE_BYTES:
            await message.answer("Фото слишком большое. Пришли изображение до 10 МБ.")
            return
        await message.answer("Распознаю меню…")
        try:
            buffer = io.BytesIO()
            await bot.download(largest, destination=buffer, timeout=30)
            draft = await recognize.execute(buffer.getvalue(), message.caption or "")
        except CleanupError:
            logger.warning("Beer-name cleanup unavailable")
            await message.answer("Не удалось выделить названия пива. Попробуй позже.")
            return
        except OcrUnavailable:
            logger.error("Menu OCR unavailable: check Tesseract and configured languages")
            await message.answer(
                "Распознавание пока недоступно: нужен Tesseract с языками OCR. "
                "Можно ввести список текстом после /editmenu."
            )
            return
        except RecognitionError, TelegramAPIError, OSError, TimeoutError:
            logger.warning("Menu photo could not be processed")
            await message.answer(
                "Не удалось прочитать фото. Пришли более чёткий снимок как файл без сжатия или /editmenu."
            )
            return
        await state.set_state(None)
        await state.set_data({"draft": draft.model_dump()})
        await show_draft(message, draft)

    @router.message(Command("editmenu"))
    async def edit_menu(message: Message, state: FSMContext) -> None:
        await state.set_state(MenuState.review)
        await message.answer(
            "Пришли список целиком: одна позиция пива на строку. /cancel — отменить."
        )

    @router.message(MenuState.review, F.text, ~F.text.startswith("/"))
    async def correction(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        previous = MenuDraft.model_validate(data["draft"]) if "draft" in data else None
        try:
            draft = await recognize.clean_text(
                message.text or "", previous.caption if previous else ""
            )
        except CleanupError:
            await message.answer("Не удалось выделить названия пива. Попробуй позже.")
            return
        # Preserve the original OCR text separately from the corrected list.
        if previous:
            draft.raw_text = previous.raw_text
        await state.set_data({"draft": draft.model_dump()})
        await state.set_state(None)
        await show_draft(message, draft)

    return router
