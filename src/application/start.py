from uuid import UUID

from src.modules.users.contracts import UserRepository


class StartUser:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def execute(self, telegram_id: int) -> UUID:
        if telegram_id <= 0:
            raise ValueError("telegram_id must be positive")
        return await self.users.get_or_create(telegram_id)
