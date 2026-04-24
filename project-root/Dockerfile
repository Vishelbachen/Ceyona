FROM python:3.11-slim

# =========================
# 🔐 RUNTIME SAFETY
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH=/app \
    PORT=8000 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONNOUSERSITE=1

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
# 📁 SOURCE CODE FIRST (FIXED BUILD ORDER)
# =========================
COPY pyproject.toml ./

COPY app ./app
COPY core ./core
COPY transport ./transport
COPY cognition ./cognition
COPY agents ./agents
COPY memory ./memory
COPY llm ./llm
COPY payments ./payments
COPY external ./external
COPY security ./security
COPY observability ./observability

# =========================
# 📦 INSTALL (DETERMINISTIC BUILD)
# =========================
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# =========================
# 🔐 SWITCH USER
# =========================
USER appuser

# =========================
# 🚀 START
# =========================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "30"]