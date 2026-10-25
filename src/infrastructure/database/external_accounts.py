from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.users.models import ExternalAccount
from src.modules.users.untappd import UntappdProfile


class PostgresExternalAccountRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def save_untappd(self, user_id: UUID, profile: UntappdProfile) -> UntappdProfile:
        async with self.sessions.begin() as session:
            # An entered username never proves account ownership. Changing it resets verification.
            await session.execute(
                insert(ExternalAccount)
                .values(user_id=user_id, provider="untappd", username=profile.username)
                .on_conflict_do_update(
                    constraint="uq_external_accounts_user_provider",
                    set_={"username": profile.username, "is_verified": False},
                )
            )
        return UntappdProfile(username=profile.username)

    async def get_untappd(self, user_id: UUID) -> UntappdProfile | None:
        async with self.sessions() as session:
            account = await session.scalar(
                select(ExternalAccount).where(
                    ExternalAccount.user_id == user_id, ExternalAccount.provider == "untappd"
                )
            )
            if account is None:
                return None
            return UntappdProfile(username=account.username, is_verified=account.is_verified)
