"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.logging_config import setup_logging
from app.middleware.auth import load_api_key
from app.routes import health, urls
from app.tracing import setup_observability

# Configure JSON logging before any module emits a log record.
setup_logging(
    service=settings.otel_service_name,
    project_id=settings.gcp_project_id,
    level=settings.log_level,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks (replaces deprecated @app.on_event)."""
    # OTel providers must be configured before any request creates a span.
    setup_observability(settings.otel_service_name, settings.gcp_project_id)

    # Auto-instrument FastAPI; relies on TracerProvider being set above.
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OTel instrumentation active")
    except Exception as exc:  # noqa: BLE001
        logger.warning("FastAPI instrumentation skipped: %s", exc)

    load_api_key()
    logger.info(
        "shortener starting: project=%s collection=%s emulator=%s",
        settings.gcp_project_id,
        settings.firestore_collection,
        settings.firestore_emulator_host or "none",
    )
    yield
    logger.info("shortener shutting down")


app = FastAPI(
    title="URL Shortener Service",
    description="Creates short codes that map to long URLs.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(urls.router)
