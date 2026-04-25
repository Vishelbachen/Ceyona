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
# PYTHON TOOLCHAIN
# =========================
RUN pip install --upgrade pip setuptools wheel

# =========================
# DEPENDENCIES (CACHED LAYER)
# =========================
COPY pyproject.toml ./
COPY README.md ./

RUN pip install .

# =========================
# SOURCE CODE
# =========================
COPY . .

# =========================
# RUNTIME CONFIG
# =========================
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# =========================
# START COMMAND
# =========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]