FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    HOME=/home/appuser

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 appuser

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY --chown=appuser:appuser . .

USER appuser

CMD ["uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "2",
     "--timeout-keep-alive", "30"]