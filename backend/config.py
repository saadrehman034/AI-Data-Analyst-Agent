import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────────────────────
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"

    def model_post_init(self, __context):
        # Strip whitespace/newlines from keys that are used in HTTP headers
        object.__setattr__(self, "gemini_api_key", self.gemini_api_key.strip())
        object.__setattr__(self, "secret_key", self.secret_key.strip())
        object.__setattr__(self, "fernet_key", self.fernet_key.strip())

    # ── Databases ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres@localhost:5432/querymind"
    analyst_db_url: str = "postgresql://postgres@localhost:5432/business_data"
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10

    # ── Security ──────────────────────────────────────────────────────────────
    # Generate once: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = secrets.token_hex(32)
    # Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    fernet_key: str = ""   # MUST be set in production .env

    # ── Query limits ──────────────────────────────────────────────────────────
    max_query_rows: int = 1000
    max_retry_count: int = 3
    conversation_history_limit: int = 5

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 20   # requests per user/IP per minute for /query

    # ── Misc ──────────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    environment: str = "development"   # development | production

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
