/**
 * Ceyona Webhook Worker
 *
 * Два маршрута:
 *   POST /webhook      — принимает update от Telegram, пересылает на HF Space
 *   GET|POST /tg/*     — обратный прокси: HF Space → api.telegram.org
 *
 * Переменные окружения (Workers Secrets):
 *   HF_WEBHOOK_URL          — URL HF Space, например https://your-space.hf.space
 *   WEBHOOK_SECRET          — секрет для проверки запросов от Telegram (опционально)
 *   FORWARD_TIMEOUT         — таймаут одной попытки forwarding в мс (по умолчанию 45000)
 *   TELEGRAM_PROXY_TIMEOUT  — таймаут исходящего запроса к api.telegram.org в /tg/*
 *                             в мс (по умолчанию 10000)
 *   HF_TOKEN                — токен HF (опционально)
 */

const TELEGRAM_API_BASE = "https://api.telegram.org";

// Количество попыток и начальная пауза между ними
const MAX_RETRIES = 1;
const RETRY_BASE_DELAY_MS = 3000; // 3s → 6s → 12s

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // ── Health check ─────────────────────────────────────────────────────────
    if (path === "/health" && request.method === "GET") {
      return Response.json({ ok: true });
    }

    // ── Входящий webhook от Telegram → пересылаем на HF Space ────────────────
    if (path === "/webhook" && request.method === "POST") {
      return handleWebhook(request, env);
    }

    // ── Исходящий прокси HF Space → Telegram API ─────────────────────────────
    if (path.startsWith("/tg/")) {
      return handleTelegramProxy(request, env, path, url);
    }

    return new Response("Not Found", { status: 404 });
  },
};

async function handleWebhook(request, env) {
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");

  if (env.WEBHOOK_SECRET && secret !== env.WEBHOOK_SECRET) {
    return new Response("Forbidden", { status: 403 });
  }

  // Читаем тело один раз — оно понадобится при каждой попытке
  const body = await request.arrayBuffer();
  const timeout = parseInt(env.FORWARD_TIMEOUT || "45000");
  const hfBase = env.HF_WEBHOOK_URL.replace(/\/$/, "");
  const hfUrl = hfBase + "/webhook";

  const headers = { "Content-Type": "application/json" };
  if (secret) headers["X-Telegram-Bot-Api-Secret-Token"] = secret;
  if (env.HF_TOKEN) headers["Authorization"] = `Bearer ${env.HF_TOKEN}`;

  // ── Wake-up: будим Space коротким GET перед основным запросом ────────────
  // HF Space после сна отвечает на первый запрос с задержкой 20-40s.
  // Этот GET запускает прогрев; основной POST пойдёт, когда Space уже живой.
  try {
    await fetch(hfBase + "/health", {
      method: "GET",
      signal: AbortSignal.timeout(5000), // не ждём долго — это только пинг
    });
  } catch (_) {
    // Игнорируем — Space мог ещё не встать, это нормально
  }

  // ── Retry loop ───────────────────────────────────────────────────────────
  let lastError;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const resp = await fetch(hfUrl, {
        method: "POST",
        headers,
        body,
        signal: AbortSignal.timeout(timeout),
      });

      console.log(`Forwarded to HF, attempt=${attempt}, status=${resp.status}`);

      // Всегда отвечаем Telegram OK — он не должен делать повторы сам
      return Response.json({ ok: true });

    } catch (err) {
      lastError = err;
      console.error(`Forward to HF failed: attempt=${attempt}/${MAX_RETRIES}, error=${err}`);

      if (attempt < MAX_RETRIES) {
        // Экспоненциальная пауза: 3s, 6s, 12s …
        const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
        console.log(`Retrying in ${delay}ms...`);
        await sleep(delay);
      }
    }
  }

  // Все попытки исчерпаны — логируем, но всё равно говорим Telegram OK
  console.error(`All ${MAX_RETRIES} attempts failed. Last error: ${lastError}`);
  return Response.json({ ok: true });
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}