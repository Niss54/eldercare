FROM python:3.11-slim
WORKDIR /app
COPY apps/worker/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -e .
COPY apps/worker/src /app/src
CMD ["celery", "-A", "src.celery_app:celery_app", "worker", "-l", "info"]
