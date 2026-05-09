Downloads a Telegram photo and sends it to a Groq vision model for analysis.

Vision model used: meta-llama/llama-4-maverick-17b-128e-instruct — supports
image + text input via Groq's OpenAI-compatible API.

Flow:
  1. Get file path from Telegram Bot API (getFile)
  2. Download the image bytes
  3. Base64-encode the image
  4. Send to Groq vision model with user caption (if any)
  5. Return the model's text response
"""
from __future__ import annotations

import base64
import logging

import httpx
from groq import AsyncGroq

from app.settings import settings

logger = logging.getLogger(__name__)

# Vision model — supports image input on Groq
_VISION_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"
_TIMEOUT = 20.0


async def _get_file_url(file_id: str) -> str | None:
    """Resolve a Telegram file_id to a download URL."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{_TELEGRAM_API}/getFile",
                params={"file_id": file_id},
            )
            r.raise_for_status()
            data = r.json()
            file_path = data.get("result", {}).get("file_path", "")
            if not file_path:
                return None
            return f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"
    except Exception as exc:
        logger.error("getFile failed", extra={"file_id": file_id, "error": str(exc)})
        return None


async def _download_image(url: str) -> bytes | None:
    """Download image bytes from Telegram CDN."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
    except Exception as exc:
        logger.error("Image download failed", extra={"url": url, "error": str(exc)})
        return None


def _build_vision_messages(
    image_b64: str,
    caption: str,
    lang: str,
) -> list[dict]:
    """
    Build the messages list for the Groq vision API call.
    Uses OpenAI-compatible image_url content block with base64 data URI.
    """
    lang_instructions = {
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
    lang_instr = lang_instructions.get(lang, "Reply in the same language the user wrote in.")

    system_content = (
        "You are a powerful vision assistant. "
        "You can fully analyze, read text from, describe, and understand any image. "
        "Examine the image carefully and provide a detailed, accurate response. "
        "If the image contains text, read it completely. "
        "If there is a question or task in the caption, answer it using the image. "
        f"{lang_instr}"
    )

    user_text = caption.strip() if caption.strip() else "Describe this image in detail."

    return [
        {"role": "system", "content": system_content},
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
    ]


async def handle_vision(
    file_id: str,
    caption: str = "",
    lang: str = "en",
) -> str:
    """
    Full pipeline: file_id → download → base64 → Groq vision → text response.

    Returns the model's response string, or an error message in user's language.
    """
    _error_msgs = {
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
    error_msg = _error_msgs.get(lang, _error_msgs["en"])

    # 1. Resolve file_id → download URL
    file_url = await _get_file_url(file_id)
    if not file_url:
        logger.error("Could not resolve file_id to URL", extra={"file_id": file_id})
        return error_msg

    # 2. Download image bytes
    image_bytes = await _download_image(file_url)
    if not image_bytes:
        return error_msg

    # 3. Base64-encode
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # 4. Build messages and call Groq vision
    messages = _build_vision_messages(image_b64, caption, lang)

    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await client.chat.completions.create(
            model=_VISION_MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
        )
        result_text = response.choices[0].message.content or ""
        logger.info(
            "Vision analysis complete",
            extra={
                "lang": lang,
                "caption_len": len(caption),
                "response_len": len(result_text),
            },
        )
        return result_text

    except Exception as exc:
        logger.error("Groq vision call failed", extra={"error": str(exc)})
        return error_msg