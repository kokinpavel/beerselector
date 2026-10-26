from src.modules.menu_recognition.contracts import (
    BeerNameCleaner,
    ImageTextReader,
    RecognitionError,
)
from src.modules.menu_recognition.menu import MAX_TEXT_LENGTH, MenuDraft, MenuItem

MAX_IMAGE_BYTES = 10 * 1024 * 1024


class RecognizeMenu:
    def __init__(self, reader: ImageTextReader, cleaner: BeerNameCleaner) -> None:
        self.reader = reader
        self.cleaner = cleaner

    async def clean_text(self, text: str, caption: str = "") -> MenuDraft:
        raw = text[:MAX_TEXT_LENGTH]
        names = await self.cleaner.clean(raw)
        return MenuDraft(
            raw_text=raw,
            caption=caption[:1024],
            items=[MenuItem(text=name) for name in names],
            truncated=len(text) > MAX_TEXT_LENGTH,
        )

    async def execute(self, image: bytes, caption: str = "") -> MenuDraft:
        if not image or len(image) > MAX_IMAGE_BYTES:
            raise RecognitionError("Expected a nonempty image of at most 10 MB")
        return await self.clean_text(await self.reader.read(image), caption)
