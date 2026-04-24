from fastapi import FastAPI
from app.bootstrap import create_app
from observability.tracing import setup_tracing
from observability.sentry import init_sentry

init_sentry()
setup_tracing()

app = create_app()


@app.get("/health")
def health():
    return {"status": "ok"}