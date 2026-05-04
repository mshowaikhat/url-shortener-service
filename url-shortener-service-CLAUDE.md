# url-shortener-service — Repo Context

This is the FastAPI service that creates short codes for long URLs and persists them to Firestore. **Write endpoints require an `X-API-Key` header.** Liveness and readiness probes are publicly accessible.

If you have not read the parent `swe455/CLAUDE.md`, do that first.

---

## Layout

```
url-shortener-service/
├── .github/workflows/deploy.yml      # CI: lint -> build -> push -> deploy -> smoke test
├── Dockerfile                        # Python 3.13-slim, exec uvicorn on $PORT
├── docker-compose.yml                # Local dev: app + Firestore emulator
├── .dockerignore
├── pyproject.toml                    # Ruff config (line-length=100, target=py313)
├── requirements.txt                  # Pinned: fastapi, uvicorn, google-cloud-firestore, etc.
├── openapi.yaml                      # API contract (committed before code; Factor 13)
└── app/
    ├── __init__.py
    ├── main.py                       # FastAPI app, route registration
    ├── config.py                     # pydantic-settings, env vars only
    ├── firestore_client.py           # asyncio-wrapped sync Firestore SDK
    ├── models.py                     # Pydantic models for request/response/storage
    ├── middleware/
    │   └── auth.py                   # X-API-Key validation; reads secret at startup
    ├── routes/
    │   ├── health.py                 # /livez, /readyz
    │   └── urls.py                   # POST /api/urls, GET /api/urls/{code}
    └── utils/
        └── shortcode.py              # base62 8-char generator
```

---

## Running locally

```cmd
docker compose up --build
```

This starts:
- The shortener on `http://localhost:8080`
- A Firestore emulator on `firestore-emulator:8200` (internal)

The app auto-detects `FIRESTORE_EMULATOR_HOST` and routes Firestore calls there. No real GCP traffic, no auth, no costs.

To test:
```cmd
curl http://localhost:8080/livez
curl -X POST http://localhost:8080/api/urls -H "Content-Type: application/json" -d "{\"long_url\":\"https://example.com\"}"
```

The local docker-compose does NOT enforce the API key — that's a production-only constraint via Secret Manager. If you want to test the API key middleware locally, set `SHORTENER_API_KEY` env var explicitly in `docker-compose.yml`.

---

## Hot paths

- `POST /api/urls` (`app/routes/urls.py`) — validates URL is http/https, generates 8-char base62 code, retries on collision up to 3 times. Returns 201 with `code`, `long_url`, `created_at`, `click_count: 0`, `short_url` (constructed from `REDIRECT_BASE_URL` env var).
- `GET /api/urls/{code}` — fetches by code, 404 if missing.
- `GET /livez` — liveness only. Returns 200 always if process is up. Does NOT touch Firestore.
- `GET /readyz` — readiness. Returns 200 only if Firestore is reachable. 503 with `{"status":"degraded","details":{"firestore":"unreachable"}}` otherwise.

`/livez` and `/readyz` are explicitly exempted from API key auth. Cloud Run probes them without credentials; if you protect them, Cloud Run will mark the service unhealthy.

---

## Critical: do NOT use `/healthz`

Cloud Run reserves the literal path `/healthz` and intercepts it at its edge before the request reaches the container. We learned this the hard way. Both services use `/livez` instead. Do not "fix" this.

---

## Configuration

All config is loaded by `app/config.py` (pydantic-settings) at startup. Required env vars:

- `GCP_PROJECT_ID`
- `FIRESTORE_COLLECTION` (default `urls`)
- `LOG_LEVEL` (default `INFO`)
- `REDIRECT_BASE_URL` (used in POST response to build `short_url`)
- `PORT` (Cloud Run injects 8080; locally docker-compose sets it)
- `OTEL_SERVICE_NAME` (default `shortener`)

Optional:
- `FIRESTORE_EMULATOR_HOST` — set locally, unset in production. Auto-detected by the SDK.

