from typing import cast

from fastapi import APIRouter, Depends, Request

from app.controllers.extract_controller import ExtractController
from app.domain.models.extract_request import ExtractionRequest
from app.domain.models.extract_result import ExtractionResult

router = APIRouter(tags=["extract"])


def get_controller(request: Request) -> ExtractController:
    return cast(ExtractController, request.app.state.runtime.controller)


@router.post("/extract", status_code=200, response_model=ExtractionResult)
async def extract(
    payload: ExtractionRequest,
    controller: ExtractController = Depends(get_controller),
) -> ExtractionResult:
    return await controller.extract(payload)
