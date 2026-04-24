FROM python:3.11-slim

# =========================
# 🔐 RUNTIME SAFETY
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app

WORKDIR /app

# =========================
# ⚙️ SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 👤 NON-ROOT USER (SECURITY)
# =========================
RUN useradd -m -u 10001 appuser

# =========================
# 📦 DEPENDENCIES (CACHED LAYER)
# =========================
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# =========================
# 📁 SOURCE CODE
# =========================
COPY --chown=appuser:appuser . .

USER appuser

# =========================
# 🚀 RAILWAY-OPTIMIZED SERVER
# =========================
CMD ["uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8000",
     "--workers", "1",
     "--timeout-keep-alive", "30"]