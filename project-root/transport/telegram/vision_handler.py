# Downloads a Telegram photo and sends it to a Groq vision model.
# Uses raw httpx to call Groq REST API directly (avoids SDK Pydantic issues).
from __future__ import annotations

import base64
import logging
import re

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT = 30.0


def _telegram_api(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


async def _get_file_url(file_id: str) -> str | None:
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
            return f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"
    except Exception as exc:
        logger.error("getFile failed", extra={"file_id": file_id, "error": str(exc)})
        return None


async def _download_image(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
    except Exception as exc:
        logger.error("Image download failed", extra={"url": url[:80], "error": str(exc)})
        return None


def _normalize_for_telegram(text: str) -> str:
    """Strip LaTeX math delimiters and Markdown that Telegram cannot render."""
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()


def _lang_instruction(lang: str) -> str:
    mapping = {
        "ru": "Отвечай ТОЛЬКО на русском языке.",
        "en": "Reply ONLY in English.",
        "de": "Antworte NUR auf Deutsch.",
        "fr": "Reponds UNIQUEMENT en francais.",
        "es": "Responde SOLO en espanol.",
        "uk": "Vidpovidaj TILKY ukrainskoyu movoyu.",
        "tr": "YALNIZCA Turkce yanitla.",
        "ar": "Ajib billughat alarabiyyah faqat.",
        "zh": "Zhi yong zhongwen huida.",
        "ja": "Nihongo nomi de kotaete kudasai.",
        "ko": "Hangugeo로만 daabhaseyo.",
        "pl": "Odpowiadaj TYLKO po polsku.",
        "it": "Rispondi SOLO in italiano.",
        "pt": "Responda APENAS em portugues.",
        "fa": "Faghat be farsi pasokh bede.",
    }
    return mapping.get(lang, "Reply in the same language the user wrote in.")


def _error_msg(lang: str) -> str:
    mapping = {
        "ru": "Не удалось обработать изображение. Попробуйте ещё раз.",
        "en": "Failed to process the image. Please try again.",
        "de": "Bild konnte nicht verarbeitet werden. Bitte erneut versuchen.",
        "fr": "Impossible de traiter l'image. Veuillez reessayer.",
        "es": "No se pudo procesar la imagen. Intentelo de nuevo.",
        "uk": "Ne vdalosia obrob. zobrazhennia. Sprobuite shche raz.",
        "tr": "Goruntu islenemedi. Lutfen tekrar deneyin.",
        "pl": "Nie udalo sie przetworzyc obrazu. Sprobuj ponownie.",
        "it": "Impossibile elaborare l'immagine. Riprova.",
        "pt": "Nao foi possivel processar a imagem. Tente novamente.",
    }
    return mapping.get(lang, mapping["en"])


async def handle_vision(
    file_id: str,
    caption: str = "",
    lang: str = "en",
) -> str:
    err = _error_msg(lang)

    file_url = await _get_file_url(file_id)
    if not file_url:
        return err

    image_bytes = await _download_image(file_url)
    if not image_bytes:
        return err

    image_b64 = base64.b64encode(image_bytes).decode("ascii")

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
                    "IMPORTANT — if the image contains a test or exam question "
                    "(OGE, EGE, or any multiple-choice/matching task): "
                    "1) Choose ONE definitive answer for each item — never write "
                    "'may be either' or 'can be both'. "
                    "2) Use the most characteristic, textbook-standard classification. "
                    "3) State the final answer clearly at the end "
                    "(e.g. Ответ: 2 1 1 2 1). "
                    "4) Do not hedge or show alternative reasoning — "
                    "give the correct answer only. "
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

            result_text = _normalize_for_telegram(result_text)

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