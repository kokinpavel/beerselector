from pydantic import BaseModel, Field

MAX_ITEMS = 60
MAX_TEXT_LENGTH = 20_000
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class MenuItem(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class MenuDraft(BaseModel):
    raw_text: str
    items: list[MenuItem]
    caption: str = ""
    truncated: bool = False
