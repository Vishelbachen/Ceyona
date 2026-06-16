"""
Telegram long-polling transport.

Replaces webhook for environments where outbound connections to
api.telegram.org are blocked (e.g. HuggingFace Spaces).

Uses getUpdates with long-polling (timeout=25s). Each update is
processed through the same handler as the webhook path, so all
business logic remains unchanged.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from app.settings import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"
_POLL_TIMEOUT = 25      # seconds — Telegram long-poll window
_ERROR_SLEEP  = 5       # seconds — back-off on errors
_HTTP_TIMEOUT = 35      # httpx timeout — must be > _POLL_TIMEOUT


async def delete_webhook() -> None:
    """Remove any previously registered webhook so getUpdates works."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_TELEGRAM_API}/deleteWebhook",
                json={"drop_pending_updates": False},
            )
            data = resp.json()
            if data.get("ok"):
                logger.info("Webhook deleted — polling mode active")
            else:
                logger.warning("deleteWebhook returned not-ok", extra={"response": data})
    except Exception as exc:
        logger.warning("deleteWebhook failed (non-fatal)", extra={"error": str(exc)})


async def polling_loop(app_state) -> None:
    """
    Long-polling loop. Runs as a background asyncio task.

    Imports the webhook handler at runtime to reuse all existing
    update processing logic (auth, rate limiting, routing, etc.).
    """
    from transport.telegram.webhook import _process_update  # noqa: WPS433

    offset: int | None = None

    logger.info("Polling loop started")

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        while True:
            try:
                params: dict = {
                    "timeout": _POLL_TIMEOUT,
                    "allowed_updates": ["message", "edited_message", "callback_query"],
                }
                if offset is not None:
                    params["offset"] = offset

                resp = await client.get(
                    f"{_TELEGRAM_API}/getUpdates",
                    params=params,
                )
                data = resp.json()

                if not data.get("ok"):
                    logger.error("getUpdates error", extra={"response": data})
                    await asyncio.sleep(_ERROR_SLEEP)
                    continue

                updates: list[dict] = data.get("result", [])

                for update in updates:
                    update_id = update.get("update_id", 0)
                    offset = update_id + 1

                    # Fire-and-forget: don't let one slow update block polling.
                    asyncio.create_task(
                        _process_update(update, app_state),
                        name=f"update_{update_id}",
                    )

            except asyncio.CancelledError:
                logger.info("Polling loop cancelled")
                return
            except Exception as exc:
                logger.error("Polling loop error", extra={"error": str(exc)})
                await asyncio.sleep(_ERROR_SLEEP)