import re
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class UntappdProfile:
    username: str
    is_verified: bool = False

    @property
    def url(self) -> str:
        return f"https://untappd.com/user/{self.username}"


def parse_untappd_profile(value: str) -> UntappdProfile:
    value = value.strip()
    if "://" in value:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.netloc.lower() not in {"untappd.com", "www.untappd.com"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Expected an HTTPS Untappd profile URL")
        match = re.fullmatch(r"/user/([A-Za-z0-9_]+)/?", parsed.path)
        if match is None:
            raise ValueError("Expected /user/username")
        value = match.group(1)
    else:
        value = value.removeprefix("@")
    if re.fullmatch(r"[A-Za-z0-9_]{1,100}", value) is None:
        raise ValueError("Invalid Untappd username")
    return UntappdProfile(username=value.lower())
