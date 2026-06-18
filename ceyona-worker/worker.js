/**
 * Ceyona Webhook Worker
 *
 * Два маршрута:
 *   POST /webhook      — принимает update от Telegram, пересылает на HF Space
 *   GET|POST /tg/*     — обратный прокси: HF Space → api.telegram.org
 *
 * Переменные окружения (Workers Secrets):
 *   HF_WEBHOOK_URL     — URL HF Space, например https://your-space.hf.space
 *   WEBHOOK_SECRET     — секрет для проверки запросов от Telegram (опционально)
 *   FORWARD_TIMEOUT    — таймаут в мс (по умолчанию 20000)
 */

const TELEGRAM_API_BASE = "https://api.telegram.org";

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

  const hfUrl = env.HF_WEBHOOK_URL.replace(/\/$/, "") + "/webhook";
  const body = await request.arrayBuffer();
  const timeout = parseInt(env.FORWARD_TIMEOUT || "20000");

  const headers = { "Content-Type": "application/json" };
  if (secret) headers["X-Telegram-Bot-Api-Secret-Token"] = secret;
  if (env.HF_TOKEN) headers["Authorization"] = `Bearer ${env.HF_TOKEN}`;

  try {
    const resp = await fetch(hfUrl, {
      method: "POST",
      headers,
      body,
      signal: AbortSignal.timeout(timeout),
    });
    console.log(`Forwarded to HF, status=${resp.status}`);
  } catch (err) {
    // Всегда отвечаем Telegram OK, чтобы он не делал повторные попытки
    console.error(`Forward to HF failed: ${err}`);
  }

  return Response.json({ ok: true });
}

async function handleTelegramProxy(request, env, path, url) {
  // /tg/bot<token>/sendMessage → https://api.telegram.org/bot<token>/sendMessage
  const tgPath = path.slice(3); // убираем /tg, оставляя ведущий слэш
  let targetUrl = `${TELEGRAM_API_BASE}${tgPath}`;
  if (url.search) targetUrl += url.search;

  const body = request.method !== "GET" ? await request.arrayBuffer() : undefined;
  const contentType = request.headers.get("content-type") || "application/json";

  try {
    const resp = await fetch(targetUrl, {
      method: request.method,
      headers: { "Content-Type": contentType },
      body,
    });

    return new Response(resp.body, {
      status: resp.status,
      headers: { "Content-Type": resp.headers.get("content-type") || "application/json" },
    });
  } catch (err) {
    console.error(`Telegram proxy failed: ${err}`);
    return new Response(JSON.stringify({ ok: false, error: "upstream failed" }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }
}