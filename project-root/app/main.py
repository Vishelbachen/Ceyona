from fastapi import FastAPI
from app.bootstrap import create_app
from observability.sentry import init_sentry
from observability.tracing import setup_tracing

app = create_app()

@app.on_event("startup")
async def startup():
    init_sentry()
    setup_tracing()

@app.get("/health")
def health():
    return {"status": "ok"}