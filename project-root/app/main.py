from fastapi import FastAPI
from app.bootstrap import create_app

app = create_app()


@app.on_event("startup")
async def startup_event():
    try:
        from observability.sentry import init_sentry
        from observability.tracing import setup_tracing

        init_sentry()
        setup_tracing()
    except Exception:
        pass


@app.get("/health")
def health():
    return {"status": "ok"}