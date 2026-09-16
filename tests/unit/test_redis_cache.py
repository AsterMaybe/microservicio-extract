import pytest
from fakeredis import FakeAsyncRedis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.domain.errors import CacheUnavailableError
from app.infrastructure.cache.redis_cache import RedisCache


@pytest.mark.asyncio
async def test_get_returns_stored_value_as_string() -> None:
    client = FakeAsyncRedis()
    cache = RedisCache(client)
    await client.set("k", "v")

    assert await cache.get("k") == "v"


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key() -> None:
    cache = RedisCache(FakeAsyncRedis())

    assert await cache.get("missing") is None


@pytest.mark.asyncio
async def test_set_stores_value_retrievable_by_get() -> None:
    cache = RedisCache(FakeAsyncRedis())

    await cache.set("k", "value", ttl_seconds=60)

    assert await cache.get("k") == "value"


@pytest.mark.asyncio
async def test_get_surfaces_connection_failure_as_cache_unavailable() -> None:
    class BrokenClient:
        async def get(self, key: str) -> None:
            raise RedisConnectionError("no route to host")

    cache = RedisCache(BrokenClient())  # type: ignore[arg-type]

    with pytest.raises(CacheUnavailableError):
        await cache.get("k")


@pytest.mark.asyncio
async def test_set_surfaces_connection_failure_as_cache_unavailable() -> None:
    class BrokenClient:
        async def set(self, key: str, value: str, ex: int) -> None:
            raise RedisConnectionError("no route to host")

    cache = RedisCache(BrokenClient())  # type: ignore[arg-type]

    with pytest.raises(CacheUnavailableError):
        await cache.set("k", "v", ttl_seconds=60)
