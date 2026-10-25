from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiogram.filters import CommandObject
from sqlalchemy.exc import OperationalError

from src.application.untappd import ManageUntappdProfile
from src.modules.users.untappd import UntappdProfile, parse_untappd_profile
from src.telegram.untappd import create_untappd_router


@pytest.mark.parametrize(
    "value",
    [
        "Beer_Fan",
        " @Beer_Fan ",
        "https://untappd.com/user/Beer_Fan",
        "https://www.untappd.com/user/Beer_Fan/",
    ],
)
def test_parse_profile(value):
    profile = parse_untappd_profile(value)
    assert profile.username == "beer_fan"
    assert profile.url == "https://untappd.com/user/beer_fan"
    assert not profile.is_verified


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "beer fan",
        "a" * 101,
        "../user",
        "<script>",
        "https://example.com/user/beer_fan",
        "https://untappd.com.evil.com/user/beer_fan",
        "https://untappd.com@evil.com/user/beer_fan",
        "http://untappd.com/user/beer_fan",
        "https://untappd.com/user/",
        "https://untappd.com/user/beer_fan/beers",
        "https://untappd.com/user/beer_fan?token=secret",
        "https://untappd.com/user/beer_fan#fragment",
    ],
)
def test_invalid_profiles_are_rejected(value):
    with pytest.raises(ValueError):
        parse_untappd_profile(value)


async def test_link_validates_before_writing_and_uses_internal_user_id():
    user_id = uuid4()
    start = SimpleNamespace(execute=AsyncMock(return_value=user_id))
    accounts = SimpleNamespace(save_untappd=AsyncMock(return_value=UntappdProfile("beer_fan")))
    service = ManageUntappdProfile(start, accounts)
    with pytest.raises(ValueError):
        await service.link(42, "not a username")
    start.execute.assert_not_awaited()
    accounts.save_untappd.assert_not_awaited()
    assert await service.link(42, "Beer_Fan") == UntappdProfile("beer_fan")
    start.execute.assert_awaited_once_with(42)
    accounts.save_untappd.assert_awaited_once_with(user_id, UntappdProfile("beer_fan"))


async def test_get_profile_uses_current_user():
    user_id = uuid4()
    start = SimpleNamespace(execute=AsyncMock(return_value=user_id))
    accounts = SimpleNamespace(get_untappd=AsyncMock(return_value=None))
    assert await ManageUntappdProfile(start, accounts).get(42) is None
    accounts.get_untappd.assert_awaited_once_with(user_id)


@pytest.mark.parametrize(
    "failure", [ValueError(), OSError(), OperationalError("", {}, Exception())]
)
async def test_handler_handles_invalid_input_and_database_errors(failure):
    profiles = SimpleNamespace(link=AsyncMock(side_effect=failure))
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42), chat=SimpleNamespace(type="private"), answer=AsyncMock()
    )
    router = create_untappd_router(profiles)
    await router.message.handlers[0].callback(
        message, CommandObject(command="untappd", args="beer")
    )
    reply = message.answer.call_args.args[0]
    assert "Не удалось" in reply
    assert "Указанный профиль" not in reply


async def test_handler_does_not_link_or_disclose_profile_in_group():
    profiles = SimpleNamespace(link=AsyncMock(), get=AsyncMock())
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42), chat=SimpleNamespace(type="group"), answer=AsyncMock()
    )
    router = create_untappd_router(profiles)
    await router.message.handlers[0].callback(
        message, CommandObject(command="untappd", args="beer")
    )
    profiles.link.assert_not_awaited()
    profiles.get.assert_not_awaited()
    assert "личном чате" in message.answer.call_args.args[0]


async def test_handler_shows_instructions_when_no_profile_saved():
    profiles = SimpleNamespace(get=AsyncMock(return_value=None))
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=42), chat=SimpleNamespace(type="private"), answer=AsyncMock()
    )
    router = create_untappd_router(profiles)
    await router.message.handlers[0].callback(message, CommandObject(command="untappd"))
    profiles.get.assert_awaited_once_with(42)
    assert "/untappd username" in message.answer.call_args.args[0]
