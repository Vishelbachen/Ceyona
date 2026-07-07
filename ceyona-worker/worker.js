/**
 * Ceyona Webhook Worker
 *
 * ARCH-change 2026-07 (outbox): HF Space больше не делает исходящий вызов
 * ни к api.telegram.org, ни к этому Worker'у, чтобы ОТПРАВИТЬ ответ
 * пользователю (см. project-root/transport/telegram/webhook.py::
 * _post_via_worker) — вместо HTTP-вызова HF пишет строку в таблицу Supabase
 * `outbox`. Причина: подтверждённый по логам ConnectTimeout именно на
 * исходящем соединении HF-контейнера наружу (incident 2026-07-04), в то
 * время как вызовы HF → Supabase в том же окне ни разу не показали такой
 * ошибки. Теперь единственная исходящая сетевая зависимость HF для отправки
 * ответа — Supabase INSERT, а сам HTTP-вызов к Telegram выполняет этот
 * Worker.
 *
 * РЕШЕНИЕ (2026-07): полностью событийная схема, БЕЗ cron и БЕЗ
 * scheduled() — по явному решению не создавать вообще никакого
 * расписанного Cloudflare-трафика к HF (ни keep-alive пинг, ни
 * периодический drain). Вместо этого:
 *
 *   Supabase Database Webhook (триггер: INSERT в outbox)
 *     → POST /outbox/drain на этом Worker'е
 *     → drainOutbox() вычитывает ВСЕ готовые pending-строки
 *       (не только ту, что вызвала webhook — см. drainOutbox)
 *     → sendOutboxRow() реально отправляет их в Telegram.
 *
 * Настройка Database Webhook — на стороне Supabase (Database → Webhooks),
 * не в этом файле: событие INSERT на таблице outbox, HTTP POST на
 * https://<этот-worker>.workers.dev/outbox/drain.
 *
 * Известный компромисс: у Supabase Database Webhook нет встроенного
 * retry на уровне доставки самого HTTP-вызова (если Worker в этот момент
 * недоступен — событие один раз потеряется). На практике это не страшно:
 * drainOutbox читает ВСЕ pending-строки с next_retry_at <= now(), а не
 * только ту, что вызвала текущий webhook, поэтому "потерянная" строка
 * всё равно уйдёт при следующем реальном сообщении, которое вызовет
 * drainOutbox заново. Осознанно не добавляем сюда никакого cron —
 * см. предыдущее обсуждение (abuse-flag risk) и явное решение не рисковать.
 *
 * ARCH-change 2026-07 (attachments): the identical ConnectError/ConnectTimeout
 * class was also hitting HF's own getFile/file-download calls for voice and
 * photo messages (see project-root/external/speech_to_text.py and
 * transport/telegram/vision_handler.py, prior to this change) — HF's
 * outbound connection to workers.dev is the unreliable part, regardless of
 * direction. So the rule from the outbox change now applies symmetrically:
 * this Worker downloads voice/photo/document attachments itself (via
 * getFile + file download, both calls it has never shown this failure
 * class on) and uploads them to Supabase Storage BEFORE the update is
 * written to pending_updates (see enqueueUpdate/downloadAndStoreAttachment
 * below). HF then reads the file from Supabase Storage — never from
 * Telegram directly. Combined with the outbox change, this Worker is now
 * the ONLY component that ever talks to api.telegram.org; HF only ever
 * talks to Supabase (pending_updates, outbox, Storage).
 *
 *   POST /webhook       — принимает update от Telegram, кладёт его в очередь
 *                         Supabase (pending_updates) и сразу отвечает 200 OK.
 *                         Worker НЕ ждёт HF Space и не форвардит запрос напрямую —
 *                         обработку забирает async-consumer на стороне HF (poll).
 *   GET|POST /tg/*      — обратный прокси: HF Space → api.telegram.org.
 *                         Оставлен для register_webhook()/setWebhook (см.
 *                         webhook.py) — это разовый вызов при старте, а не
 *                         часть пути отправки сообщений пользователю, так
 *                         что переносить его в outbox смысла нет.
 *   POST /outbox/drain  — вызывается Supabase Database Webhook'ом при
 *                         INSERT в outbox. Запускает drainOutbox().
 *   GET /outbox/health  — счётчик незадренированных строк outbox, для мониторинга.
 *
 * Переменные окружения (Workers Secrets):
 *   WEBHOOK_SECRET          — секрет для проверки запросов от Telegram (опционально)
 *   TELEGRAM_PROXY_TIMEOUT  — таймаут исходящего запроса к api.telegram.org в /tg/*
 *                             и в drainOutbox, в мс (по умолчанию 10000)
 *   HF_TOKEN                — токен HF (опционально, используется в /tg/*)
 *   BOT_TOKEN               — токен Telegram-бота, нужен drainOutbox для
 *                             сборки URL api.telegram.org/bot<token>/...
 *   SUPABASE_URL            — URL проекта Supabase, например https://xxx.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY — service role key (полный доступ, RLS bypass) —
 *                             нужен и для pending_updates, и для outbox,
 *                             т.к. обе таблицы закрыты RLS для anon-ключа
 *   OUTBOX_DRAIN_SECRET     — опциональный секрет для защиты /outbox/drain
 *                             от произвольных вызовов извне (Supabase
 *                             Database Webhook умеет слать кастомный
 *                             заголовок — сверьте с этим значением)
 */

