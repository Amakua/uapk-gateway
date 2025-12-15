"""UAPK Gateway - FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import get_logger, setup_logging
from app.ui.routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context manager."""
    logger = get_logger("app.lifespan")
    settings = get_settings()

    logger.info(
        "starting_application",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Startup: Initialize resources
    await init_db()
    logger.info("database_initialized")

    yield

    # Shutdown: Cleanup resources
    logger.info("shutting_down_application")
    await close_db()
    logger.info("database_closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Universal Agent Protocol Kit Gateway - "
            "Policy enforcement and audit logging for AI agents. "
            "Agents POST action requests to the gateway, which enforces policies, "
            "capabilities, and budgets while logging tamper-evident InteractionRecords."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware - strict defaults for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Mount static files for UI
    app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")

    # Include API routers
    app.include_router(v1_router, prefix="/api")

    # Include UI router (operator dashboard)
    app.include_router(ui_router)

    # Root-level health endpoints (convenience aliases)
    @app.get("/healthz", include_in_schema=False)
    async def root_health() -> dict[str, str]:
        """Root health check alias."""
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def root_ready() -> dict[str, str]:
        """Root readiness check alias."""
        return {"status": "ready"}

    return app


# Application instance
app = create_app()


def cli() -> None:
    """CLI entry point for running the server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    cli()
