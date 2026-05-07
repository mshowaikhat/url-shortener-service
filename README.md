# url-shortener-service

FastAPI service that creates short codes from long URLs and persists them to Google Cloud Firestore. Part of the SWE 455 (Cloud Applications Engineering) URL shortener project at KFUPM.

The companion services live in:

- [`url-redirect-service`](https://github.com/mshowaikhat/url-redirect-service) — resolves a code and returns an HTTP 302 redirect
- [`url-shortener-infra`](https://github.com/mshowaikhat/url-shortener-infra) — Terraform for everything in GCP

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/urls` | `X-API-Key` | Generate an 8-char base62 code for `long_url`; write to Firestore |
| `GET`  | `/api/urls/{code}` | `X-API-Key` | Look up an existing record |
| `GET`  | `/livez` | none | Liveness probe (200 while process is up) |
| `GET`  | `/readyz` | none | Readiness probe (200 if Firestore reachable, else 503) |

Full schema: [`openapi.yaml`](./openapi.yaml).

> **Note:** Cloud Run reserves `/healthz` at the edge — the probes are `/livez` and `/readyz`.

---

## Tech stack

- Python 3.13 + FastAPI 0.115 + Uvicorn
- Google Cloud Firestore (native mode, collection `urls`)
- Google Secret Manager (`shortener-api-key`)
- Cloud Run v2, Artifact Registry (SHA-tagged images)
- OpenTelemetry → Cloud Trace + Cloud Monitoring
- Structured JSON logging (Cloud Logging native fields)
- API key authentication on write endpoints (Twelve-Factor Factor 15)

---

## Local development

A `docker-compose.yml` is included with a Firestore emulator.

```bash
docker compose up --build
# Service on  http://localhost:8080
# Firestore emulator on  http://localhost:8085
```

Run the test suite (where applicable):

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # if present
pytest
```

---

## Configuration (environment variables)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GCP_PROJECT_ID` | yes | — | GCP project hosting Firestore |
| `FIRESTORE_COLLECTION` | no | `urls` | Firestore collection name |
| `FIRESTORE_EMULATOR_HOST` | no | — | Set for local dev with the emulator |
| `SHORTENER_API_KEY` | yes (prod) | — | In production this comes from Secret Manager via Cloud Run; for local dev set it directly |
| `LOG_LEVEL` | no | `INFO` | |
| `OTEL_SERVICE_NAME` | no | `shortener` | |
| `REDIRECT_BASE_URL` | yes | — | Used to build the `short_url` returned to clients |
| `PORT` | no | `8080` | Cloud Run sets this automatically |

Secrets are **never** committed. In production, the API key is mounted as a Cloud Run secret reference to the `shortener-api-key` Secret Manager resource.

---

## Admin / migration job (Factor 12)

The same image is used as a Cloud Run **Job** (`shortener-migrate`) with the entrypoint overridden to `python -m app.migrate`. The job is provisioned by Terraform in the infra repo and its image is updated by CI on every push to `main`.

---

## CI/CD

Every push to `main` runs `.github/workflows/deploy.yml`:

```
lint (ruff) → docker build → push to Artifact Registry (SHA tag) → Cloud Run deploy → update migration job image → smoke test
```

Authentication uses **Workload Identity Federation** — there are no service-account keys stored in GitHub Secrets.

---

## Repository layout

```
app/
  main.py               # FastAPI app + lifespan (Factor 9)
  config.py             # Env-driven config (Factor 3)
  firestore_client.py   # Firestore client wrapper
  logging_config.py     # JSON logging for Cloud Logging
  tracing.py            # OTel → Cloud Trace + Cloud Monitoring
  middleware/           # API-key auth (Factor 15)
  models.py             # Pydantic models
  migrate.py            # Cloud Run Job entrypoint (Factor 12)
  routes/
    health.py           # /livez, /readyz
    urls.py             # /api/urls, /api/urls/{code}
Dockerfile
docker-compose.yml      # Local dev with Firestore emulator
openapi.yaml            # Public API spec
```

---

## License & course context

KFUPM SWE 455 Term 252 course project.
