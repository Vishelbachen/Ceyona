"""
transport/telegram/queue_consumer.py

Фоновый consumer очереди pending_updates (Supabase).

Архитектура (Вариант 1 / push-queue, ARCH-refactor июль 2026):
    Telegram → Cloudflare Worker → INSERT в pending_updates (мгновенно, 200 OK)
    HF Space → queue_consumer (этот файл) → process_update() → ответ пользователю

Раньше Worker синхронно форвардил апдейт на HF и ждал ответа — если HF Space
был холодным, Worker упирался в собственный 30s wall-time лимит и апдейт
терялся молча (см. incident 2026-07-04: ConnectTimeout + waitUntil() cancelled).
Теперь Worker вообще не ждёт HF: кладёт апдейт в очередь и сразу отвечает.
HF сам вычитывает очередь, когда готов — независимо от того, насколько
медленным был cold start.

Паттерн скопирован с уже проверенного в проде _wallet_poll_loop() (TON
polling, app/main.py) — тот же принцип: asyncio.create_task с бесконечным
циклом poll + sleep, переживающий всё время жизни приложения.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Интервал между опросами очереди. TON-поллинг в проекте использует 10s —
# здесь короче, потому что это прямой путь ответа пользователю в Telegram,
# и задержка напрямую ощущается как "бот долго думает".
POLL_INTERVAL_SECONDS = 1.5

# Сколько апдейтов вычитывать за один проход. Больше — выше throughput при
# всплеске сообщений, но и больше конкурентных задач на один HF-контейнер.
BATCH_SIZE = 10

# После скольких неудачных попыток обработки апдейт помечается 'failed'
# и больше не подхватывается poller'ом (чтобы битый апдейт не крутился
# в цикле retry вечно, забирая ресурсы у нормальных апдейтов).
MAX_ATTEMPTS = 3


def _now_iso() -> str:
    """
    PostgREST не выполняет SQL-функции вроде now() из JSON-тела запроса —
    это интерпретировалось бы как буквальная строка "now()" и упало бы на
    типе timestamptz (или дало неверное значение). Настоящее время нужно
    сгенерировать на стороне клиента.
    """
    return datetime.now(timezone.utc).isoformat()


async def _claim_batch(supabase) -> list[dict]:
    """
    Атомарно забирает пачку 'pending' записей и сразу помечает их
    'processing', чтобы при нескольких параллельных consumer'ах (сейчас их
    нет, но код готов к этому) никто не обработал одну и ту же запись дважды.

    Supabase REST API не даёт напрямую "SELECT ... FOR UPDATE SKIP LOCKED"
    одним вызовом, поэтому делаем это в два шага: читаем кандидатов, затем
    UPDATE ... WHERE status='pending' AND id IN (...) — если два poller'а
    заберут одну и ту же строку одновременно, только один UPDATE применится
    первым и вернёт строку; второй просто получит 0 обновлённых строк для
    неё и отфильтрует её из своего батча ниже.
    """
    result = (
        supabase.table("pending_updates")
        .select("id, update_id, payload, attempts")
        .eq("status", "pending")
        .order("created_at")
        .limit(BATCH_SIZE)
        .execute()
    )
    candidates = result.data or []
    if not candidates:
        return []

    ids = [row["id"] for row in candidates]

    claimed = (
        supabase.table("pending_updates")
        .update({"status": "processing", "claimed_at": _now_iso()})
        .in_("id", ids)
        .eq("status", "pending")  # защита от гонки, см. docstring выше
        .execute()
    )
    claimed_ids = {row["id"] for row in (claimed.data or [])}
    return [row for row in candidates if row["id"] in claimed_ids]


async def _mark_done(supabase, row_id: int) -> None:
    try:
        supabase.table("pending_updates").update({
            "status": "done",
            "completed_at": _now_iso(),
        }).eq("id", row_id).execute()
    except Exception as exc:
        logger.error("queue_consumer: failed to mark row done", extra={"row_id": row_id, "error": str(exc)})


async def _mark_failed(supabase, row_id: int, attempts: int, error: str) -> None:
    next_status = "failed" if attempts + 1 >= MAX_ATTEMPTS else "pending"
    try:
        supabase.table("pending_updates").update({
            "status": next_status,
            "attempts": attempts + 1,
            "last_error": error[:2000],
            "completed_at": _now_iso() if next_status == "failed" else None,
        }).eq("id", row_id).execute()
    except Exception as exc:
        logger.error("queue_consumer: failed to mark row failed", extra={"row_id": row_id, "error": str(exc)})


async def _process_one(app_state, row: dict) -> None:
    from transport.telegram.webhook import process_update

    row_id = row["id"]
    update = row["payload"]

    try:
        await process_update(update, app_state)
        await _mark_done(app_state.supabase, row_id)
    except Exception as exc:
        logger.error(
            "queue_consumer: process_update failed",
            extra={"row_id": row_id, "update_id": row.get("update_id"), "error": str(exc)},
        )
        await _mark_failed(app_state.supabase, row_id, row.get("attempts", 0), repr(exc))


async def queue_consumer_loop(app_state) -> None:
    """
    Background task: раз в POLL_INTERVAL_SECONDS вычитывает необработанные
    апдейты из pending_updates и прогоняет их через process_update().

    Запускается один раз при старте приложения (см. app/main.py lifespan,
    по аналогии с _wallet_poll_loop) и живёт всё время жизни процесса.
    """
    supabase = app_state.supabase

    while True:
        try:
            batch = await _claim_batch(supabase)
            if batch:
                logger.info("queue_consumer: claimed batch", extra={"count": len(batch)})
                # Обрабатываем апдейты из одного батча параллельно — они
                # независимы друг от друга (разные пользователи/чаты).
                await asyncio.gather(*(_process_one(app_state, row) for row in batch))
        except Exception as exc:
            logger.error("queue_consumer: loop iteration failed", extra={"error": str(exc)})

        await asyncio.sleep(POLL_INTERVAL_SECONDS)