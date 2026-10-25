import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Chat, Message, Update
from aiogram.types import User as TelegramUser
from alembic.config import Config
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from src.application.start import StartUser
from src.application.untappd import ManageUntappdProfile
from src.core.config import get_settings
from src.infrastructure.database.external_accounts import (
    PostgresExternalAccountRepository,
)
from src.infrastructure.database.users import PostgresUserRepository
from src.modules.users.models import ExternalAccount, User
from src.modules.users.untappd import UntappdProfile
from src.telegram.start import create_start_router
from src.telegram.untappd import create_untappd_router

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL must point to a disposable PostgreSQL database",
)


@pytest.fixture
def database_url(monkeypatch):
    url = os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
        yield url
    finally:
        get_settings.cache_clear()


async def test_start_persists_user_and_handles_concurrent_repeats(database_url):
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = StartUser(PostgresUserRepository(sessions))
    telegram_id = uuid4().int % (2**50) + 1
    other_id = telegram_id + 1
    try:
        user_ids = await asyncio.gather(*(service.execute(telegram_id) for _ in range(5)))
        assert isinstance(user_ids[0], UUID)
        assert len(set(user_ids)) == 1
        assert await service.execute(telegram_id) == user_ids[0]
        assert await service.execute(other_id) != user_ids[0]
        async with sessions() as session:
            users = (
                await session.scalars(select(User).where(User.telegram_id == telegram_id))
            ).all()
            assert len(users) == 1
            assert users[0].created_at.tzinfo is not None
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.telegram_id.in_([telegram_id, other_id])))
        await engine.dispose()


async def test_untappd_links_are_persistent_idempotent_and_isolated(database_url):
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    accounts = PostgresExternalAccountRepository(sessions)
    start = StartUser(PostgresUserRepository(sessions))
    profiles = ManageUntappdProfile(start, accounts)
    telegram_id = uuid4().int % (2**50) + 1
    other_id = telegram_id + 1
    try:
        assert await profiles.get(telegram_id) is None
        await asyncio.gather(*(profiles.link(telegram_id, "Beer_Fan") for _ in range(5)))
        user_id = await start.execute(telegram_id)
        async with sessions() as session:
            rows = (
                await session.scalars(
                    select(ExternalAccount).where(ExternalAccount.user_id == user_id)
                )
            ).all()
            assert len(rows) == 1
            original_id = rows[0].id
            assert not rows[0].is_verified
        # Same public username is allowed for another user: ownership is not verified.
        await profiles.link(other_id, "Beer_Fan")
        await profiles.link(telegram_id, "https://untappd.com/user/Other_Beer/")
        fresh_service = ManageUntappdProfile(start, PostgresExternalAccountRepository(sessions))
        assert await fresh_service.get(telegram_id) == UntappdProfile("other_beer")
        assert await fresh_service.get(other_id) == UntappdProfile("beer_fan")
        async with sessions() as session:
            account = await session.scalar(
                select(ExternalAccount).where(ExternalAccount.user_id == user_id)
            )
            assert account.id == original_id
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.telegram_id.in_([telegram_id, other_id])))
        await engine.dispose()


async def test_telegram_untappd_link_and_status(database_url):
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    dispatcher = Dispatcher()
    service = ManageUntappdProfile(
        StartUser(PostgresUserRepository(sessions)), PostgresExternalAccountRepository(sessions)
    )
    dispatcher.include_router(create_untappd_router(service))
    telegram_id = uuid4().int % (2**50) + 1
    bot = Bot(token="123456:test-token", session=AsyncMock())
    try:
        for update_id, text in enumerate(("/untappd Beer_Fan", "/untappd"), start=1):
            await dispatcher.feed_update(
                bot,
                Update(
                    update_id=update_id,
                    message=Message(
                        message_id=update_id,
                        date=datetime.now(UTC),
                        chat=Chat(id=telegram_id, type="private"),
                        from_user=TelegramUser(id=telegram_id, is_bot=False, first_name="Test"),
                        text=text,
                    ),
                ),
            )
        assert bot.session.call_count == 2
        for call in bot.session.call_args_list:
            assert "https://untappd.com/user/beer_fan" in call.args[1].text
            assert "Импорт истории оценок пока недоступен" in call.args[1].text
        assert await service.get(telegram_id) == UntappdProfile("beer_fan")
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.telegram_id == telegram_id))
        await dispatcher.storage.close()
        await bot.session.close()
        await engine.dispose()


async def test_telegram_start_update_creates_one_persistent_user(database_url):
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    dispatcher = Dispatcher()
    dispatcher.include_router(create_start_router(StartUser(PostgresUserRepository(sessions))))
    telegram_id = uuid4().int % (2**50) + 1
    bot = Bot(token="123456:test-token", session=AsyncMock())
    try:
        for update_id in (1, 2):
            await dispatcher.feed_update(
                bot,
                Update(
                    update_id=update_id,
                    message=Message(
                        message_id=update_id,
                        date=datetime.now(UTC),
                        chat=Chat(id=telegram_id, type="private"),
                        from_user=TelegramUser(id=telegram_id, is_bot=False, first_name="Test"),
                        text="/start",
                    ),
                ),
            )
        assert bot.session.call_count == 2
        for call in bot.session.call_args_list:
            assert "профиль сохранён" in call.args[1].text
        async with sessions() as session:
            users = (
                await session.scalars(select(User).where(User.telegram_id == telegram_id))
            ).all()
            assert len(users) == 1
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.telegram_id == telegram_id))
        await dispatcher.storage.close()
        await bot.session.close()
        await engine.dispose()
