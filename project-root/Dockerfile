# =========================
# 🧠 BASE IMAGE
# =========================
FROM python:3.11-slim

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
# 📦 INSTALL DEPENDENCIES (no poetry = cleaner)
# =========================
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# =========================
# 📁 SOURCE CODE
# =========================
COPY . .

# =========================
# 🚀 PRODUCTION SERVER
# =========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]