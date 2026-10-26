import asyncio
import logging

import httpx
from pydantic import ValidationError

from src.modules.menu_recognition.beer_names import INSTRUCTIONS, ExtractedNames, validate_names
from src.modules.menu_recognition.contracts import CleanupError

logger = logging.getLogger(__name__)


class OllamaBeerNameCleaner:
    def __init__(
        self,
        base_url: str = "http://ollama:11434",
        model: str = "qwen2.5:3b",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = client
        self._slots = asyncio.Semaphore(1)

    async def clean(self, text: str) -> list[str]:
        if not text.strip():
            return []
        async with self._slots:
            try:
                async with asyncio.timeout(180):
                    return await self._clean(text)
            except TimeoutError as exc:
                logger.warning("Local LLM cleanup timed out")
                raise CleanupError("Local LLM timed out") from exc

    async def _clean(self, text: str) -> list[str]:
        lines = text.splitlines()
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": INSTRUCTIONS + "\nReturn JSON matching the provided schema.",
                },
                {
                    "role": "user",
                    "content": "OCR menu lines:\n"
                    + "\n".join(f"{index}: {line}" for index, line in enumerate(lines, start=1)),
                },
            ],
            "stream": False,
            "format": ExtractedNames.model_json_schema(),
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 4000},
        }
        try:
            if self.client is not None:
                response = await self.client.post(
                    f"{self.base_url}/api/chat", json=payload, timeout=180
                )
            else:
                async with httpx.AsyncClient(timeout=180) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
            if response.is_error:
                logger.warning("Local LLM HTTP error: status=%s", response.status_code)
            response.raise_for_status()
            body = response.json()
            if body.get("done") is not True or body.get("done_reason") == "length":
                raise CleanupError("Local LLM response is incomplete")
            result = ExtractedNames.model_validate_json(body["message"]["content"])
            return validate_names(result, lines)
        except (
            httpx.HTTPError,
            ValidationError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as exc:
            logger.warning("Local LLM returned an unavailable or invalid result")
            raise CleanupError("Could not extract beer names locally") from exc
