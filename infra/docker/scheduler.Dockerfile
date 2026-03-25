FROM python:3.11-slim
WORKDIR /app
COPY apps/scheduler/pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir -e .
COPY apps/scheduler/src /app/src
CMD ["celery", "-A", "src.beat:beat", "beat", "-l", "info"]
