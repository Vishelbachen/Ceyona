from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.settings import settings
from contracts.shared_types import Tier
from core.kernel.policy_registry import RUNTIME

logger = logging.getLogger(__name__)

# llama-4-scout: LONG-CONTEXT TRANSFORMATION ENGINE (Heavy Tier, models.md)
# Role here: image content extraction only — NOT solving, NOT answering.
_VISION_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"
_GROQ_ENDPOINT  = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT        = 30.0


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VisionResult:
    """
    text          — extracted image content (text, description, or error message).
    needs_pipeline — True  → forward `text` into the main orchestrator pipeline.
                    False → deliver `text` directly to the user.
    intent_result  — pre-computed IntentResult; passed to OrchestratorRequest as
                     forced_intent to avoid a second classify() call in the pipeline.
                     None when needs_pipeline is False.
    """
    text: str
    needs_pipeline: bool
    intent_result: object | None = None   # IntentResult — typed as object to avoid circular import


# ─── TELEGRAM FILE HELPERS ────────────────────────────────────────────────────

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


# ─── EXTRACTION SYSTEM PROMPT ─────────────────────────────────────────────────

_EXTRACTION_SYSTEM = (
    "You are a precise image content extractor. "
    "Your ONLY task is to faithfully report what is in the image — nothing more. "
    "\n\n"
    "RULES:\n"
    "1. If the image contains written text (exam questions, tasks, problems, "
    "formulas, diagrams with labels, tables, code, handwriting): "
    "transcribe ALL text EXACTLY as it appears. Preserve numbering, structure, "
    "and formatting. Do NOT solve, do NOT answer, do NOT interpret.\n"
    "2. If the image is a photograph, illustration, or scene with no significant "
    "text: describe what you see clearly and concisely. "
    "Include objects, people, setting, colours, actions — whatever is visible.\n"
    "3. NEVER add conclusions, answers, suggestions, or commentary. "
    "Report only what is literally present in the image."
)


# ─── MAIN ENTRY POINT ─────────────────────────────────────────────────────────

async def handle_vision(
    file_id: str,
    caption: str = "",
    lang: str = "en",
) -> VisionResult:
    """
    Step 1 — llama-4-scout extracts image content (text or description).
    Step 2 — intent_engine.classify() determines whether the extracted content
              requires the main pipeline or can be answered directly.

    Returns VisionResult with:
      text           — extracted content or error message
      needs_pipeline — routing flag for update_handler
    """
    from i18n.t import t
    err_text = t("vision_error", lang)

    # ── download ──────────────────────────────────────────────────────────────
    file_url = await _get_file_url(file_id)
    if not file_url:
        return VisionResult(text=err_text, needs_pipeline=False)

    image_bytes = await _download_image(file_url)
    if not image_bytes:
        return VisionResult(text=err_text, needs_pipeline=False)

    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # ── build user message: image first, then caption (if any) ───────────────
    user_content: list[dict] = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        },
    ]
    if caption.strip():
        user_content.append({"type": "text", "text": caption.strip()})

    payload = {
        "model": _VISION_MODEL,
        "max_tokens": RUNTIME.tier_configs[Tier.FAST].max_output_tokens,  # §15: reads from policy_registry, not hardcoded
        "temperature": 0.1,      # low: extraction must be faithful, not creative
        "messages": [
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user",   "content": user_content},
        ],
    }

    # ── call Groq vision API ──────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                _GROQ_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type":  "application/json",
                },
            )
            r.raise_for_status()
            data = r.json()
            extracted = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

    except httpx.HTTPStatusError as exc:
        logger.error("Groq vision HTTP error", extra={
            "status": exc.response.status_code,
            "body":   exc.response.text[:300],
        })
        return VisionResult(text=err_text, needs_pipeline=False)

    except Exception as exc:
        logger.error("Groq vision call failed", extra={"error": str(exc)})
        return VisionResult(text=err_text, needs_pipeline=False)

    if not extracted:
        logger.error("Groq vision returned empty content", extra={"data": str(data)[:200]})
        return VisionResult(text=err_text, needs_pipeline=False)

    # ── classify extracted content via intent_engine ──────────────────────────
    # Combine caption + extracted text so the classifier sees full context.
    classify_input = (
        f"{caption.strip()}\n\n{extracted}".strip()
        if caption.strip()
        else extracted
    )

    intent_result  = None
    try:
        from cognition.intent_engine import classify, Intent
        intent_result  = await classify(classify_input, lang=lang)
        needs_pipeline = intent_result.intent != Intent.CONVERSATION
    except Exception as exc:
        # If classifier fails, default to pipeline for safety.
        logger.warning("Intent classify failed in vision, defaulting to pipeline",
                       extra={"error": str(exc)})
        needs_pipeline = True

    logger.info("Vision extraction complete", extra={
        "lang":           lang,
        "caption_len":    len(caption),
        "extracted_len":  len(extracted),
        "needs_pipeline": needs_pipeline,
    })

    return VisionResult(
        text=extracted,
        needs_pipeline=needs_pipeline,
        intent_result=intent_result if needs_pipeline else None,
    )