const TELEGRAM_API_BASE = "https://api.telegram.org";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // ── Health check ─────────────────────────────────────────────────────────
    if (path === "/health" && request.method === "GET") {
      return Response.json({ ok: true });
    }

    // ── Outbox monitoring: сколько строк ждут отправки прямо сейчас ──────────
    if (path === "/outbox/health" && request.method === "GET") {
      return handleOutboxHealth(env);
    }

    // ── Вызывается Supabase Database Webhook при INSERT в outbox ─────────────
    if (path === "/outbox/drain" && request.method === "POST") {
      return handleOutboxDrain(request, env, ctx);
    }

    // ── Входящий webhook от Telegram → пересылаем на HF Space ────────────────
    if (path === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env, ctx);
    }

    // ── Исходящий прокси HF Space → Telegram API ─────────────────────────────
    if (path.startsWith("/tg/")) {
      return handleTelegramProxy(request, env, path, url);
    }

    return new Response("Not Found", { status: 404 });
  },
};

async function handleOutboxDrain(request, env, ctx) {
  if (env.OUTBOX_DRAIN_SECRET) {
    const provided = request.headers.get("X-Outbox-Drain-Secret");
    if (provided !== env.OUTBOX_DRAIN_SECRET) {
      return new Response("Forbidden", { status: 403 });
    }
  }
  // Отвечаем сразу — сама отправка идёт в фоне через waitUntil, чтобы
  // Supabase Database Webhook не ждал полного цикла drainOutbox
  // (который может отправлять несколько сообщений последовательно)
  // и не считал вызов неудачным по собственному таймауту.
  ctx.waitUntil(drainOutbox(env));
  return Response.json({ ok: true });
}

