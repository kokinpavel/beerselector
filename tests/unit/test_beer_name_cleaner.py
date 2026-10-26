import json

import httpx
import pytest

from src.infrastructure.llm.beer_names import OpenAIBeerNameCleaner
from src.modules.menu_recognition.contracts import CleanupError


def completed(items):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"items": items})}],
            }
        ],
    }


async def test_structured_extraction_keeps_only_names_deduplicates_and_does_not_send_images():
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=completed(
                [
                    {"name": "West Tripel", "source_lines": [2]},
                    {"name": "west tripel", "source_lines": [2]},
                    {"name": "Rochefort 10", "source_lines": [3]},
                ]
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cleaner = OpenAIBeerNameCleaner("test-key", client=client)
        names = await cleaner.clean("MENU\nWest Tripel 8.5% 500 руб\nRochefort 10 11.3%")
    assert names == ["West Tripel", "Rochefort 10"]
    payload = captured[0]
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"]["additionalProperties"] is False
    assert "2: West Tripel" in payload["input"]
    assert "test-key" not in json.dumps(payload)


@pytest.mark.parametrize(
    "item",
    [
        {"name": "Invented Tripel", "source_lines": [1]},
        {"name": "Beer 8%", "source_lines": [1]},
        {"name": "Beer", "source_lines": [999]},
        {"name": "Beer", "source_lines": [0]},
        {"name": "Beer", "source_lines": []},
        {"name": "Beer", "source_lines": [1], "extra": "data"},
    ],
)
async def test_unsupported_or_dirty_results_are_rejected(item):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completed([item])))
    ) as client:
        with pytest.raises(CleanupError):
            await OpenAIBeerNameCleaner("key", client=client).clean("Beer 8%")


@pytest.mark.parametrize(
    "body",
    [
        {"status": "incomplete", "output": []},
        {"status": "completed", "output": []},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}],
        },
        {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "not JSON"}]}
            ],
        },
    ],
)
async def test_bad_or_refused_responses_fail_without_raw_text_fallback(body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    ) as client:
        with pytest.raises(CleanupError):
            await OpenAIBeerNameCleaner("key", client=client).clean("Beer 8%")


async def test_missing_key_does_not_request_api():
    with pytest.raises(CleanupError, match="not configured"):
        await OpenAIBeerNameCleaner(None).clean("Beer")
    assert await OpenAIBeerNameCleaner(None).clean(" ") == []


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_api_errors_do_not_expose_response_body(status):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="private raw OCR or credentials")
        )
    ) as client:
        with pytest.raises(CleanupError) as failure:
            await OpenAIBeerNameCleaner("key", client=client).clean("Beer")
    assert "private" not in str(failure.value)


@pytest.mark.parametrize(
    "code", ["insufficient_quota", "credit_balance_exhausted", "rate_limit_exceeded"]
)
async def test_api_error_logs_safe_code_without_private_body(caplog, code):
    body = {
        "error": {
            "code": code,
            "type": "insufficient_quota",
            "message": "private-menu",
            "key": "secret-key",
        }
    }
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(429, json=body))
    ) as client:
        with pytest.raises(CleanupError):
            await OpenAIBeerNameCleaner("secret-key", client=client).clean("private-menu")
    assert f"code={code}" in caplog.text
    assert "private-menu" not in caplog.text
    assert "secret-key" not in caplog.text


async def test_unexpected_api_code_is_not_logged(caplog):
    body = {"error": {"code": "private-menu", "type": "secret-key"}}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(429, json=body))
    ) as client:
        with pytest.raises(CleanupError):
            await OpenAIBeerNameCleaner("key", client=client).clean("Beer")
    assert "code=unknown type=unknown" in caplog.text
    assert "private-menu" not in caplog.text
    assert "secret-key" not in caplog.text
