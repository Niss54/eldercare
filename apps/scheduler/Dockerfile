# Scheduler (Celery Beat) Dockerfile - uses same base as API
FROM python:3.13-slim as builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final runtime image
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY src /app/src
COPY pyproject.toml .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check: celery inspect active_queues
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD celery -A src.integrations.celery_config inspect active_queues | grep -q "celery" || exit 1

# Start beat scheduler (requires CELERY_BROKER_URL and CELERY_RESULT_BACKEND env vars)
CMD ["celery", "-A", "src.integrations.celery_config", "beat", "--loglevel=info"]
