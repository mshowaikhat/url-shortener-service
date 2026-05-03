# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

# Don't write .pyc files, don't buffer stdout (Factor 11: logs go straight to stdout)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so changes to app/ don't bust the layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY app/ ./app/

# Cloud Run injects PORT=8080. Locally, docker-compose sets PORT=8080 too.
ENV PORT=8080
EXPOSE 8080

# Bind to 0.0.0.0:$PORT (Factor 7: port binding)
# Using `sh -c` so the env var expands at runtime, not build time
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}