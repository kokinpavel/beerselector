from src.application.start import StartUser
from src.modules.users.contracts import ExternalAccountRepository
from src.modules.users.untappd import UntappdProfile, parse_untappd_profile


class ManageUntappdProfile:
    def __init__(self, start_user: StartUser, accounts: ExternalAccountRepository) -> None:
        self.start_user = start_user
        self.accounts = accounts

    async def link(self, telegram_id: int, value: str) -> UntappdProfile:
        profile = parse_untappd_profile(value)
        user_id = await self.start_user.execute(telegram_id)
        return await self.accounts.save_untappd(user_id, profile)

    async def get(self, telegram_id: int) -> UntappdProfile | None:
        user_id = await self.start_user.execute(telegram_id)
        return await self.accounts.get_untappd(user_id)
