"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI

from app.config import settings
from app.routes import health, urls

# Basic logging setup. B will replace this with structured JSON in their slice.
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="URL Shortener Service",
    description="Creates short codes that map to long URLs.",
    version="1.0.0",
)

# Routes
app.include_router(health.router)
app.include_router(urls.router)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "shortener starting: project=%s collection=%s emulator=%s",
        settings.gcp_project_id,
        settings.firestore_collection,
        settings.firestore_emulator_host or "none",
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("shortener shutting down")