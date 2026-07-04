/**
 * Ceyona Webhook Worker
 *
 * Два HTTP-маршрута + один Cron Trigger:
 *   POST /webhook      — принимает update от Telegram, пересылает на HF Space
 *   GET|POST /tg/*     — обратный прокси: HF Space → api.telegram.org
 *   scheduled()        — Cron: периодический keep-alive пинг HF Space
 *                         (снижает вероятность холодного старта, не устраняет)
 *
 * Переменные окружения (Workers Secrets):
 *   HF_WEBHOOK_URL          — URL HF Space, например https://your-space.hf.space
 *   WEBHOOK_SECRET          — секрет для проверки запросов от Telegram (опционально)
 *   FORWARD_TIMEOUT         — таймаут одной попытки forwarding в мс (по умолчанию 45000)
 *   TELEGRAM_PROXY_TIMEOUT  — таймаут исходящего запроса к api.telegram.org в /tg/*
 *                             в мс (по умолчанию 10000)
 *   HF_TOKEN                — токен HF (опционально)
 *
 * Cron Trigger (расписание раз в 10 минут) настраивается отдельно
 * в wrangler.toml под ключом [triggers].
 */

const TELEGRAM_API_BASE = "https://api.telegram.org";

// Количество попыток и начальная пауза между ними.
// HF Space на бесплатном тарифе может "спать" после длительного простоя
// (официально Hugging Face не публикует точное время холодного старта —
// оно зависит от размера образа и зависимостей приложения) и не успевать
// ответить с первой попытки. MAX_RETRIES=1 означало, что при таймауте
// на первой попытке апдейт просто терялся без единого повтора.
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY_MS = 3000; // 3s → 6s

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
  // холодного старта именно в момент, когда приходит реальное сообщение
  // от пользователя. Worker всё равно должен уметь пережить cold start
  // (см. wake-up пинг + retry в forwardToHF) — cron лишь смягчает частоту,
  // а не устраняет саму возможность.
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

  // Читаем тело один раз — оно понадобится при каждой попытке
  const body = await request.arrayBuffer();
  const timeout = parseInt(env.FORWARD_TIMEOUT || "45000");
  const hfBase = env.HF_WEBHOOK_URL.replace(/\/$/, "");
  const hfUrl = hfBase + "/webhook";

  const headers = { "Content-Type": "application/json" };
  if (secret) headers["X-Telegram-Bot-Api-Secret-Token"] = secret;
  if (env.HF_TOKEN) headers["Authorization"] = `Bearer ${env.HF_TOKEN}`;

  // ── Отвечаем Telegram НЕМЕДЛЕННО ──────────────────────────────────────────
  // Telegram ждёт ответ на webhook ограниченное время (обычно порядка секунд,
  // до ~60s), после чего сам считает доставку неуспешной и повторяет апдейт.
  // При MAX_RETRIES=2 и FORWARD_TIMEOUT=45000 весь цикл форвардинга может
  // занимать почти 100 секунд — если ждать его синхронно, Telegram успеет
  // решить, что мы не ответили, и продублирует апдейт, что приведёт к двойной
  // обработке одного сообщения. Поэтому подтверждаем webhook сразу, а сам
  // форвардинг (с прогревом и ретраями) выполняем в фоне через ctx.waitUntil.
  ctx.waitUntil(forwardToHF(hfBase, hfUrl, body, headers, timeout));

  return Response.json({ ok: true });
}

async function forwardToHF(hfBase, hfUrl, body, headers, timeout) {
  // ── Wake-up: будим Space коротким GET перед основным запросом ────────────
  // Если Space "спал", этот GET запускает прогрев; основной POST пойдёт,
  // когда Space уже отвечает (или после отдельного keep-alive пинга, см.
  // scheduled() ниже, который снижает саму вероятность того, что Space
  // вообще успеет заснуть).
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
      return;

    } catch (err) {
      lastError = err;
      console.error(`Forward to HF failed: attempt=${attempt}/${MAX_RETRIES}, error=${err}`);

      if (attempt < MAX_RETRIES) {
        // Экспоненциальная пауза: 3s, 6s …
        const delay = RETRY_BASE_DELAY_MS * Math.pow(2, attempt - 1);
        console.log(`Retrying in ${delay}ms...`);
        await sleep(delay);
      }
    }
  }

  // Все попытки исчерпаны — апдейт потерян, логируем для диагностики.
  console.error(`All ${MAX_RETRIES} attempts failed. Last error: ${lastError}`);
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