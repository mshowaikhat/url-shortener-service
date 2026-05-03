"""Application configuration, loaded from environment variables (Factor 3)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All config for the shortener service. Read once at startup."""

    # Required: GCP project (used by Firestore client)
    gcp_project_id: str = Field(..., alias="GCP_PROJECT_ID")

    # Required: Firestore collection name
    firestore_collection: str = Field("urls", alias="FIRESTORE_COLLECTION")

    # Optional: log level
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Optional: base URL prefix used when constructing short_url in responses
    redirect_base_url: str = Field(
        "http://localhost:8081", alias="REDIRECT_BASE_URL"
    )

    # Optional: HTTP port the app listens on (Cloud Run injects PORT=8080)
    port: int = Field(8080, alias="PORT")

    # OpenTelemetry (B will use these; defaults are safe)
    otel_service_name: str = Field("shortener", alias="OTEL_SERVICE_NAME")

    # Firestore emulator support: when set, the google-cloud-firestore
    # client auto-detects it via FIRESTORE_EMULATOR_HOST.
    firestore_emulator_host: str | None = Field(
        None, alias="FIRESTORE_EMULATOR_HOST"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Singleton — imported wherever needed
settings = Settings()