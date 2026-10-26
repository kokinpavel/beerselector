import json

import httpx
import pytest

from src.infrastructure.llm.ollama import OllamaBeerNameCleaner
from src.modules.menu_recognition.contracts import CleanupError


async def test_local_model_receives_schema_without_key_and_cleans_menu():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "items": [
                                {"name": "West Tripel", "source_lines": [2]},
                                {"name": "West Tripel", "source_lines": [2]},
                                {"name": "Rochefort 10", "source_lines": [3]},
                            ]
                        }
                    )
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        names = await OllamaBeerNameCleaner(client=client).clean(
            "BEER MENU\nWest Tripel 8.5% 500 руб\nRochefort 10 11.3%"
        )
    assert names == ["West Tripel", "Rochefort 10"]
    request = requests[0]
    assert str(request.url) == "http://ollama:11434/api/chat"
    assert "authorization" not in request.headers
    payload = json.loads(request.content)
    assert payload["stream"] is False
    assert payload["format"]["additionalProperties"] is False
    assert payload["model"] == "qwen2.5:3b"


@pytest.mark.parametrize(
    "body",
    [
        {"done": False},
        {"done": True, "done_reason": "length"},
        {"done": True, "message": {"content": "not json"}},
        {
            "done": True,
            "message": {"content": '{"items":[{"name":"Invented Beer","source_lines":[1]}]}'},
        },
        {"done": True, "message": {"content": '{"items":[{"name":"Beer 8%","source_lines":[1]}]}'}},
    ],
)
async def test_invalid_local_result_never_falls_back_to_raw_text(body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    ) as client:
        with pytest.raises(CleanupError):
            await OllamaBeerNameCleaner(client=client).clean("Beer 8%")


@pytest.mark.parametrize("status", [404, 500, 503])
async def test_local_service_or_model_unavailable_has_safe_error(status, caplog):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="private menu data")
        )
    ) as client:
        with pytest.raises(CleanupError):
            await OllamaBeerNameCleaner(client=client).clean("Beer")
    assert "private menu data" not in caplog.text


async def test_empty_text_needs_no_model():
    assert await OllamaBeerNameCleaner().clean(" ") == []
