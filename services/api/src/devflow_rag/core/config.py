from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://devflow:devflow_local@localhost:5433/devflow"
    cors_origins: str = "http://localhost:3000"
    ollama_url: str = "http://localhost:11434"
    embedding_model: str = "qwen3-embedding:4b"
    chat_model: str = "qwen3:8b"
    storage_dir: str = "../../data/uploads"
    max_upload_bytes: int = 10_000_000
    min_similarity: float = 0.35

    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
