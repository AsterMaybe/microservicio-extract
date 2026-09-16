import base64
import hashlib

import pytest

from app.config.settings import Settings
from app.domain.errors import (
    CacheUnavailableError,
    InvalidPayloadError,
    PayloadTooLargeError,
)
from app.domain.models.extract_request import ExtractionRequest
from app.domain.models.extract_result import ExtractedContent, ExtractionResult
from app.services.extraction_service import ExtractionService


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.fail_ops: set[str] = set()

    def fail(self, operation: str) -> None:
        self.fail_ops.add(operation)

    async def get(self, key: str) -> str | None:
        if "get" in self.fail_ops:
            raise CacheUnavailableError("cache down")
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if "set" in self.fail_ops:
            raise CacheUnavailableError("cache down")
        self.store[key] = value


class FakeProcessor:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    async def extract(self, pdf_bytes: bytes) -> ExtractedContent:
        self.calls.append(pdf_bytes)
        return ExtractedContent(text="extracted text", page_count=3)


class FakeRepository:
    def __init__(self) -> None:
        self.saved: list[ExtractionResult] = []
        self.fail = False

    async def save(self, result: ExtractionResult) -> None:
        if self.fail:
            raise RuntimeError("mongo is down")
        self.saved.append(result)


def _make_request(payload: str = "dGVzdA==") -> ExtractionRequest:
    return ExtractionRequest(
        document_id="doc-1",
        filename="report.pdf",
        pdf_base64=payload,
    )


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        base64_payload_max_size_mb=10,
        cache_ttl_seconds=120,
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestCacheHit:
    async def test_returns_cached_result_without_processing(self) -> None:
        cache = FakeCache()
        processor = FakeProcessor()
        service = ExtractionService(
            cache=cache,
            processor=processor,
            repository=FakeRepository(),
            settings=_settings(),
        )
        request = _make_request()
        checksum = _sha256(base64.b64decode(request.pdf_base64))
        cached = ExtractionResult(text="cached", page_count=1, checksum=checksum)
        cache.store[f"pdf:extract:{checksum}"] = cached.model_dump_json()

        result = await service.extract(request)

        assert result == cached
        assert processor.calls == []


class TestCacheMiss:
    async def test_extracts_and_persists_on_cache_miss(self) -> None:
        processor = FakeProcessor()
        repository = FakeRepository()
        service = ExtractionService(
            cache=FakeCache(),
            processor=processor,
            repository=repository,
            settings=_settings(),
        )
        request = _make_request()
        payload = base64.b64decode(request.pdf_base64)

        result = await service.extract(request)

        assert result.text == "extracted text"
        assert result.page_count == 3
        assert result.checksum == _sha256(payload)
        assert result.document_id == "doc-1"
        assert result.filename == "report.pdf"
        assert len(repository.saved) == 1
        assert processor.calls == [payload]

    async def test_stores_result_in_cache_with_correct_key(self) -> None:
        cache = FakeCache()
        service = ExtractionService(
            cache=cache,
            processor=FakeProcessor(),
            repository=FakeRepository(),
            settings=_settings(),
        )
        request = _make_request()
        checksum = _sha256(base64.b64decode(request.pdf_base64))

        await service.extract(request)

        assert f"pdf:extract:{checksum}" in cache.store


class TestPayloadValidation:
    async def test_rejects_invalid_base64(self) -> None:
        service = _service()

        with pytest.raises(InvalidPayloadError):
            await service.extract(ExtractionRequest(pdf_base64="!!!not base64!!!"))

    async def test_rejects_payload_over_size_limit(self) -> None:
        service = _service()
        oversized = "A" * (10 * 1024 * 1024 + 1)

        with pytest.raises(PayloadTooLargeError):
            await service.extract(ExtractionRequest(pdf_base64=oversized))


class TestCacheFailureFallback:
    async def test_ignores_cache_get_failure(self) -> None:
        cache = FakeCache()
        cache.fail("get")
        repository = FakeRepository()
        service = _service(cache=cache, repository=repository)

        result = await service.extract(_make_request())

        assert result.text == "extracted text"
        assert len(repository.saved) == 1

    async def test_ignores_cache_set_failure(self) -> None:
        cache = FakeCache()
        cache.fail("set")
        repository = FakeRepository()
        service = _service(cache=cache, repository=repository)

        result = await service.extract(_make_request())

        assert result.text == "extracted text"
        assert len(repository.saved) == 1


class TestRepositoryFailure:
    async def test_propagates_persistence_error(self) -> None:
        repository = FakeRepository()
        repository.fail = True
        service = _service(repository=repository)

        with pytest.raises(RuntimeError, match="mongo is down"):
            await service.extract(_make_request())


def _service(
    cache: FakeCache | None = None,
    processor: FakeProcessor | None = None,
    repository: FakeRepository | None = None,
) -> ExtractionService:
    return ExtractionService(
        cache=cache or FakeCache(),
        processor=processor or FakeProcessor(),
        repository=repository or FakeRepository(),
        settings=_settings(),
    )