If a required var is missing, the app fails fast at startup. Do not add silent defaults for production-required values.

---

## API key authentication (Factor 15)

Middleware in `app/middleware/auth.py` validates the `X-API-Key` header on `POST /api/urls` and `GET /api/urls/{code}`. The expected key is read once at startup from Secret Manager (`shortener-api-key`) and cached in memory — Secret Manager is NOT hit per-request.

**To rotate the key:** generate a new value, add it as a new version, then disable the old version. The next service redeployment picks up the latest enabled version.

```cmd
python -c "import secrets; print(secrets.token_hex(32))"
gcloud secrets versions add shortener-api-key --data-file=- --project=swe455-urlshortener-252
gcloud secrets versions disable <old-version-number> --secret=shortener-api-key --project=swe455-urlshortener-252
```

Do NOT log or echo the API key value anywhere. Never paste it into chat output.

---

## Logging — current state

The current code uses basic `logging.basicConfig`. Cloud Logging captures stdout, but logs are unstructured plaintext, so you can't filter by severity in the GCP Console without parsing.

This is on the gap list to fix (Factor 11 evidence). When implementing structured JSON logging:

- Replace `logging.basicConfig` in `app/main.py` with a JSON formatter
- Required fields: `timestamp` (ISO 8601 UTC), `severity` (Cloud Logging levels: `DEBUG`/`INFO`/`WARNING`/`ERROR`), `message`, `service` (e.g. `"shortener"`), `trace` (Cloud Trace ID — read from `X-Cloud-Trace-Context` header), `request_id`
- Use `python-json-logger==2.0.7` or write a custom formatter
- Cloud Logging auto-parses JSON on stdout when the field `severity` is uppercase string

Reference docs: https://cloud.google.com/logging/docs/structured-logging

---

## Lifespan / shutdown — current state

Currently uses deprecated `@app.on_event("startup")` and `@app.on_event("shutdown")` hooks. These work but FastAPI will remove them eventually. Replace with the lifespan context manager pattern. Cloud Run sends SIGTERM and gives ~10 seconds before SIGKILL — make sure shutdown completes well within that.

---

## Tests

Currently none. The CI workflow lints with Ruff but doesn't run pytest because there's nothing to run. If you add tests, they go under `tests/` at the repo root and the CI workflow's `lint` job needs an additional step to install + run pytest.

---

## Deploy flow

```
git push origin main
  -> .github/workflows/deploy.yml triggers
  -> Lint job: ruff check app/
  -> Build & deploy job:
     - WIF auth as shortener-deployer-sa
     - docker build -t <ar-repo>/shortener:<sha> .
     - docker push <ar-repo>/shortener:<sha>
     - gcloud run deploy shortener --image=<ar-repo>/shortener:<sha>
     - Smoke test /livez (6 retries x 5 sec)
```

Total time: 3-5 minutes from push to live.

---

## Common operations

```cmd
:: Lint locally before push (CI will fail on lint errors)
python -m ruff check app/ --fix
python -m ruff check app/

:: View Cloud Run logs
gcloud run services logs read shortener --region=us-central1 --project=swe455-urlshortener-252 --limit=50

:: Force-redeploy without code changes (e.g., to pick up an env var change from infra)
git commit --allow-empty -m "ci: redeploy"
git push origin main

:: Read the live API key (for testing — don't paste into chat)
gcloud secrets versions access latest --secret=shortener-api-key --project=swe455-urlshortener-252
```

---

## Things you must NOT do

- Do not change the `openapi.yaml` contract in breaking ways. You may add endpoints or optional fields. You may not remove or rename what's there.
- Do not bypass the API key check on `POST /api/urls` or `GET /api/urls/{code}`.
- Do not add Redis or other backing services here. The shortener is intentionally simple. Backing service additions go to redirect.
- Do not commit any `.env` file or any file containing real secret values.
- Do not introduce `:latest` image tags.
