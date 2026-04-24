FROM python:3.11-slim

# =========================
# 🔐 RUNTIME SAFETY
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# =========================
# ⚙️ SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 👤 NON-ROOT USER
# =========================
RUN useradd -m -u 10001 appuser

# =========================
# 📦 DEPENDENCY LAYER
# =========================
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# =========================
# 📁 SOURCE CODE
# =========================
COPY --chown=appuser:appuser . .

USER appuser

# =========================
# 🚀 PRODUCTION SERVER (RAILWAY SAFE)
# =========================
CMD ["uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "1",
     "--timeout-keep-alive", "30"]