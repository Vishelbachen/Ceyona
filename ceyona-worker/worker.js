/**
 * Ceyona Webhook Worker
 *
 * Два HTTP-маршрута + один Cron Trigger:
 *   POST /webhook      — принимает update от Telegram, кладёт его в очередь
 *                         Supabase (pending_updates) и сразу отвечает 200 OK.
 *                         Worker НЕ ждёт HF Space и не форвардит запрос напрямую —
 *                         обработку забирает async-consumer на стороне HF (poll).
 *                         Это убирает риск упереться в 30s wall-time лимит Worker'а
 *                         из-за медленного/холодного HF Space (см. ARCH: push-queue).
 *   GET|POST /tg/*     — обратный прокси: HF Space → api.telegram.org
 *   scheduled()        — Cron: периодический keep-alive пинг HF Space
 *                         (снижает вероятность холодного старта, не устраняет)
 *
 * Переменные окружения (Workers Secrets):
 *   HF_WEBHOOK_URL          — URL HF Space, например https://your-space.hf.space
 *                             (используется только для keep-alive пинга /health)
 *   WEBHOOK_SECRET          — секрет для проверки запросов от Telegram (опционально)
 *   TELEGRAM_PROXY_TIMEOUT  — таймаут исходящего запроса к api.telegram.org в /tg/*
 *                             в мс (по умолчанию 10000)
 *   HF_TOKEN                — токен HF (опционально, используется в /tg/* и cron)
 *   SUPABASE_URL            — URL проекта Supabase, например https://xxx.supabase.co
 *   SUPABASE_SERVICE_ROLE_KEY — service role key (полный доступ, RLS bypass) —
 *                             нужен, т.к. таблица pending_updates закрыта RLS
 *                             для anon-ключа
 *
 * Cron Trigger (расписание раз в 10 минут) настраивается отдельно
 * в wrangler.toml под ключом [triggers].
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

  // ── Cron Trigger: периодический keep-alive пинг HF Space ──────────────────
  // Настраивается в wrangler.toml через [triggers] crons = ["*/10 * * * *"]
  // (пример: раз в 10 минут). Это НЕ гарантирует, что Space никогда не
  // заснёт — HF управляет этим на своей стороне — но резко снижает шанс
  // холодного старта к моменту, когда HF-consumer пойдёт вычитывать очередь.
  // С push-queue архитектурой (см. handleWebhook/enqueueUpdate) Worker уже
  // не зависит от того, ответит ли HF вовремя — но чем реже HF спит, тем
  // быстрее пользователь получает ответ, поэтому cron остаётся полезным.
  async scheduled(event, env, ctx) {
    const hfBase = (env.HF_WEBHOOK_URL || "").replace(/\/$/, "");
    if (!hfBase) {
      console.error("Cron keep-alive skipped: HF_WEBHOOK_URL not set");
      return;
    }
    ctx.waitUntil(
      (async () => {
        try {
          const resp = await fetch(hfBase + "/health", {
            method: "GET",
            signal: AbortSignal.timeout(10000),
          });
          console.log(`Cron keep-alive ping: status=${resp.status}`);
        } catch (err) {
          console.error(`Cron keep-alive ping failed: error=${err}`);
        }
      })()
    );
  },
};

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