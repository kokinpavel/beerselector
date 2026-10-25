from typing import Protocol
from uuid import UUID

from src.modules.users.untappd import UntappdProfile


class UserRepository(Protocol):
    async def get_or_create(self, telegram_id: int) -> UUID: ...


class ExternalAccountRepository(Protocol):
    async def save_untappd(self, user_id: UUID, profile: UntappdProfile) -> UntappdProfile: ...

    async def get_untappd(self, user_id: UUID) -> UntappdProfile | None: ...
