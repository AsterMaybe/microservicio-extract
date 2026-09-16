from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.deps import Runtime
from app.api.routes.extract import get_controller
from app.config.settings import Settings
from app.controllers.extract_controller import ExtractController
from app.domain.errors import PayloadTooLargeError
from app.main import create_app
from app.services.extraction_service import ExtractionService

from .test_extraction_service import FakeCache, FakeProcessor, FakeRepository


def _service_settings(**overrides: int) -> Settings:
    defaults: dict[str, object] = {"_env_file": None}
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


async def _noop() -> None: ...


@asynccontextmanager
async def _fake_runtime_factory(settings: Settings) -> AsyncIterator[Runtime]:
    cache = FakeCache()
    processor = FakeProcessor()
    repository = FakeRepository()
    service = ExtractionService(
        cache=cache, processor=processor, repository=repository, settings=settings
    )
    yield Runtime(controller=ExtractController(service), close=_noop)


VALID_REQUEST = {"pdf_base64": "dGVzdA==", "document_id": "d1", "filename": "f.pdf"}


class TestExtraction200:
    async def test_returns_extracted_text_with_metadata(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/extract", json=VALID_REQUEST)

        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "extracted text"
        assert body["page_count"] == 3
        assert body["document_id"] == "d1"
        assert body["filename"] == "f.pdf"
        assert len(body["checksum"]) == 64


class TestDomainErrors400And413:
    async def test_invalid_base64_returns_problem_400(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/extract", json={"pdf_base64": "!!!bad!!!"})

        assert response.status_code == 400
        _assert_problem_body(
            response, status=400, expected_type="/problems/invalid-payload"
        )

    async def test_payload_too_large_returns_problem_413(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        ctrl = AsyncMock(spec=ExtractController)
        ctrl.extract.side_effect = PayloadTooLargeError("too big")
        app.dependency_overrides[get_controller] = lambda: ctrl
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/extract", json={"pdf_base64": "AAAA"})

        assert response.status_code == 413
        _assert_problem_body(
            response, status=413, expected_type="/problems/payload-too-large"
        )


class TestValidationError422:
    async def test_missing_pdf_base64_returns_problem_422(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/extract", json={})

        assert response.status_code == 422
        _assert_problem_body(
            response, status=422, expected_type="/problems/invalid-request"
        )


class TestServerError500:
    async def test_unhandled_exception_returns_problem_500(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        ctrl = AsyncMock(spec=ExtractController)
        ctrl.extract.side_effect = RuntimeError("kaboom")
        app.dependency_overrides[get_controller] = lambda: ctrl
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/extract", json=VALID_REQUEST)

        assert response.status_code == 500
        _assert_problem_body(
            response, status=500, expected_type="/problems/internal-error"
        )


class TestHealth200:
    async def test_health_returns_ok(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestNotFound404:
    async def test_unknown_route_returns_problem_404(self) -> None:
        app = create_app(
            settings=_service_settings(),
            runtime_factory=_fake_runtime_factory,
        )
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/does/not/exist")

        assert response.status_code == 404
        _assert_problem_body(response, status=404, expected_type="/problems/not-found")


def _assert_problem_body(response, *, status: int, expected_type: str) -> None:
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status
    assert body["type"] == expected_type
    assert isinstance(body["title"], str) and body["title"]
    assert isinstance(body["detail"], str) and body["detail"]
