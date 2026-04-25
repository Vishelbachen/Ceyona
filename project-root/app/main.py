from fastapi import FastAPI
from app.bootstrap import create_app

app = create_app()


@app.on_event("startup")
async def startup_event():
    from observability.tracing import setup_tracing
    from observability.sentry import init_sentry

    init_sentry()
    setup_tracing()


@app.get("/health")
def health():
    return {"status": "ok"}