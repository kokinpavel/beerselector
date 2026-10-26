import re

from pydantic import BaseModel, Field

MAX_ITEMS = 60
MAX_TEXT_LENGTH = 20_000
HEADER = re.compile(
    r"(?:beer\s+menu|menu|меню|пиво|разливное(?:\s+пиво)?|бутылочное(?:\s+пиво)?|"
    r"draft\s+beers?|bottled\s+beers?|название|на\s+кранах)[\s:]*",
    re.IGNORECASE,
)
ABV = re.compile(r"(?<![\d.,])(\d{1,2}(?:[.,]\d{1,2})?)\s*%")


class MenuItem(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    abv: float | None = Field(default=None, ge=0, le=30)


class MenuDraft(BaseModel):
    raw_text: str
    items: list[MenuItem]
    caption: str = ""
    truncated: bool = False


def parse_menu(text: str, caption: str = "") -> MenuDraft:
    """Extract provisional rows only; do not invent beers, styles or missing ABV."""
    items: list[MenuItem] = []
    truncated = len(text) > MAX_TEXT_LENGTH
    for line in text[:MAX_TEXT_LENGTH].splitlines():
        line = " ".join(line.split())
        if not line or HEADER.fullmatch(line) or not re.search(r"[^\W\d_]", line):
            continue
        if len(items) == MAX_ITEMS:
            truncated = True
            break
        amounts = ABV.findall(line)
        abv = float(amounts[0].replace(",", ".")) if len(amounts) == 1 else None
        if abv is not None and abv > 30:
            abv = None
        truncated = truncated or len(line) > 300
        items.append(MenuItem(text=line[:300], abv=abv))
    return MenuDraft(
        raw_text=text[:MAX_TEXT_LENGTH], items=items, caption=caption[:1024], truncated=truncated
    )
