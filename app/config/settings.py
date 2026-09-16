from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    redis_url: str = "redis://redis:6379/0"
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db: str = "pdf_extractor"
    base64_payload_max_size_mb: int = Field(gt=0, default=25)
    cache_ttl_seconds: int = Field(gt=0, default=86400)

    @property
    def base64_payload_max_size_bytes(self) -> int:
        return self.base64_payload_max_size_mb * 1024 * 1024
