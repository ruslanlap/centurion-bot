FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy application code
COPY centurion_bot/ centurion_bot/

# Create data directory for SQLite
RUN mkdir -p data

EXPOSE 8080

CMD ["python", "-m", "centurion_bot"]
