import os

import pytest

from app.domain.models.extract_result import ExtractionResult
from app.infrastructure.storage.mongo_client import MongoDatabase
from app.repositories.extraction_repository import ExtractionRepository

TEST_DB = "pdf_extractor_test"
TEST_COLLECTION = "extractions_it"


def _result(checksum: str) -> ExtractionResult:
    return ExtractionResult(text="hello", page_count=1, checksum=checksum)


@pytest.fixture()
async def mongo() -> None:
    uri = os.getenv("MONGO_TEST_URI", "mongodb://localhost:27017")
    db = MongoDatabase(uri, TEST_DB)
    try:
        await db.extractions.drop()
        await db.ensure_indexes()
        yield db
    finally:
        await db.database.drop_collection(TEST_COLLECTION)
        await db.close()


@pytest.mark.integration
async def test_save_persists_extraction_retrievable_by_checksum(
    mongo: MongoDatabase,
) -> None:
    repository = ExtractionRepository(mongo.extractions)
    result = _result("c" * 64)

    await repository.save(result)

    stored = await mongo.extractions.find_one({"checksum": result.checksum})
    assert stored is not None
    assert stored["text"] == "hello"
    assert stored["page_count"] == 1


@pytest.mark.integration
async def test_save_is_idempotent_for_same_checksum(mongo: MongoDatabase) -> None:
    repository = ExtractionRepository(mongo.extractions)
    result = _result("d" * 64)

    await repository.save(result)
    await repository.save(result)

    count = await mongo.extractions.count_documents({"checksum": result.checksum})
    assert count == 1


@pytest.mark.integration
async def test_save_reuses_document_when_checksum_reappears(
    mongo: MongoDatabase,
) -> None:
    repository = ExtractionRepository(mongo.extractions)
    first = _result("e" * 64)
    await repository.save(first)

    updated = first.model_copy(update={"text": "reprocessed"})
    await repository.save(updated)

    count = await mongo.extractions.count_documents({"checksum": first.checksum})
    assert count == 1
    stored = await mongo.extractions.find_one({"checksum": first.checksum})
    assert stored is not None
    assert stored["text"] == "reprocessed"
