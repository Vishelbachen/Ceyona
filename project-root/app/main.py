from fastapi import FastAPI
from app.bootstrap import create_app

app = create_app()

@app.get("/health")
def health():
    return {"status": "ok"}