// ── Outbox drain: HF writes rows, this reads and actually calls Telegram ────
async function drainOutbox(env) {
  const supabaseUrl = (env.SUPABASE_URL || "").replace(/\/$/, "");
  const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY;
  const botToken = env.BOT_TOKEN;

  if (!supabaseUrl || !serviceKey || !botToken) {
    console.error("drainOutbox skipped: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY or BOT_TOKEN not set");
    return;
  }

  const proxyTimeout = parseInt(env.TELEGRAM_PROXY_TIMEOUT || "10000");
  const BATCH_SIZE = 20;
  const nowIso = new Date().toISOString();

  // Claim: read pending rows whose retry delay has elapsed, then flip them
  // to 'processing' filtered by status='pending' — same claim-then-filter
  // pattern as HF's own queue_consumer.py::_claim_batch, for the same
  // reason (concurrent drains — e.g. two Database Webhook deliveries
  // arriving close together — must not double-send a message).
  let rows;
  try {
    const readResp = await fetch(
      `${supabaseUrl}/rest/v1/outbox?status=eq.pending&next_retry_at=lte.${encodeURIComponent(nowIso)}&order=created_at.asc&limit=${BATCH_SIZE}`,
      {
        headers: {
          "apikey": serviceKey,
          "Authorization": `Bearer ${serviceKey}`,
        },
        signal: AbortSignal.timeout(8000),
      }
    );
    if (!readResp.ok) {
      console.error(`drainOutbox: read failed, status=${readResp.status}`);
      return;
    }
    rows = await readResp.json();
  } catch (err) {
    console.error(`drainOutbox: read error: ${err}`);
    return;
  }

  if (!rows || rows.length === 0) return;

  const ids = rows.map((r) => r.id);
  try {
    const claimResp = await fetch(
      `${supabaseUrl}/rest/v1/outbox?id=in.(${ids.join(",")})&status=eq.pending`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "apikey": serviceKey,
          "Authorization": `Bearer ${serviceKey}`,
          "Prefer": "return=representation",
        },
        body: JSON.stringify({ status: "processing" }),
        signal: AbortSignal.timeout(8000),
      }
    );
    if (!claimResp.ok) {
      console.error(`drainOutbox: claim failed, status=${claimResp.status}`);
      return;
    }
    const claimed = await claimResp.json();
    const claimedIds = new Set(claimed.map((r) => r.id));
    rows = rows.filter((r) => claimedIds.has(r.id));
  } catch (err) {
    console.error(`drainOutbox: claim error: ${err}`);
    return;
  }

  console.log(`drainOutbox: claimed batch, count=${rows.length}`);

  await Promise.all(rows.map((row) => sendOutboxRow(row, env, supabaseUrl, serviceKey, botToken, proxyTimeout)));
}

// Backoff schedule for temporary Telegram errors (429/5xx) — seconds to wait
// before the next attempt, indexed by (current) retry_count. Mirrors the
// shape of HF's own _RETRY_BACKOFF_S in webhook.py, adapted to an
// event-driven Worker: instead of sleeping in-process, we push next_retry_at
// forward and let the next drainOutbox call (triggered by the next real
// message, since there's no cron) pick it back up.
const RETRY_BACKOFF_S = [5, 30, 120, 600, 1800]; // 5s, 30s, 2m, 10m, 30m
const MAX_RETRIES = RETRY_BACKOFF_S.length;

function isTemporaryStatus(status) {
  return status === 429 || (status >= 500 && status < 600);
}

