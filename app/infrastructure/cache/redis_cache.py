from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.errors import CacheUnavailableError


class RedisCache:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        try:
            value = await self._client.get(key)
        except RedisError as exc:
            raise CacheUnavailableError("cache is unreachable") from exc
        if value is None:
            return None
        return value.decode("utf-8") if isinstance(value, bytes) else value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._client.set(key, value, ex=ttl_seconds)
        except RedisError as exc:
            raise CacheUnavailableError("cache is unreachable") from exc
