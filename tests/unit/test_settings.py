import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_settings_apply_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.mongodb_uri == "mongodb://mongo:27017"
    assert settings.mongodb_db == "pdf_extractor"
    assert settings.base64_payload_max_size_mb == 25
    assert settings.cache_ttl_seconds == 86400


def test_settings_read_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380/2")
    monkeypatch.setenv("BASE64_PAYLOAD_MAX_SIZE_MB", "10")

    settings = Settings(_env_file=None)

    assert settings.redis_url == "redis://localhost:6380/2"
    assert settings.base64_payload_max_size_mb == 10


def test_settings_reject_non_positive_payload_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, base64_payload_max_size_mb=0)


def test_settings_reject_negative_payload_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, base64_payload_max_size_mb=-5)


def test_max_payload_bytes_derives_from_mb() -> None:
    settings = Settings(_env_file=None, base64_payload_max_size_mb=2)

    assert settings.base64_payload_max_size_bytes == 2 * 1024 * 1024
