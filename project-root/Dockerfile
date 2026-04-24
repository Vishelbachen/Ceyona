# =========================
# 🧠 BASE IMAGE (stable)
# =========================
FROM python:3.11-slim

# =========================
# 🔐 SECURITY
# =========================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# =========================
# ⚙️ SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# 👤 CREATE NON-ROOT USER (CRITICAL)
# =========================
RUN useradd -m appuser
USER appuser

# =========================
# 📦 INSTALL DEPENDENCIES (CACHE OPTIMIZED)
# =========================
COPY --chown=appuser:appuser pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# =========================
# 📁 SOURCE CODE
# =========================
COPY --chown=appuser:appuser . .

# =========================
# 🚀 PRODUCTION SERVER
# =========================
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--timeout-keep-alive", "30"]