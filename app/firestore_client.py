"""Firestore client wrapper for URL records."""

import asyncio
from typing import Any

from google.cloud import firestore

from app.config import settings
from app.models import UrlRecord

_client: firestore.Client | None = None


def get_client() -> firestore.Client:
    """Lazy-init Firestore client. Reused across requests."""
    global _client
    if _client is None:
        _client = firestore.Client(project=settings.gcp_project_id)
    return _client


def _collection() -> firestore.CollectionReference:
    return get_client().collection(settings.firestore_collection)


async def get_by_code(code: str) -> UrlRecord | None:
    """Fetch a URL record by its short code. Returns None if missing."""

    def _sync() -> dict[str, Any] | None:
        doc = _collection().document(code).get()
        return doc.to_dict() if doc.exists else None

    data = await asyncio.to_thread(_sync)
    return UrlRecord(**data) if data else None


async def create_if_absent(record: UrlRecord) -> bool:
    """
    Atomically create a record only if its code doesn't already exist.

    Returns True on successful create, False if the code is already taken
    (caller should retry with a fresh code).
    """

    def _sync() -> bool:
        doc_ref = _collection().document(record.code)
        # Firestore: create() fails with AlreadyExists if doc exists.
        # That's exactly the "atomic create" semantic we need.
        try:
            doc_ref.create(record.to_firestore_dict())
            return True
        except Exception as e:  # google.api_core.exceptions.AlreadyExists
            if "already exists" in str(e).lower():
                return False
            raise

    return await asyncio.to_thread(_sync)


async def ping() -> bool:
    """Health check — verify we can reach Firestore."""

    def _sync() -> bool:
        # Cheapest possible call: list one document from the collection.
        list(_collection().limit(1).stream())
        return True

    try:
        return await asyncio.to_thread(_sync)
    except Exception:
        return False