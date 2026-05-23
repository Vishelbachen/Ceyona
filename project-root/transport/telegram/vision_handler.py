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


# ─── IMAGE RESIZE ─────────────────────────────────────────────────────────────

_MAX_IMAGE_SIDE     = 1280   # px — default for photos/illustrations
_MAX_IMAGE_SIDE_UI  = 800    # px — aggressive resize for UI screenshots (Wildberries, apps)
_JPEG_QUALITY       = 85     # default quality
_JPEG_QUALITY_UI    = 70     # lower quality for UI — text is still readable, size drops 40%
_UI_SIZE_THRESHOLD  = 300_000  # bytes — images larger than this after initial resize get second pass

def _resize_image_if_needed(image_bytes: bytes) -> bytes:
    """
    Resize image to prevent 413 Payload Too Large from Groq vision endpoint.

    Two-pass strategy:
    - Pass 1: resize to max 1280px on longest side (standard for photos).
    - Pass 2: if result still > 300KB (typical for UI screenshots like Wildberries,
      marketplace pages with many text elements), resize again to 800px at quality 70.
      Text remains readable; base64-encoded payload drops to ~300KB safe zone.

    Falls back to original bytes if PIL unavailable or resize fails.
    """
    try:
        import io

        from PIL import Image

        def _encode(img: Image.Image, max_side: int, quality: int) -> bytes:
            w, h = img.size
            if max(w, h) > max_side:
                ratio = max_side / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=quality)
            return buf.getvalue()

        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size

        # Pass 1: standard resize
        result = _encode(img, _MAX_IMAGE_SIDE, _JPEG_QUALITY)

        # Pass 2: if still large (UI screenshot), compress more aggressively
        if len(result) > _UI_SIZE_THRESHOLD:
            result_pass2 = _encode(Image.open(io.BytesIO(result)), _MAX_IMAGE_SIDE_UI, _JPEG_QUALITY_UI)
            logger.info("Image double-compressed for Groq vision (UI screenshot path)", extra={
                "original_bytes": len(image_bytes),
                "pass1_bytes":    len(result),
                "pass2_bytes":    len(result_pass2),
                "original_size":  f"{w}x{h}",
            })
            return result_pass2

        logger.info("Image resized for Groq vision", extra={
            "original_bytes": len(image_bytes),
            "resized_bytes":  len(result),
            "original_size":  f"{w}x{h}",
        })
        return result

    except Exception as exc:
        logger.warning("Image resize failed — using original bytes", extra={"error": str(exc)})
        return image_bytes


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

    # ── resize to prevent 413 Payload Too Large ───────────────────────────────
    # Groq vision endpoint rejects images > ~4MB base64.
    # Resize to max 1280px on longest side before encoding.
    # Uses only stdlib (no Pillow dependency) via a pure-Python JPEG resize,
    # or falls back to raw bytes if resize fails (still better than guaranteed 413).
    image_bytes = _resize_image_if_needed(image_bytes)

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

    # Choose max_tokens based on image size.
    # FAST (1024): sufficient for simple photos, illustrations, small text.
    # GENERAL (3072): required for UI screenshots, marketplace pages, dense text layouts
    #   (e.g. Wildberries, Ozon, app interfaces) — these produce long extraction output
    #   that exceeds FAST limit, causing truncated extraction → broken pipeline.
    # Threshold: if image > 200KB after resize, treat as complex and use GENERAL limit.
    _extraction_max_tokens = (
        RUNTIME.tier_configs[Tier.GENERAL].max_output_tokens
        if len(image_bytes) > 200_000
        else RUNTIME.tier_configs[Tier.FAST].max_output_tokens
    )

    payload = {
        "model": _VISION_MODEL,
        "max_tokens": _extraction_max_tokens,  # §15: reads from policy_registry; adaptive by image complexity
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
        from cognition.intent_engine import Intent, classify
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