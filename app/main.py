from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI

from app.api.deps import RuntimeFactory, default_runtime
from app.api.errors import register_exception_handlers
from app.api.routes.extract import router as extract_router
from app.api.routes.health import router as health_router
from app.config.settings import Settings


def create_app(
    settings: Settings | None = None,
    runtime_factory: RuntimeFactory | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    resolved_factory = cast(RuntimeFactory, runtime_factory or default_runtime)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with resolved_factory(resolved_settings) as runtime:
            app.state.runtime = runtime
            yield

    app = FastAPI(title="pdf-extract-service", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(extract_router)
    return app


app = create_app()
