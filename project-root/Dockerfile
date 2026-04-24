FROM python:3.11-slim

WORKDIR /app

# =========================
# SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# =========================
# PYTHON TOOLING
# =========================
RUN pip install --upgrade pip setuptools wheel

# =========================
# DEPENDENCY LAYER (CACHED)
# =========================
COPY pyproject.toml ./
RUN pip install .

# =========================
# SOURCE CODE
# =========================
COPY . .

# =========================
# RUNTIME CONFIG
# =========================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OTEL_SERVICE_NAME=ai-platform \
    OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# =========================
# START
# =========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]