async function sendOutboxRow(row, env, supabaseUrl, serviceKey, botToken, proxyTimeout) {
  const targetUrl = `${TELEGRAM_API_BASE}/bot${botToken}${row.path}`;

  try {
    const { resp, bodyText } = await sendToTelegram(targetUrl, row, proxyTimeout);

    if (resp.ok) {
      console.log(`drainOutbox: sent outbox_id=${row.id}, path=${row.path}, status=${resp.status}`);
      await markOutboxRow(supabaseUrl, serviceKey, row.id, { status: "sent" });
      return;
    }

    // Markdown-parse-error fallback — restores the behavior HF used to do
    // itself in _send_message before the outbox change (see webhook.py's
    // comment on the now-dead-on-HF's-side retry). Requires BOTH the HTTP
    // code and the specific error text, not just "any 400" — a 400 for
    // "chat not found" or "message is too long" would just fail identically
    // a second time without parse_mode, wasting a retry (ChatGPT's point,
    // and a fair one). This check runs BEFORE the temporary-vs-permanent
    // split below because a Markdown parse error is itself a 400, which
    // would otherwise fall straight into "permanent failure".
    const isMarkdownParseError =
      resp.status === 400 &&
      row.json_body &&
      row.json_body.parse_mode === "Markdown" &&
      /can't parse entities/i.test(bodyText);

    if (isMarkdownParseError) {
      console.error(`drainOutbox: Markdown parse error outbox_id=${row.id}, retrying without parse_mode`);
      const plainRow = {
        ...row,
        json_body: { ...row.json_body },
      };
      delete plainRow.json_body.parse_mode;

      const retry = await sendToTelegram(targetUrl, plainRow, proxyTimeout);
      if (retry.resp.ok) {
        console.log(`drainOutbox: sent (no-Markdown retry) outbox_id=${row.id}, status=${retry.resp.status}`);
        await markOutboxRow(supabaseUrl, serviceKey, row.id, {
          status: "sent",
          last_error: "sent without Markdown after parse error",
        });
        return;
      }
      console.error(`drainOutbox: no-Markdown retry also failed outbox_id=${row.id}, status=${retry.resp.status}, body=${retry.bodyText.slice(0, 300)}`);
      await markOutboxRow(supabaseUrl, serviceKey, row.id, {
        status: "failed",
        last_error: `Markdown retry failed — HTTP ${retry.resp.status}: ${retry.bodyText.slice(0, 500)}`,
      });
      return;
    }

    // Temporary vs. permanent split (per ChatGPT's point, which is correct):
    // 429/5xx are worth retrying with backoff, since they resolve on their
    // own with time (rate limit window passes, Telegram's transient issue
    // clears). 400/401/403/404 etc. won't change on retry — same request,
    // same result — so they go straight to 'failed' instead of wasting
    // retry budget on something that cannot succeed.
    if (isTemporaryStatus(resp.status)) {
      const nextRetryCount = (row.retry_count || 0) + 1;
      if (nextRetryCount > MAX_RETRIES) {
        console.error(`drainOutbox: outbox_id=${row.id} exhausted ${MAX_RETRIES} retries, status=${resp.status}`);
        await markOutboxRow(supabaseUrl, serviceKey, row.id, {
          status: "failed",
          last_error: `Exhausted ${MAX_RETRIES} retries — last HTTP ${resp.status}: ${bodyText.slice(0, 500)}`,
        });
        return;
      }
      const delaySec = RETRY_BACKOFF_S[nextRetryCount - 1];
      const nextRetryAt = new Date(Date.now() + delaySec * 1000).toISOString();
      console.error(
        `drainOutbox: temporary failure outbox_id=${row.id}, status=${resp.status}, ` +
        `retry ${nextRetryCount}/${MAX_RETRIES} scheduled in ${delaySec}s`
      );
      await markOutboxRow(supabaseUrl, serviceKey, row.id, {
        status: "pending",
        retry_count: nextRetryCount,
        next_retry_at: nextRetryAt,
        last_error: `HTTP ${resp.status}: ${bodyText.slice(0, 500)}`,
      });
      return;
    }

    // Permanent failure (400 non-Markdown, 401, 403, 404, ...) — no retry.
    console.error(`drainOutbox: Telegram rejected outbox_id=${row.id}, status=${resp.status}, body=${bodyText.slice(0, 300)}`);
    await markOutboxRow(supabaseUrl, serviceKey, row.id, {
      status: "failed",
      last_error: `HTTP ${resp.status}: ${bodyText.slice(0, 500)}`,
    });
  } catch (err) {
    // Network-level failure (timeout, DNS, connection reset) — treated the
    // same as a temporary Telegram error: back to 'pending' with backoff,
    // not an immediate 'failed'. Mirrors HF's own _mark_failed/MAX_ATTEMPTS
    // shape in queue_consumer.py.
    const nextRetryCount = (row.retry_count || 0) + 1;
    if (nextRetryCount > MAX_RETRIES) {
      console.error(`drainOutbox: outbox_id=${row.id} exhausted ${MAX_RETRIES} retries after network errors, last error=${err}`);
      await markOutboxRow(supabaseUrl, serviceKey, row.id, {
        status: "failed",
        last_error: `Exhausted ${MAX_RETRIES} retries — last error: ${String(err)}`,
      });
      return;
    }
    const delaySec = RETRY_BACKOFF_S[nextRetryCount - 1];
    const nextRetryAt = new Date(Date.now() + delaySec * 1000).toISOString();
    console.error(`drainOutbox: send error outbox_id=${row.id}, error=${err}, retry ${nextRetryCount}/${MAX_RETRIES} in ${delaySec}s`);
    await markOutboxRow(supabaseUrl, serviceKey, row.id, {
      status: "pending",
      retry_count: nextRetryCount,
      next_retry_at: nextRetryAt,
      last_error: String(err),
    });
  }
}

