import os
import logging

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ceyona-relay")

HF_WEBHOOK_URL = os.environ["HF_WEBHOOK_URL"].rstrip("/") + "/webhook"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
FORWARD_TIMEOUT = float(os.environ.get("FORWARD_TIMEOUT", "20.0"))

app = FastAPI()
client: httpx.AsyncClient | None = None


@app.on_event("startup")
async def startup() -> None:
    global client
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
    client = httpx.AsyncClient(timeout=FORWARD_TIMEOUT, limits=limits)


@app.on_event("shutdown")
async def shutdown() -> None:
    if client is not None:
        await client.aclose()


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/webhook")
async def relay(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    body = await request.body()

    headers = {"Content-Type": "application/json"}
    if x_telegram_bot_api_secret_token:
        headers["X-Telegram-Bot-Api-Secret-Token"] = x_telegram_bot_api_secret_token

    try:
        resp = await client.post(HF_WEBHOOK_URL, content=body, headers=headers)
        logger.info("Forwarded update, HF status=%s", resp.status_code)
    except httpx.HTTPError as exc:
        logger.error("Forward to HF failed: %s", exc)
        # Always ack Telegram so it doesn't retry/backoff the same update forever.
        return {"ok": True}

    return {"ok": True}
