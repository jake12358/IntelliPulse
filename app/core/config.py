from functools import lru_cache
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:
    BaseSettings = object
    SettingsConfigDict = dict


class Settings(BaseSettings):
    app_name: str = "IntelliPulse"
    app_env: str = "development"
    api_prefix: str = "/api"

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://postgres:123456@localhost:5432/intellipulse"
    sync_database_url: str = "postgresql+psycopg2://postgres:123456@localhost:5432/intellipulse"

    upload_dir: str = "data/uploads"
    parsed_dir: str = "data/parsed"

    llm_provider: str = "dashscope"
    dashscope_api_key: str = ""
    dashscope_model: str = "qwen-plus"
    dashscope_embedding_model: str = "text-embedding-v3"

    embedding_provider: str = "local"
    local_embedding_dim: int = 384
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"
    cors_origin_regex: str = r"http://(localhost|127\.0\.0\.1):[0-9]+"

    if BaseSettings is not object:
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **values):
        if BaseSettings is not object:
            super().__init__(**values)
            return
        import os

        annotations = getattr(self, "__annotations__", {})
        for key, annotation in annotations.items():
            default = getattr(self.__class__, key)
            raw = os.getenv(key.upper(), default)
            if annotation is int:
                raw = int(raw)
            setattr(self, key, raw)
        for key, value in values.items():
            setattr(self, key, value)

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def upload_path(self) -> Path:
        return (self.base_dir / self.upload_dir).resolve()

    @property
    def parsed_path(self) -> Path:
        return (self.base_dir / self.parsed_dir).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.parsed_path.mkdir(parents=True, exist_ok=True)
    return settings
