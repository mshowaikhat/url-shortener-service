"""Pydantic models for request, response, and Firestore documents."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, HttpUrl, field_validator


class CreateUrlRequest(BaseModel):
    """Request body for POST /api/urls."""

    long_url: HttpUrl

    @field_validator("long_url")
    @classmethod
    def must_be_http_or_https(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in ("http", "https"):
            raise ValueError("URL must use http or https scheme")
        return v


class UrlRecord(BaseModel):
    """A URL record as stored in Firestore and returned to clients."""

    code: str
    long_url: str
    created_at: datetime
    click_count: int = 0
    short_url: str | None = None  # Only set in responses, not stored

    @classmethod
    def new(cls, code: str, long_url: str) -> "UrlRecord":
        """Factory: build a fresh record with current timestamp."""
        return cls(
            code=code,
            long_url=long_url,
            created_at=datetime.now(UTC),
            click_count=0,
        )

    def to_firestore_dict(self) -> dict[str, Any]:
        """Serialize for Firestore. Excludes derived fields like short_url."""
        return {
            "code": self.code,
            "long_url": self.long_url,
            "created_at": self.created_at,
            "click_count": self.click_count,
        }


class HealthResponse(BaseModel):
    status: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
