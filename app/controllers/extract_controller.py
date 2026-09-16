from app.domain.models.extract_request import ExtractionRequest
from app.domain.models.extract_result import ExtractionResult
from app.services.extraction_service import ExtractionService


class ExtractController:
    def __init__(self, service: ExtractionService) -> None:
        self._service = service

    async def extract(self, payload: ExtractionRequest) -> ExtractionResult:
        return await self._service.extract(payload)
