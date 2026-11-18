from functools import lru_cache
from typing import Any, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Personal Intelligent Email OS"
    APP_ENV: str = "production"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "debug", "on")
        return bool(v)
    API_V1_PREFIX: str = "/api/v1"
    FERNET_SECRET_KEY: str = "cGVyc29uYWwtaW50ZWxsaWdlbnQtZW1haWwtb3MtZmVybmV0LWtleS0zMmI="
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3005,http://127.0.0.1:3005"

    DATABASE_URL: str = "postgresql+asyncpg://emailos:emailos_secure_password@localhost:5432/emailos_db"
    SYNC_DATABASE_URL: str = "postgresql://emailos:emailos_secure_password@localhost:5432/emailos_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    GMAIL_SCOPES: str = (
        "https://www.googleapis.com/auth/gmail.modify,"
        "https://www.googleapis.com/auth/gmail.labels"
    )

    PRIMARY_LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    TELEGRAM_BOT_TOKEN: str = ""
    ALLOWED_TELEGRAM_USER_IDS: str = ""

    SYNC_INTERVAL_MINUTES: int = 5
    CLEANUP_CRON_HOUR: int = 3
    DIGEST_DAY_OF_WEEK: str = "sun"
    DIGEST_HOUR: int = 9
    GHOSTED_SLA_HOURS: int = 72

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def gmail_scope_list(self) -> List[str]:
        return [s.strip() for s in self.GMAIL_SCOPES.split(",") if s.strip()]

    @property
    def allowed_telegram_ids(self) -> List[int]:
        ids: List[int] = []
        for raw in self.ALLOWED_TELEGRAM_USER_IDS.split(","):
            val = raw.strip()
            if val.isdigit():
                ids.append(int(val))
        return ids


@lru_cache()
def get_settings() -> Settings:
    return Settings()
