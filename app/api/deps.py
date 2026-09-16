from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from app.config.settings import Settings
from app.controllers.extract_controller import ExtractController
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.processor.pymupdf4llm_processor import Pymupdf4LlmProcessor
from app.infrastructure.storage.mongo_client import MongoDatabase
from app.repositories.extraction_repository import ExtractionRepository
from app.services.extraction_service import ExtractionService


async def _noop() -> None: ...


RuntimeFactory = Callable[[Settings], Any]


@dataclass
class Runtime:
    controller: ExtractController
    close: Callable[[], Awaitable[None]] = _noop


@asynccontextmanager
async def default_runtime(settings: Settings) -> AsyncIterator[Runtime]:
    redis_client = Redis.from_url(settings.redis_url)
    cache = RedisCache(redis_client)
    mongo = MongoDatabase(settings.mongodb_uri, settings.mongodb_db)
    await mongo.ensure_indexes()

    repository = ExtractionRepository(mongo.extractions)
    service = ExtractionService(
        cache=cache,
        processor=Pymupdf4LlmProcessor(),
        repository=repository,
        settings=settings,
    )

    async def close() -> None:
        await redis_client.aclose()
        await mongo.close()

    yield Runtime(controller=ExtractController(service), close=close)
    await close()
