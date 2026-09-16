FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS base

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
RUN useradd --create-home --home-dir /home/app app

COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]