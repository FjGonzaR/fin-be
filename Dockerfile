# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build tools needed for some native extensions (psycopg2-binary, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip && pip install --no-cache-dir .


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Runtime system deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default env — override at runtime via docker run -e or platform env vars
ENV APP_ENV=production \
    DEBUG=false \
    PORT=8000

EXPOSE 8000

# Run migrations then start the server
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2
