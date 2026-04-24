FROM python:3.11-slim

WORKDIR /app

# system deps (важно для cryptography, orjson, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# dependency tooling
RUN pip install --upgrade pip setuptools wheel

# copy only dependency metadata first (cache layer optimization)
COPY pyproject.toml ./

# install project dependencies from pyproject
RUN pip install .

# copy source
COPY . .

# runtime config
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]