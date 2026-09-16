import base64
import binascii
import hashlib
import logging

from app.config.settings import Settings
from app.domain.errors import (
    CacheUnavailableError,
    InvalidPayloadError,
    PayloadTooLargeError,
)
from app.domain.models.extract_request import ExtractionRequest
from app.domain.models.extract_result import ExtractionResult
from app.domain.ports import CachePort, ExtractionRepositoryPort, TextProcessorPort

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "pdf:extract:"


class ExtractionService:
    def __init__(
        self,
        cache: CachePort,
        processor: TextProcessorPort,
        repository: ExtractionRepositoryPort,
        settings: Settings,
    ) -> None:
        self._cache = cache
        self._processor = processor
        self._repository = repository
        self._settings = settings

    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self._enforce_payload_limit(request.pdf_base64)
        payload_bytes = self._decode_base64(request.pdf_base64)
        checksum = hashlib.sha256(payload_bytes).hexdigest()
        cache_key = CACHE_KEY_PREFIX + checksum

        cached = await self._get_cached(cache_key)
        if cached is not None:
            return cached

        extracted = await self._processor.extract(payload_bytes)
        result = ExtractionResult(
            document_id=request.document_id,
            filename=request.filename,
            text=extracted.text,
            page_count=extracted.page_count,
            checksum=checksum,
        )

        await self._repository.save(result)
        await self._set_cached(cache_key, result)
        return result

    def _enforce_payload_limit(self, payload_b64: str) -> None:
        if len(payload_b64) > self._settings.base64_payload_max_size_bytes:
            raise PayloadTooLargeError(
                f"payload exceeds maximum allowed size of "
                f"{self._settings.base64_payload_max_size_mb} MB"
            )

    @staticmethod
    def _decode_base64(payload_b64: str) -> bytes:
        try:
            return base64.b64decode(payload_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidPayloadError("payload is not valid base64") from exc

    async def _get_cached(self, key: str) -> ExtractionResult | None:
        try:
            cached = await self._cache.get(key)
        except CacheUnavailableError:
            logger.warning(
                "cache unavailable during get; proceeding without cache", exc_info=True
            )
            return None
        if cached is None:
            return None
        return ExtractionResult.model_validate_json(cached)

    async def _set_cached(self, key: str, result: ExtractionResult) -> None:
        try:
            await self._cache.set(
                key, result.model_dump_json(), self._settings.cache_ttl_seconds
            )
        except CacheUnavailableError:
            logger.warning(
                "cache unavailable during set; result not cached", exc_info=True
            )
