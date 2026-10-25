from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.users.models import User


class PostgresUserRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def get_or_create(self, telegram_id: int) -> UUID:
        async with self.sessions.begin() as session:
            # The unique constraint also protects concurrent /start requests.
            await session.execute(
                insert(User)
                .values(telegram_id=telegram_id)
                .on_conflict_do_nothing(constraint="uq_users_telegram_id")
            )
            result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
            return result.scalar_one()
