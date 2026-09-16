from typing import Protocol

from app.domain.models.extract_result import ExtractedContent, ExtractionResult


class CachePort(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class TextProcessorPort(Protocol):
    async def extract(self, pdf_bytes: bytes) -> ExtractedContent: ...


class ExtractionRepositoryPort(Protocol):
    async def save(self, result: ExtractionResult) -> None: ...
