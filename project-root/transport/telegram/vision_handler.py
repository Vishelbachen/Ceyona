Downloads a Telegram photo and sends it to a Groq vision model for analysis.

Vision model: meta-llama/llama-4-maverick-17b-128e-instruct
API: Groq OpenAI-compatible REST endpoint (httpx, not SDK — avoids Pydantic validation
     issues with image_url content blocks in older SDK versions).

Flow:
  1. getFile — resolve file_id to a download path
  2. Download image bytes from Telegram CDN
  3. Base64-encode
  4. POST to Groq /openai/v1/chat/completions with image_url content block
  5. Return model response text
"""
from __future__ import annotations

import base64
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_VISION_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT = 30.0


def _telegram_api(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


async def _get_file_url(file_id: str) -> str | None:
    """Resolve Telegram file_id to a direct download URL."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                _telegram_api("getFile"),
                params={"file_id": file_id},
            )
            r.raise_for_status()
            data = r.json()
            file_path = data.get("result", {}).get("file_path", "")
            if not file_path:
                logger.error("getFile returned no file_path", extra={"file_id": file_id})
                return None
            return (
                f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"
            )
    except Exception as exc:
        logger.error("getFile failed", extra={"file_id": file_id, "error": str(exc)})
        return None


async def _download_image(url: str) -> bytes | None:
    """Download raw image bytes from Telegram CDN."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
    except Exception as exc:
        logger.error("Image download failed", extra={"url": url[:80], "error": str(exc)})
        return None


def _lang_instruction(lang: str) -> str:
    mapping = {
        "ru": "Отвечай ТОЛЬКО на русском языке.",
        "en": "Reply ONLY in English.",
        "de": "Antworte NUR auf Deutsch.",
        "fr": "Réponds UNIQUEMENT en français.",
        "es": "Responde SÓLO en español.",
        "uk": "Відповідай ТІЛЬКИ українською мовою.",
        "tr": "YALNIZCA Türkçe yanıtla.",
        "ar": "أجب باللغة العربية فقط.",
        "zh": "只用中文回答。",
        "ja": "日本語のみで答えてください。",
        "ko": "한국어로만 답하세요.",
        "pl": "Odpowiadaj TYLKO po polsku.",
        "it": "Rispondi SOLO in italiano.",
        "pt": "Responda APENAS em português.",
        "fa": "فقط به فارسی پاسخ بده.",
    }
    return mapping.get(lang, "Reply in the same language the user wrote in.")


def _error_msg(lang: str) -> str:
    mapping = {
        "ru": "❌ Не удалось обработать изображение. Попробуйте ещё раз.",
        "en": "❌ Failed to process the image. Please try again.",
        "de": "❌ Bild konnte nicht verarbeitet werden. Bitte erneut versuchen.",
        "fr": "❌ Impossible de traiter l'image. Veuillez réessayer.",
        "es": "❌ No se pudo procesar la imagen. Inténtelo de nuevo.",
        "uk": "❌ Не вдалося обробити зображення. Спробуйте ще раз.",
        "tr": "❌ Görüntü işlenemedi. Lütfen tekrar deneyin.",
        "ar": "❌ تعذّر معالجة الصورة. يرجى المحاولة مرة أخرى.",
        "zh": "❌ 无法处理图片，请重试。",
        "ja": "❌ 画像を処理できませんでした。もう一度お試しください。",
        "ko": "❌ 이미지를 처리할 수 없습니다. 다시 시도하세요.",
        "pl": "❌ Nie udało się przetworzyć obrazu. Spróbuj ponownie.",
        "it": "❌ Impossibile elaborare l'immagine. Riprova.",
        "pt": "❌ Não foi possível processar a imagem. Tente novamente.",
        "fa": "❌ پردازش تصویر ناموفق بود. لطفاً دوباره امتحان کنید.",
    }
    return mapping.get(lang, mapping["en"])


async def handle_vision(
    file_id: str,
    caption: str = "",
    lang: str = "en",
) -> str:
    """
    Full pipeline: file_id → download → base64 → Groq vision → response text.
    Uses raw httpx POST to Groq REST API to avoid SDK Pydantic validation issues.
    """
    err = _error_msg(lang)

    # 1. Resolve file_id → download URL
    file_url = await _get_file_url(file_id)
    if not file_url:
        return err

    # 2. Download image
    image_bytes = await _download_image(file_url)
    if not image_bytes:
        return err

    # 3. Base64-encode
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # 4. Build request payload (OpenAI-compatible, Groq vision format)
    user_text = caption.strip() if caption.strip() else "Describe this image in detail."

    payload = {
        "model": _VISION_MODEL,
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a powerful vision assistant. "
                    "Analyze images thoroughly: read all text, describe contents, "
                    "answer questions based on what you see. "
                    "Be accurate and detailed. "
                    + _lang_instruction(lang)
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": user_text,
                    },
                ],
            },
        ],
    }

    # 5. Call Groq REST API directly via httpx
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                _GROQ_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
            )
            r.raise_for_status()
            data = r.json()
            result_text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not result_text:
                logger.error("Groq vision returned empty content", extra={"data": str(data)[:200]})
                return err

            logger.info("Vision analysis complete", extra={
                "lang": lang,
                "caption_len": len(caption),
                "response_len": len(result_text),
            })
            return result_text

    except httpx.HTTPStatusError as exc:
        logger.error("Groq vision HTTP error", extra={
            "status": exc.response.status_code,
            "body": exc.response.text[:300],
        })
        return err
    except Exception as exc:
        logger.error("Groq vision call failed", extra={"error": str(exc)})
        return err
