from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

from pymongo.asynchronous.collection import AsyncCollection

from app.domain.models.extract_result import ExtractionResult
from app.repositories.extraction_repository import ExtractionRepository


def _result() -> ExtractionResult:
    return ExtractionResult(
        document_id="doc-1",
        filename="report.pdf",
        text="hello",
        page_count=2,
        checksum="b" * 64,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


async def test_save_upserts_document_keyed_on_checksum() -> None:
    collection = AsyncMock(spec=AsyncCollection)
    collection.update_one = AsyncMock()
    repository = ExtractionRepository(cast(AsyncCollection, collection))
    result = _result()

    await repository.save(result)

    collection.update_one.assert_awaited_once_with(
        {"checksum": result.checksum},
        {"$set": result.model_dump(mode="json")},
        upsert=True,
    )


async def test_save_serializes_datetime_to_iso_string() -> None:
    collection = AsyncMock(spec=AsyncCollection)
    collection.update_one = AsyncMock()
    repository = ExtractionRepository(cast(AsyncCollection, collection))
    result = _result()

    await repository.save(result)

    update: dict[str, Any] = collection.update_one.call_args.args[1]
    created_at = update["$set"]["created_at"]
    assert created_at == "2026-01-01T00:00:00Z"
