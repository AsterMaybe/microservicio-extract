from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.errors import DomainError
from app.domain.models.problem_details import ProblemDetails

PROBLEM_MEDIA_TYPE = "application/problem+json"
HTTP_PROBLEM_TYPES = {
    400: "/problems/invalid-request",
    404: "/problems/not-found",
    405: "/problems/method-not-allowed",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status = exc.status_code if exc.status_code is not None else 500
        problem = ProblemDetails(
            type=exc.problem_type,
            title=exc.title,
            status=status,
            detail=exc.detail,
            instance=str(request.url),
        )
        return _problem_response(status, problem)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        detail = _validation_summary(exc)
        problem = ProblemDetails(
            type="/problems/invalid-request",
            title="Invalid Request",
            status=422,
            detail=detail,
            instance=str(request.url),
        )
        return _problem_response(422, problem)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        status = exc.status_code
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        problem = ProblemDetails(
            type=HTTP_PROBLEM_TYPES.get(status, "about:blank"),
            title=_status_title(status),
            status=status,
            detail=detail,
            instance=str(request.url),
        )
        return _problem_response(status, problem)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        problem = ProblemDetails(
            type="/problems/internal-error",
            title="Internal Server Error",
            status=500,
            detail="an unexpected error occurred",
            instance=str(request.url),
        )
        return _problem_response(500, problem)


def _validation_summary(exc: RequestValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "request validation failed"
    return "; ".join(
        f"{'.'.join(str(part) for part in err.get('loc', ()))}: {err.get('msg', '')}"
        for err in errors
    )


def _status_title(status: int) -> str:
    return {
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        413: "Payload Too Large",
        500: "Internal Server Error",
    }.get(status, "Error")


def _problem_response(status: int, problem: ProblemDetails) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(),
        media_type=PROBLEM_MEDIA_TYPE,
    )
