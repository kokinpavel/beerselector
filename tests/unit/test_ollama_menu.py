import base64

import httpx
import pytest

from src.infrastructure.llm.menu import OllamaMenuRecognizer
from src.modules.menu_recognition.contracts import RecognitionError
from src.modules.menu_recognition.menu import MAX_IMAGE_BYTES


async def test_image_uses_single_service_and_preserves_caption():
    async def handle(request):
        import json

        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["model"] == "qwen3-vl:4b-instruct"
        assert payload["messages"][1]["images"] == [base64.b64encode(b"photo").decode()]
        assert "caption" not in request.content.decode()
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"content": '{"names":["Guinness", "Guinness"],"truncated":false}'},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        draft = await OllamaMenuRecognizer(client=client).execute(b"photo", "caption")
    assert [item.text for item in draft.items] == ["Guinness"]
    assert draft.caption == "caption"


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        '{"names":[""],"truncated":false}',
        '{"names":["Beer"]}',
        '{"names":["Beer"],"truncated":"false"}',
    ],
)
async def test_invalid_result_is_not_exposed(output):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"done": True, "done_reason": "stop", "message": {"content": output}}
            )
        )
    ) as client:
        with pytest.raises(RecognitionError):
            await OllamaMenuRecognizer(client=client).execute(b"photo")


async def test_unavailable_service_is_translated():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    ) as client:
        with pytest.raises(RecognitionError):
            await OllamaMenuRecognizer(client=client).clean_text("Beer")


@pytest.mark.parametrize("image", [b"", b"x" * (MAX_IMAGE_BYTES + 1)])
async def test_invalid_image_size_is_rejected_before_calling_model(image):
    recognizer = OllamaMenuRecognizer()
    with pytest.raises(RecognitionError):
        await recognizer.execute(image)


async def test_empty_text_skips_model():
    assert not (await OllamaMenuRecognizer().clean_text(" ")).items


async def test_text_is_bounded_and_truncation_is_preserved():
    import json

    async def handle(request):
        assert json.loads(request.content)["messages"][1]["content"].endswith("A" * 20_000)
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"content": '{"names":["Beer"],"truncated":false}'},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        draft = await OllamaMenuRecognizer(client=client).clean_text("A" * 20_001)
    assert draft.truncated
    assert len(draft.raw_text) == 20_000


@pytest.mark.parametrize(
    "body",
    [
        {"done": False, "done_reason": "stop"},
        {"done": True, "done_reason": "length"},
        [],
        {"done": True, "done_reason": "stop", "message": {}},
    ],
)
async def test_incomplete_or_malformed_response_is_rejected(body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    ) as client:
        with pytest.raises(RecognitionError):
            await OllamaMenuRecognizer(client=client).clean_text("Beer")
