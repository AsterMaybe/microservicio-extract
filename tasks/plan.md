# Plan: PDF Text Extraction Microservice

Implementation order (component dependencies, then build order):

```
domain → infrastructure (parallel: cache | processor) + repositories
      → config, services
      → controllers, api (RFC 9457, DI)
      → tests, Dockerfile, docker-compose.yml (Traefik + shared network)
```

## Components & dependencies

| Component | Depends on |
|---|---|
| `domain/ports.py`, `domain/types.py`, `domain/errors.py` | — |
| `infrastructure/cache/redis_cache.py` | domain ports |
| `infrastructure/processor/pymupdf4llm_processor.py` | domain models/types |
| `repositories/extraction_repository.py` | domain ports, `infrastructure/storage/mongo_client.py` |
| `infrastructure/storage/mongo_client.py` | config |
| `config/settings.py` | pydantic-settings |
| `services/extraction_service.py` | domain ports, config |
| `controllers/extract_controller.py` | service |
| `api/routes/*, api/deps.py, api/errors.py, main.py` | controllers, config |
| `Dockerfile`, `docker-compose.yml` | all |

## Order

1. Domain contracts (ports, types, exceptions) — no external deps; unblocks everything.
2. Config (settings, env vars incl. `BASE64_PAYLOAD_MAX_SIZE_MB`).
3. Adapters in parallel: Redis cache, pymupdf4llm processor, Mongo client+repository.
4. Extraction service (cache-first flow).
5. Controllers + API wiring + RFC 9457 handlers + app factory.
6. Tests (unit along each step, integration marked).
7. Docker: Dockerfile, compose with Traefik labels + external shared network, `.env`.

## Risks & mitigations

- **Python 3.14 wheel availability** (PyMongo, pymupdf4llm, pydantic-core): resolve at
  install time in step 1-2; pin exact versions once `uv sync` succeeds. Fallback:
  ask human before stepping down to 3.13.
- **RFC 9457 strictness**: handlers must never leak framework 500 bodies; central
  exception→problem mapping in `api/errors.py` with `RequestValidationError`
  included.
- **Redis/mongo dependency injection hygiene** (Dependency Inversion): every
  adapter constructed at composition root (`api/deps.py`), never imported into
  services/domain.
- **Traefik external network absent locally**: compose uses `external: true`; document
  `docker network create choreographer-net` as a setup step.

## Parallel vs sequential

Parallel: cache + processor + mongo adapters. Sequential: domain → config →
adapters → service → api → tests → docker.

## Verification checkpoints

- After domain+config: `uv run ruff check . && uv run mypy app` clean (tests minimal).
- After service: unit tests green (cache hit / miss / decode fail / cache-down fallback).
- After api: fault-injection via TestClient — bad Base64→400 problem, corrupted
  PDF→422 problem, health→200.
- After docker: compose up, Traefik route POST, re-post same file → cached path.