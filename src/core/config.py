from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://untappt:untappt@localhost:5432/untappt"
    app_env: str = "development"
    log_level: str = "INFO"
    telegram_bot_token: str | None = None
    ocr_executable: str = "tesseract"
    ocr_languages: str = "eng+rus"
    ocr_page_segmentation: Literal[3, 6, 11] = 3
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"

    @field_validator("ocr_page_segmentation", mode="before")
    @classmethod
    def parse_ocr_page_segmentation(cls, value: object) -> object:
        return int(value) if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