async function sendToTelegram(targetUrl, row, proxyTimeout) {
  let fetchOptions;
  if (row.files_b64) {
    // Voice messages: rebuild multipart/form-data from the base64 payload
    // HF encoded (see webhook.py::_post_via_worker — PostgREST has no
    // native multipart support, hence base64 over JSON).
    const form = new FormData();
    if (row.form_data) {
      for (const [k, v] of Object.entries(row.form_data)) form.append(k, String(v));
    }
    for (const [field, file] of Object.entries(row.files_b64)) {
      const bytes = Uint8Array.from(atob(file.data_b64), (c) => c.charCodeAt(0));
      form.append(field, new Blob([bytes], { type: file.content_type }), file.filename);
    }
    fetchOptions = { method: "POST", body: form };
  } else {
    fetchOptions = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(row.json_body || row.form_data || {}),
    };
  }
  fetchOptions.signal = AbortSignal.timeout(proxyTimeout);

  const resp = await fetch(targetUrl, fetchOptions);
  const bodyText = await resp.text().catch(() => "");
  return { resp, bodyText };
}

async function markOutboxRow(supabaseUrl, serviceKey, id, fields) {
  const { status, last_error = null, retry_count, next_retry_at } = fields;
  const body = {
    status,
    last_error,
    completed_at: status === "sent" || status === "failed" ? new Date().toISOString() : null,
  };
  if (retry_count !== undefined) body.retry_count = retry_count;
  if (next_retry_at !== undefined) body.next_retry_at = next_retry_at;

  try {
    await fetch(`${supabaseUrl}/rest/v1/outbox?id=eq.${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "apikey": serviceKey,
        "Authorization": `Bearer ${serviceKey}`,
        "Prefer": "return=minimal",
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(8000),
    });
  } catch (err) {
    console.error(`markOutboxRow failed: id=${id}, error=${err}`);
  }
}

async function handleOutboxHealth(env) {
  const supabaseUrl = (env.SUPABASE_URL || "").replace(/\/$/, "");
  const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceKey) {
    return Response.json({ ok: false, error: "not configured" }, { status: 500 });
  }
  try {
    const resp = await fetch(`${supabaseUrl}/rest/v1/outbox?status=eq.pending&select=id`, {
      headers: {
        "apikey": serviceKey,
        "Authorization": `Bearer ${serviceKey}`,
        "Prefer": "count=exact",
      },
      signal: AbortSignal.timeout(8000),
    });
    const countHeader = resp.headers.get("content-range"); // "0-9/23"
    const pendingCount = countHeader ? parseInt(countHeader.split("/")[1]) : null;
    return Response.json({ ok: true, pending_count: pendingCount });
  } catch (err) {
    return Response.json({ ok: false, error: String(err) }, { status: 502 });
  }
}

async function handleWebhook(request, env, ctx) {
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");

  if (env.WEBHOOK_SECRET && secret !== env.WEBHOOK_SECRET) {
    return new Response("Forbidden", { status: 403 });
  }

  let update;
  try {
    update = await request.json();
  } catch (err) {
    console.error(`Failed to parse Telegram update JSON: error=${err}`);
    // Отвечаем 200, чтобы Telegram не долбил нас повторами битого тела.
    return Response.json({ ok: true });
  }

  // ── Кладём апдейт в очередь Supabase и сразу отвечаем ────────────────────
  // Worker больше НЕ ждёт HF Space: ни forward, ни retry, ни wake-up пинга.
  // INSERT в Supabase — это единственная операция на критическом пути,
  // и она занимает обычно 50-200ms, что несравнимо с холодным стартом HF
  // (который мог доходить до 20-30s и упирался в лимит воркера).
  // update_id уникален (constraint в БД) — если Telegram продублирует
  // апдейт, повторный INSERT просто будет молча проигнорирован (upsert
  // с ignoreDuplicates), а не упадёт с ошибкой.
  ctx.waitUntil(enqueueUpdate(env, update));

  return Response.json({ ok: true });
}

async function enqueueUpdate(env, update) {
  const supabaseUrl = (env.SUPABASE_URL || "").replace(/\/$/, "");
  const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !serviceKey) {
    console.error("enqueueUpdate skipped: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set");
    return;
  }

  const insertTimeout = parseInt(env.SUPABASE_INSERT_TIMEOUT || "8000");

  // ARCH-change 2026-07 (attachments): same reasoning as the outbox change,
  // applied to the opposite direction. HF's own getFile/file-download calls
  // (see project-root/external/speech_to_text.py::download_telegram_voice
  // and transport/telegram/vision_handler.py::_download_image_via_worker)
  // showed the identical ConnectError/ConnectTimeout as the original
  // sendMessage incident — HF's outbound connection to workers.dev is the
  // unreliable part, regardless of direction. So the Worker now downloads
  // any voice/photo/document attachment itself (it has never shown this
  // failure class) and uploads it to Supabase Storage BEFORE the update is
  // enqueued. HF then reads the file from Supabase (stable) instead of
  // calling Telegram at all for attachments — mirroring outbox's "HF only
  // ever talks to Supabase" rule, now enforced in both directions.
  const attachment = extractAttachmentRef(update);
  if (attachment) {
    const uploaded = await downloadAndStoreAttachment(env, supabaseUrl, serviceKey, attachment);
    if (uploaded) {
      update = {
        ...update,
        _attachment: uploaded, // { bucket, path, mime_type, size, file_id, kind }
      };
    } else {
      // Download/upload failed after retries — still enqueue the update
      // (so the text/caption path and user-facing error message still
      // work) but WITHOUT _attachment. HF's handlers already have a
      // graceful "couldn't read attachment" fallback for a missing/failed
      // download (see vision_handler.py / update_handler.py's existing
      // error paths) — this preserves that behavior instead of silently
      // dropping the whole update.
      console.error(`enqueueUpdate: attachment download/upload failed for update_id=${update.update_id}, kind=${attachment.kind}`);
    }
  }

  try {
    const resp = await fetch(`${supabaseUrl}/rest/v1/pending_updates`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "apikey": serviceKey,
        "Authorization": `Bearer ${serviceKey}`,
        // on_conflict + resolution=ignore-duplicates → безопасный upsert:
        // если update_id уже существует (дубль от Telegram), просто
        // ничего не делаем, вместо ошибки 409.
        "Prefer": "resolution=ignore-duplicates,return=minimal",
      },
      body: JSON.stringify({
        update_id: update.update_id,
        payload: update,
      }),
      signal: AbortSignal.timeout(insertTimeout),
    });

    if (!resp.ok && resp.status !== 409) {
      const bodyText = await resp.text().catch(() => "");
      console.error(`enqueueUpdate failed: status=${resp.status}, body=${bodyText.slice(0, 300)}`);
      return;
    }

    console.log(`Enqueued update_id=${update.update_id}, status=${resp.status}`);
  } catch (err) {
    console.error(`enqueueUpdate error: update_id=${update.update_id}, error=${err}`);
  }
}

// Pull out the one attachment we care about from a Telegram update, if any.
// Telegram sends photo as an array of sizes — we take the largest, same
// choice HF's own vision_handler used to make implicitly via file_id.
function extractAttachmentRef(update) {
  const msg = update.message || update.edited_message;
  if (!msg) return null;

  if (msg.voice) {
    return { kind: "voice", file_id: msg.voice.file_id, mime_type: msg.voice.mime_type || "audio/ogg" };
  }
  if (msg.photo && msg.photo.length > 0) {
    const largest = msg.photo[msg.photo.length - 1];
    return { kind: "photo", file_id: largest.file_id, mime_type: "image/jpeg" };
  }
  if (msg.document) {
    return { kind: "document", file_id: msg.document.file_id, mime_type: msg.document.mime_type || "application/octet-stream" };
  }
  return null;
}

async function downloadAndStoreAttachment(env, supabaseUrl, serviceKey, attachment) {
  const botToken = env.BOT_TOKEN;
  if (!botToken) {
    console.error("downloadAndStoreAttachment skipped: BOT_TOKEN not set");
    return null;
  }
  const proxyTimeout = parseInt(env.TELEGRAM_PROXY_TIMEOUT || "10000");
  const RETRIES = 2;

  for (let attempt = 0; attempt <= RETRIES; attempt++) {
    try {
      // Step 1: getFile → file_path. Worker calls api.telegram.org directly —
      // this is the same host Worker already talks to for sendMessage, and
      // has never shown the ConnectError HF's own calls did.
      const getFileResp = await fetch(
        `${TELEGRAM_API_BASE}/bot${botToken}/getFile?file_id=${encodeURIComponent(attachment.file_id)}`,
        { signal: AbortSignal.timeout(proxyTimeout) }
      );
      if (!getFileResp.ok) {
        throw new Error(`getFile HTTP ${getFileResp.status}`);
      }
      const getFileData = await getFileResp.json();
      const filePath = getFileData?.result?.file_path;
      if (!filePath) {
        throw new Error("getFile returned no file_path");
      }

      // Step 2: download the actual bytes.
      const fileResp = await fetch(`${TELEGRAM_API_BASE}/file/bot${botToken}/${filePath}`, {
        signal: AbortSignal.timeout(proxyTimeout),
      });
      if (!fileResp.ok) {
        throw new Error(`file download HTTP ${fileResp.status}`);
      }
      const bytes = await fileResp.arrayBuffer();

      // Step 3: upload to Supabase Storage. Bucket layout: voice/, photo/,
      // document/ — matches the recommendation to keep attachments out of
      // Postgres rows entirely (pending_updates only ever stores the
      // pointer: bucket + path + mime_type + size).
      const bucket = "telegram-attachments";
      const ext = filePath.split(".").pop() || "bin";
      const storagePath = `${attachment.kind}/${attachment.file_id}.${ext}`;

      const uploadResp = await fetch(
        `${supabaseUrl}/storage/v1/object/${bucket}/${storagePath}`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${serviceKey}`,
            "Content-Type": attachment.mime_type,
            "x-upsert": "true", // retries on the same attempt overwrite cleanly instead of erroring on "already exists"
          },
          body: bytes,
          signal: AbortSignal.timeout(proxyTimeout),
        }
      );
      if (!uploadResp.ok) {
        const bodyText = await uploadResp.text().catch(() => "");
        throw new Error(`Storage upload HTTP ${uploadResp.status}: ${bodyText.slice(0, 300)}`);
      }

      console.log(`downloadAndStoreAttachment: stored kind=${attachment.kind}, file_id=${attachment.file_id}, size=${bytes.byteLength}`);
      return {
        bucket,
        path: storagePath,
        mime_type: attachment.mime_type,
        size: bytes.byteLength,
        file_id: attachment.file_id,
        kind: attachment.kind,
      };
    } catch (err) {
      const isLastAttempt = attempt === RETRIES;
      const logFn = isLastAttempt ? console.error : console.warn;
      logFn(`downloadAndStoreAttachment attempt=${attempt + 1} failed: kind=${attachment.kind}, file_id=${attachment.file_id}, error=${err}`);
      if (!isLastAttempt) {
        await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
      }
    }
  }
  return null;
}

