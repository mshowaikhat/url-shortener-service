import secrets
from typing import Optional

from fastapi import Header, HTTPException, status, Depends
from google.cloud import secretmanager

from app.config import settings

_cached_api_key: Optional[str] = None


def load_api_key() -> str:
    """
    Loads API key once from Secret Manager.
    """
    global _cached_api_key

    if _cached_api_key is not None:
        return _cached_api_key

    client = secretmanager.SecretManagerServiceClient()
    name = (
        f"projects/{settings.gcp_project_id}/secrets/"
        f"shortener-api-key/versions/latest"
    )

    response = client.access_secret_version(request={"name": name})
    _cached_api_key = response.payload.data.decode("utf-8").strip()

    return _cached_api_key


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected_key = load_api_key()

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )