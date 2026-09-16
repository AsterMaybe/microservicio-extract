# Spec: PDF Text Extraction Microservice

## Objective

A Python microservice that accepts Base64-encoded PDFs from a Choreographer,
extracts text with pymupdf4llm, and returns the plain text synchronously.

Owners in priority order: **cache-first**: skip extraction when the same file
(SHA-256 of the decoded bytes) was already processed; otherwise extract, persist
to MongoDB, and cache the result.

User story:
> As a Choreographer, I POST a JSON payload containing a Base64 PDF and
> immediately receive `{ text, page_count, checksum, ... }`. If the payload
> references a document I sent before, I get the cached/previous answer without
> re-processing.

Acceptance criteria:
- `POST /extract` with a valid Base64 PDF returns extracted text + metadata (200).
- Submitting the same bytes a second time returns the cached result without re-running pymupdf4llm.
- Invalid Base64, non-PDF bytes, and oversized payloads return RFC 9457 `application/problem+json` errors with correct status codes.
- `GET /health` returns 200 when the app is up.
- Strict N-Layer layout; dependencies point inward; adapters implement domain Protocols (Dependency Inversion).

## Tech Stack

- Python **3.14.7**, dependency management via **uv** (`pyproject.toml`)
- FastAPI + Pydantic v2 (latest compatible)
- PyMongo async driver (`pymongo.asyncio` — async MongoDB driver; Motor is deprecated)
- redis-py `redis.asyncio` (Redis cache)
- pymupdf4llm (LLM-friendly text extraction; built on PyMuPDF, which remains a transitive dep for `page_count`)
- Traefik v3 as API Gateway (labels, Docker provider)
- Dev/test: pytest, pytest-asyncio, ruff, mypy

Compatibility note: confirm PyMongo/pymupdf4llm wheels for 3.14 at install time during
implementation; pin exact versions in `pyproject.toml` once resolved.

## Commands

```
Install: uv sync
Run:     uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
Test:    uv run pytest
Lint:    uv run ruff check .
Format:  uv run ruff format .
Types:   uv run mypy app
Build:   docker compose up --build
```

## Project Structure

```
app/
  api/                → FastAPI app factory, routers, RFC 9457 handlers, DI deps
    deps.py
    errors.py
    routes/extract.py
    routes/health.py
  config/
    settings.py       → pydantic-settings, env-driven (REDIS_URL, MONGODB_URI,
                        BASE64_PAYLOAD_MAX_SIZE_MB, CACHE_TTL_SECONDS, ...)
  controllers/        → HTTP layer: parse/validate payload, call service, map exceptions
    extract_controller.py
  domain/             → Pydantic models + ports (Protocols). No I/O imports allowed.
    ports.py          → CachePort, TextProcessorPort, ExtractionRepositoryPort
    models/
      extract_request.py
      extract_result.py
      problem_details.py
    errors.py         → domain exception hierarchy
  infrastructure/     → adapters for external systems (implement domain ports)
    cache/redis_cache.py
    processor/pymupdf4llm_processor.py
    storage/mongo_client.py
  repositories/       → Mongo repository (implements ExtractionRepositoryPort)
    extraction_repository.py
  services/           → business logic orchestration (pure, depends only on ports)
    extraction_service.py
  main.py             → create_app()
tests/
  unit/               → service logic with mocked ports; models
  integration/        → real Redis/Mongo/pymupdf4llm via testcontainers or local deps
Dockerfile
docker-compose.yml
```

Dependency rule: `api → controllers → services → domain ← infrastructure/repositories`.
`config` is read by the composition root only. No layer imports from a layer it
does not depend on; no adapter imports another adapter directly.

## Code Style

Ruff defaults (E, F, I, W, UP, B) + line length 88, `from X import Y` imports,
type hints everywhere, no `Optional[...]`, no comments unless they explain a
non-obvious decision. One representative snippet:

```python
# domain/ports.py
class CachePort(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

# services/extraction_service.py
class ExtractionService:
    def __init__(
        self,
        cache: CachePort,
        processor: TextProcessorPort,
        repository: ExtractionRepositoryPort,
    ) -> None:
        self._cache = cache
        self._processor = processor
        self._repository = repository

    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        payload = base64.b64decode(request.pdf_base64, validate=True)
        checksum = hashlib.sha256(payload).hexdigest()

        cached = await self._cache.get(self._key_for(checksum))
        if cached is not None:
            return ExtractionResult.model_validate_json(cached)

        result = await self._processor.extract(payload)
        await self._repository.save(result)
        await self._cache.set(self._key_for(checksum), result.model_dump_json(), TTL)
        return result
```

Naming: snake_case modules/functions, PascalCase classes, async for everything
doing I/O, exceptions live in `domain/errors.py` and carry a `status_code`.

## Testing Strategy

- Framework: pytest + pytest-asyncio.
- `tests/unit`: service behavior with fake ports (`FakeCache`, `FakeProcessor`)
  — no network. Covers cache-hit (processor never called), cache-miss persist+set,
  decode failures, cache down (non-fatal) fallback.
- `tests/integration`: repository against real Mongo, cache adapter against real
  Redis, processor against a generated PDF. Marked `@pytest.mark.integration`.
- Coverage floor for service + controllers: 90%. CI runs `uv run pytest`,
  `uv run ruff check .`, `uv run mypy app`.

## Boundaries

- Always: follow the N-Layer layout; implement adapters against domain Protocols;
  validate every input (Base64 validity, size limit, magic bytes); return
  RFC 9457 problems for all 4xx/5xx; run lint + tests before committing; use
  checksum-derived cache keys.
- Ask first: adding a dependency; changing the request/response contract;
  changing MIME/status semantics; introducing a second database or cache cluster;
  altering the Traefik routing rules or network topology.
- Never: import infrastructure inside domain; write to Redis/Mongo from
  controllers/services directly (ports only); commit secrets or connection
  strings; let a processor exception escape as a 500 without a problem body;
  silently swallow decode/corruption errors.

## Success Criteria

1. `docker compose up` brings up Traefik + app + Redis + Mongo on a shared network.
2. Posting a valid Base64 PDF via the Traefik route returns 200 with
   `{ text, page_count, checksum }` and the document is persisted in Mongo.
3. Re-posting identical bytes returns the cached result and pymupdf4llm is not invoked
   a second time (verifiable via logs/cache probe).
4. Invalid Base64 → 400, corrupt/non-PDF → 400/422, both with
   `Content-Type: application/problem+json` per RFC 9457.
5. `GET /health` → 200.
6. Redis unavailable: extraction still completes and persists (cache treated as
   best-effort, logged).
7. `uv run ruff check . && uv run mypy app && uv run pytest` all pass.

## Configuration (env)

| Variable | Default | Meaning |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `MONGODB_URI` | `mongodb://mongo:27017` | Mongo connection string |
| `MONGODB_DB` | `pdf_extractor` | Mongo database name |
| `BASE64_PAYLOAD_MAX_SIZE_MB` | `25` | Max accepted Base64 payload size in MB |
| `CACHE_TTL_SECONDS` | `86400` | Redis cache TTL (24h) |

## Open Questions

Resolved (keep SDD defaults): cache TTL 86400s; a checksum found in Mongo but
missing from Redis does NOT re-warm the cache — the file is re-extracted. Payload
size limit reads from `BASE64_PAYLOAD_MAX_SIZE_MB` (default 25 MB of Base64 text
≈ ~18 MB decoded PDF); requests above the limit → 413.