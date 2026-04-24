# =========================
# 🧠 BASE IMAGE (stable + slim)
# =========================
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# =========================
# ⚙️ SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 📦 DEPENDENCY LAYER (cached)
# =========================
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# =========================
# 📁 SOURCE CODE
# =========================
COPY . .

# =========================
# 🔐 SECURITY / RUNTIME
# =========================
ENV PYTHONPATH=/app

# =========================
# 🚀 START COMMAND
# =========================
CMD ["python", "-m", "app.main"]