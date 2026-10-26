import logging

import httpx
from pydantic import ValidationError

from src.modules.menu_recognition.beer_names import INSTRUCTIONS, ExtractedNames, validate_names
from src.modules.menu_recognition.contracts import CleanupError

logger = logging.getLogger(__name__)
SAFE_ERROR_CODES = {
    "rate_limit_exceeded",
    "slow_down",
    "insufficient_quota",
    "credit_balance_exhausted",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
    "invalid_api_key",
    "model_not_found",
    "invalid_request_error",
    "rate_limit_error",
    "server_error",
}


def log_api_error(response: httpx.Response) -> None:
    try:
        body = response.json()
        error = body.get("error", {}) if isinstance(body, dict) else {}
        if not isinstance(error, dict):
            error = {}
    except ValueError:
        error = {}
    code = error.get("code")
    kind = error.get("type")
    logger.warning(
        "OpenAI API error: status=%s code=%s type=%s",
        response.status_code,
        code if isinstance(code, str) and code in SAFE_ERROR_CODES else "unknown",
        kind if isinstance(kind, str) and kind in SAFE_ERROR_CODES else "unknown",
    )


class OpenAIBeerNameCleaner:
    def __init__(
        self,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.client = client

    async def clean(self, text: str) -> list[str]:
        if not text.strip():
            return []
        if not self.api_key:
            raise CleanupError("LLM API key is not configured")
        lines = text.splitlines()
        payload = {
            "model": self.model,
            "instructions": INSTRUCTIONS,
            "input": "OCR menu lines:\n"
            + "\n".join(f"{i}: {line}" for i, line in enumerate(lines, start=1)),
            "store": False,
            "max_output_tokens": 4000,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "beer_names",
                    "strict": True,
                    "schema": ExtractedNames.model_json_schema(),
                }
            },
        }
        try:
            if self.client is not None:
                response = await self.client.post(
                    "https://api.openai.com/v1/responses",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=35,
                )
            else:
                async with httpx.AsyncClient(timeout=35) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/responses",
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
            if response.is_error:
                log_api_error(response)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise CleanupError("Invalid LLM response")
            if body.get("status") != "completed":
                raise CleanupError("LLM response is incomplete")
            contents = [
                content
                for output in body.get("output", [])
                if output.get("type") == "message"
                for content in output.get("content", [])
            ]
            if any(content.get("type") == "refusal" for content in contents):
                raise CleanupError("LLM declined extraction")
            outputs = [
                content["text"] for content in contents if content.get("type") == "output_text"
            ]
            if len(outputs) != 1:
                raise CleanupError("Missing structured LLM result")
            extracted = ExtractedNames.model_validate_json(outputs[0])
            return validate_names(extracted, lines)
        except (
            httpx.HTTPError,
            ValidationError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as exc:
            # Never include the response body, authorization header or OCR text in errors/logs.
            raise CleanupError("Could not extract beer names") from exc
