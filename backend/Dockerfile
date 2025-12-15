# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base AS development

# Install all dependencies including dev
COPY pyproject.toml /app/../
WORKDIR /app/..
RUN pip install -e ".[dev]"

WORKDIR /app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production builder stage
FROM base AS builder

COPY pyproject.toml /app/../
WORKDIR /app/..
RUN pip install build && python -m build --wheel

# Production stage
FROM base AS production

# Create non-root user
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --from=builder /app/../dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

WORKDIR /app
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
