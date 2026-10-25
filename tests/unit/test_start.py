from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from src.application.start import StartUser
from src.telegram.start import create_start_router


async def test_start_passes_telegram_identity_to_repository():
    user_id = uuid4()
    users = SimpleNamespace(get_or_create=AsyncMock(return_value=user_id))
    assert await StartUser(users).execute(123456789012) == user_id
    users.get_or_create.assert_awaited_once_with(123456789012)


async def test_start_rejects_invalid_identity():
    users = SimpleNamespace(get_or_create=AsyncMock())
    with pytest.raises(ValueError):
        await StartUser(users).execute(0)
    users.get_or_create.assert_not_awaited()


async def test_handler_registers_sender_instead_of_chat():
    service = SimpleNamespace(execute=AsyncMock())
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42), chat=SimpleNamespace(id=-100), answer=AsyncMock()
    )
    router = create_start_router(service)
    await router.message.handlers[0].callback(message)
    service.execute.assert_awaited_once_with(42)
    assert "профиль сохранён" in message.answer.call_args.args[0]


async def test_handler_does_not_claim_success_when_database_unavailable():
    service = SimpleNamespace(execute=AsyncMock(side_effect=OperationalError("", {}, Exception())))
    message = SimpleNamespace(from_user=SimpleNamespace(id=42), answer=AsyncMock())
    router = create_start_router(service)
    await router.message.handlers[0].callback(message)
    assert "Попробуйте /start" in message.answer.call_args.args[0]


async def test_handler_ignores_messages_without_sender():
    service = SimpleNamespace(execute=AsyncMock())
    message = SimpleNamespace(from_user=None, answer=AsyncMock())
    router = create_start_router(service)
    await router.message.handlers[0].callback(message)
    service.execute.assert_not_awaited()
    message.answer.assert_not_awaited()
