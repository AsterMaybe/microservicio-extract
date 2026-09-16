from pymongo.asynchronous.collection import AsyncCollection

from app.domain.models.extract_result import ExtractionResult


class ExtractionRepository:
    def __init__(self, collection: AsyncCollection) -> None:
        self._collection = collection

    async def save(self, result: ExtractionResult) -> None:
        document = result.model_dump(mode="json")
        await self._collection.update_one(
            {"checksum": result.checksum},
            {"$set": document},
            upsert=True,
        )
