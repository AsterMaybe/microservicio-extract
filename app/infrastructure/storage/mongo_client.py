from typing import Any

from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase


class MongoDatabase:
    def __init__(self, uri: str, db_name: str) -> None:
        self._client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(uri)
        self._db_name = db_name

    @property
    def database(self) -> AsyncDatabase:
        return self._client[self._db_name]

    @property
    def extractions(self) -> AsyncCollection:
        return self.database["extractions"]

    async def ensure_indexes(self) -> None:
        await self.extractions.create_index([("checksum", ASCENDING)], unique=True)

    async def close(self) -> None:
        await self._client.close()
