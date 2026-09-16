# Tasks: PDF Text Extraction Microservice

- [ ] Task: Scaffold project tooling (uv, ruff, mypy, pytest, pyproject.toml)
  - Acceptance: `pyproject.toml` with deps; `uv sync` resolves on Python 3.14.7; lint/fmt/type/test commands run
  - Verify: `uv sync; uv run ruff check .; uv run mypy app; uv run pytest` (exit 0, no tests yet)
  - Files: `pyproject.toml`, `Dockerfile` (base layer), `.gitignore`, `.python-version`

- [ ] Task: Domain contracts — ports, types, exceptions
  - Acceptance: `CachePort`, `TextProcessorPort`, `ExtractionRepositoryPort` Protocols; Pydantic `ExtractionRequest`, `ExtractionResult`, `ProblemDetails`; exception hierarchy with `status_code`; no I/O imports in `domain/`
  - Verify: `uv run ruff check . && uv run mypy app`; unit tests for Pydantic model validation
  - Files: `app/domain/ports.py`, `app/domain/types/*.py`, `app/domain/errors.py`, `tests/unit/test_domain_models.py`

- [ ] Task: Config layer
  - Acceptance: `AppSettings` via pydantic-settings reads `REDIS_URL`, `MONGODB_URI`, `MONGODB_DB`, `BASE64_PAYLOAD_MAX_SIZE_MB` (default 25), `CACHE_TTL_SECONDS` (default 86400); size limit validated >0
  - Verify: `uv run pytest tests/unit/test_settings.py`; ruff+mypy clean
  - Files: `app/config/settings.py`, `tests/unit/test_settings.py`

- [ ] Task: Redis cache adapter
  - Acceptance: implements `CachePort` on `redis.asyncio`; `get`/`set` with TTL; connection errors surface as `CacheUnavailableError` (non-fatal downstream)
  - Verify: unit tests with `fakeredis`; ruff+mypy clean
  - Files: `app/infrastructure/cache/redis_cache.py`, `tests/unit/test_redis_cache.py`

- [ ] Task: pymupdf4llm processor adapter
  - Acceptance: implements `TextProcessorPort`; `extract(bytes) -> ExtractionResult.TextInfo` (text + page_count); raises `ExtractionError`/`CorruptPdfError` on bad bytes; 100% async wrapper
  - Verify: unit test against generated in-memory PDF; unit test for non-PDF bytes raises `CorruptPdfError`
  - Files: `app/infrastructure/processor/pymupdf4llm_processor.py`, `tests/unit/test_pymupdf4llm_processor.py`

- [ ] Task: Mongo client + extraction repository
  - Acceptance: async `MongoClient` lifecycle; `ExtractionRepository` implements `ExtractionRepositoryPort` (`save`, unique index on checksum)
  - Verify: unit tests with mocked `AsyncMongoClient`/collection; integration test marked, run locally if Mongo up
  - Files: `app/infrastructure/storage/mongo_client.py`, `app/repositories/extraction_repository.py`, `tests/unit/test_extraction_repository.py`, `tests/integration/test_mongo_repository.py`

- [ ] Task: Extraction service (core)
  - Acceptance: cache-first flow exactly per SPEC; Base64 decode `validate=True` in service layer; SHA-256 key; cache miss → extract → save → cache set; cache down → proceed (logged); `PayloadTooLargeError` from controller-driven limit is raised in service before decode
  - Verify: unit tests — cache hit (processor not called), miss (persist+set called), invalid Base64 → `InvalidPayloadError(400)`, cache-unavailable fallback, oversized payload → 413
  - Files: `app/services/extraction_service.py`, `tests/unit/test_extraction_service.py`

- [ ] Task: Controllers + API (RFC 9457, DI, app factory)
  - Acceptance: `POST /extract` → 200 result; `GET /health` → 200; exception handlers map domain errors to ProblemDetails with `application/problem+json`; `RequestValidationError` → 422 problem; size limit enforced from settings; adapters constructed in `deps.py`
  - Verify: TestClient fault injection — bad Base64 → 400 problem body with correct content-type, corrupted PDF → 422 problem, health → 200, oversized → 413
  - Files: `app/controllers/extract_controller.py`, `app/api/routes/*.py`, `app/api/deps.py`, `app/api/errors.py`, `app/main.py`, `tests/unit/test_api.py`

- [ ] Task: Dockerfile + docker-compose.yml (Traefik + shared network)
  - Acceptance: compose runs Traefik (web entrypoint, Docker provider, labels on app: router `Host(\`extract.…\`)`, PathPrefix `/`, loadbalancer port 8000, healthcheck), app (uv image), redis:7-alpine, mongo:7; app attached to `choreographer-net` (external) + internal network; `.env` consumes settings vars
  - Verify: `docker compose config --quiet`; manual `docker compose up --build` smoke test (documented, blocked if no Docker daemon)
  - Files: `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md` (setup incl. `docker network create choreographer-net`)