async function handleTelegramProxy(request, env, path, url) {
  // /tg/bot<token>/sendMessage → https://api.telegram.org/bot<token>/sendMessage
  const tgPath = path.slice(3); // убираем /tg, оставляя ведущий слэш
  let targetUrl = `${TELEGRAM_API_BASE}${tgPath}`;
  if (url.search) targetUrl += url.search;

  const body = request.method !== "GET" ? await request.arrayBuffer() : undefined;
  const contentType = request.headers.get("content-type") || "application/json";

  // Явный таймаут — без него зависший fetch к Telegram может висеть
  // неопределённо долго, а вызывающая сторона (HF) увидит только свой
  // собственный httpx-таймаут без понимания, что произошло на стороне Worker.
  const proxyTimeout = parseInt(env.TELEGRAM_PROXY_TIMEOUT || "10000");

  const startedAt = Date.now();
  try {
    const resp = await fetch(targetUrl, {
      method: request.method,
      headers: { "Content-Type": contentType },
      body,
      signal: AbortSignal.timeout(proxyTimeout),
    });

    console.log(`Telegram proxy ok: path=${tgPath}, status=${resp.status}, elapsed_ms=${Date.now() - startedAt}`);

    return new Response(resp.body, {
      status: resp.status,
      headers: { "Content-Type": resp.headers.get("content-type") || "application/json" },
    });
  } catch (err) {
    const elapsed = Date.now() - startedAt;
    const isTimeout = err.name === "TimeoutError" || err.name === "AbortError";
    console.error(
      `Telegram proxy failed: path=${tgPath}, elapsed_ms=${elapsed}, timeout=${isTimeout}, error=${err}`
    );
    return new Response(
      JSON.stringify({
        ok: false,
        error: isTimeout ? "upstream timeout" : "upstream failed",
        elapsed_ms: elapsed,
      }),
      {
        status: isTimeout ? 504 : 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}