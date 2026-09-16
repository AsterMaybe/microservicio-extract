# pdf-extract-service

Microservice that extracts text from Base64-encoded PDFs for the Choreographer.
Strict N-Layer architecture (`api`, `config`, `controllers`, `domain`,
`infrastructure`, `repositories`, `services`), FastAPI behind a Traefik API
Gateway, Redis cache keyed by the PDF's SHA-256, and Mongo persistence via the
async PyMongo driver.

All API errors are returned as RFC 9457 `application/problem+json`.

## Local development

Requires Python 3.14 and `uv`.

```sh
uv sync
uv run uvicorn app.main:app --reload
```

## Commands

```sh
uv run pytest                     # unit tests (integration excluded)
uv run pytest -m integration      # integration tests (needs live Redis/Mongo)
uv run ruff check .
uv run ruff format .
uv run mypy app
```

## Configuration (env)

| Variable | Default | Meaning |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `MONGODB_URI` | `mongodb://mongo:27017` | Mongo connection string |
| `MONGODB_DB` | `pdf_extractor` | Mongo database name |
| `BASE64_PAYLOAD_MAX_SIZE_MB` | `25` | Max accepted Base64 payload size in MB |
| `CACHE_TTL_SECONDS` | `86400` | Redis cache TTL |

## API

- `POST /extract` — body `{ "pdf_base64": "...", "document_id"?, "filename"? }` →
  `200` with `{ text, page_count, checksum, document_id, filename, created_at }`.
  Repeat submissions with the same bytes are served from cache.
- `GET /health` — liveness probe.

## Run with Docker (monolith-local setup)

This microservice does not run its own Traefik or Mongo — it reuses the
monolith's. In the monolith's `docker-compose.yml`, attach its **Traefik** and
its **Mongo** containers to the shared network:

```yaml
networks:
  choreographer-net:
    external: true
# attach <traefik-service> and <mongo-service> to: choreographer-net
```

Then run:

```sh
docker network create choreographer-net   # one-time
cp .env.example .env                      # set MONGODB_URI to your monolith's Mongo
docker compose up --build
```

Routing works through the monolith's Traefik via the `Host('extract.localhost')`
rule (labels on this container are auto-discovered), targeting the app on port
`8000`. The monolith calls `POST http://extract.localhost/extract`. If the
monolith Traefik's HTTP entrypoint is not named `web`, update the
`traefik.http.routers.pdf-extract.entrypoints` label. Endpoint docs are served
at `http://extract.localhost/docs`. Swap `extract.localhost` for a real domain
at deploy time.