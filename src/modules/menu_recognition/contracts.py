from typing import Protocol


class RecognitionError(Exception):
    """An image could not be read by the configured OCR engine."""


class OcrUnavailable(RecognitionError):
    """The OCR executable or language data is unavailable."""


class ImageTextReader(Protocol):
    async def read(self, image: bytes) -> str: ...


class CleanupError(RecognitionError):
    """The LLM could not produce a validated list of beer names."""


class BeerNameCleaner(Protocol):
    async def clean(self, text: str) -> list[str]: ...
