"""
Migration / admin entrypoint — Factor 12 admin process.

Runs as a Cloud Run Job (not the web service). Uses the same image, the
same env vars, and the same service account as the shortener service, so
migrations execute in an identical environment to production.

Current operations:
  1. Verify Firestore is reachable and the configured collection is accessible.

Extend this file as the data model evolves (index seeding, backfills, etc.).
Exit code 0 = success, non-zero = failure — Cloud Run Jobs surface non-zero
exits as task failures and stop the execution immediately.
"""

import logging
import sys

from google.cloud import firestore

from app.config import settings
from app.logging_config import setup_logging

setup_logging(
    service="shortener-migrate",
    project_id=settings.gcp_project_id,
    level=settings.log_level,
)
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info(
        "migration starting project=%s collection=%s",
        settings.gcp_project_id,
        settings.firestore_collection,
    )

    client = firestore.Client(project=settings.gcp_project_id)
    docs = list(client.collection(settings.firestore_collection).limit(1).stream())
    logger.info(
        "firestore ok collection=%s docs_sampled=%d",
        settings.firestore_collection,
        len(docs),
    )

    logger.info("migration complete")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        logger.error("migration failed: %s", exc)
        sys.exit(1)
