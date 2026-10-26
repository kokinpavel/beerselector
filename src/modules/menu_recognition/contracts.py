from typing import Protocol

from src.modules.menu_recognition.menu import MenuDraft


class RecognitionError(Exception):
    """The menu could not be recognized or the model response is invalid."""


class MenuRecognizer(Protocol):
    async def execute(self, image: bytes, caption: str = "") -> MenuDraft: ...

    async def clean_text(self, text: str, caption: str = "") -> MenuDraft: ...
