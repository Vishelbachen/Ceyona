from __future__ import annotations

import asyncio
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
    "You are an image analysis assistant. Extract and report image content accurately.\n\n"
    "RULES — apply the first matching rule:\n\n"
    "RULE 1 — TEXT/TASK IMAGE (exam, problem, formula, table, code, handwriting, diagram with labels):\n"
    "Transcribe ALL text EXACTLY as it appears. Preserve numbering, structure, formatting.\n"
    "Do NOT solve, answer, or interpret. Output the raw text only.\n\n"
    "RULE 2 — DRAWN / ANIMATED / ILLUSTRATED CHARACTER "
    "(anime, manga, game art, cartoon, digital art, fictional character — NOT a real photograph):\n"
    "Describe the character's visible appearance: hair colour and style, eye colour, "
    "clothing, accessories, art style, setting, any visible name/logo/insignia.\n"
    "Then attempt to identify the character and their franchise/game/anime/series. "
    "State your confidence explicitly. If uncertain, say so and give your best guess with reasoning.\n"
    "Example output: 'Персонаж с тёмными растрёпанными волосами, в длинном пальто, со швом на лбу. "
    "По стилю — манга/аниме. Похоже на [Name] из [Series], но не уверен — уточни.'\n"
    "Only say you cannot identify if you have genuinely zero visual clues.\n\n"
    "RULE 3 — REAL PERSON (photograph of an actual human being):\n"
    "Describe ONLY what is literally visible: clothing (colours, style, brand if visible), "
    "hair (colour, length, style), pose, expression, objects held, setting/background, "
    "lighting, mood. Be detailed and specific.\n"
    "NEVER attempt to name, identify, or guess who this person is.\n"
    "NEVER infer age, location, profession, or any personal information.\n"
    "NEVER confirm or deny if someone asks 'is this [name]?'.\n\n"
    "RULE 4 — OTHER (product, place, animal, object, scene, app screenshot, UI):\n"
    "Describe what you see clearly and concisely. "
    "Include relevant details: objects, colours, layout, text visible, context.\n\n"
    "OUTPUT FORMAT: plain prose, no headers, no bullet points, no meta-commentary like "
    "'The image shows' or 'This image depicts' or 'Изображение представляет собой'. "
    "Start directly with the content."
)


# ─── UNCERTAINTY SIGNALS ──────────────────────────────────────────────────────
# Signals that the extractor couldn't identify/understand the image.
# These must always go through the pipeline — never returned raw to user.
# Shared by handle_vision() and handle_vision_group().
_UNCERTAINTY_SIGNALS = (
    "не знаю", "не могу определить", "не удалось", "не удалось идентифицировать",
    "don't know", "cannot identify", "unable to identify", "i'm not sure",
    "not sure", "невозможно определить", "не могу распознать",
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

        _extracted_lower = extracted.lower()
        _has_uncertainty = any(s in _extracted_lower for s in _UNCERTAINTY_SIGNALS)

        # Force pipeline when:
        # 1. Intent is not a simple conversational reply
        # 2. Extractor expressed uncertainty — raw "I don't know" must never reach user directly;
        #    pipeline LLM will give a warmer, more helpful response
        needs_pipeline = (
            intent_result.intent != Intent.CONVERSATION
            or _has_uncertainty
        )
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

# ─── MULTI-IMAGE (ALBUM) HANDLER ──────────────────────────────────────────────

_GROUP_EXTRACTION_SYSTEM = (
    "You are given multiple images from the same album sent by a user. "
    "Describe what you see across all images as a coherent whole. "
    "If images show multiple items (products, places, documents), list each briefly. "
    "If they tell a story or sequence, describe the sequence. "
    "Be concise and factual. Do not hallucinate. "
    "If you cannot determine what an image shows, say so for that image only."
)


async def handle_vision_group(
    file_ids: list[str],
    caption: str = "",
    lang: str = "en",
) -> VisionResult:
    """
    Process a Telegram media group (album) as a single vision call.

    Downloads all images concurrently, builds a multi-image Groq request,
    and returns a single VisionResult — same contract as handle_vision().

    Falls back to handle_vision() on the first image if the group has only
    one item (degenerate case from a race in the aggregator).
    """
    from i18n.t import t
    err_text = t("vision_error", lang)

    if not file_ids:
        return VisionResult(text=err_text, needs_pipeline=False)

    # Degenerate case: aggregator flushed a single-item group.
    if len(file_ids) == 1:
        return await handle_vision(file_id=file_ids[0], caption=caption, lang=lang)

    # ── download all images concurrently ─────────────────────────────────────
    async def _fetch(fid: str) -> bytes | None:
        url = await _get_file_url(fid)
        if not url:
            return None
        raw = await _download_image(url)
        if not raw:
            return None
        return _resize_image_if_needed(raw)

    results = await asyncio.gather(*[_fetch(fid) for fid in file_ids], return_exceptions=True)

    user_content: list[dict] = []
    loaded = 0
    for idx, res in enumerate(results):
        if isinstance(res, Exception) or res is None:
            logger.warning(
                "Vision group: failed to load image",
                extra={"index": idx, "error": str(res) if isinstance(res, Exception) else "None"},
            )
            continue
        b64 = base64.b64encode(res).decode("ascii")
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
        loaded += 1

    if loaded == 0:
        return VisionResult(text=err_text, needs_pipeline=False)

    if caption.strip():
        user_content.append({"type": "text", "text": caption.strip()})

    # Group calls are inherently heavier — always use GENERAL token budget.
    _max_tokens = RUNTIME.tier_configs[Tier.GENERAL].max_output_tokens

    payload = {
        "model": _VISION_MODEL,
        "max_tokens": _max_tokens,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": _GROUP_EXTRACTION_SYSTEM},
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
        logger.error("Groq vision group HTTP error", extra={
            "status": exc.response.status_code,
            "body":   exc.response.text[:300],
        })
        return VisionResult(text=err_text, needs_pipeline=False)
    except Exception as exc:
        logger.error("Groq vision group call failed", extra={"error": str(exc)})
        return VisionResult(text=err_text, needs_pipeline=False)

    if not extracted:
        return VisionResult(text=err_text, needs_pipeline=False)

    # ── classify extracted content ────────────────────────────────────────────
    intent_result = None
    needs_pipeline = True
    try:
        from cognition.intent_engine import Intent, classify
        classify_input = (
            f"{caption.strip()}\n\n{extracted}".strip()
            if caption.strip()
            else extracted
        )
        intent_result = await classify(classify_input, lang=lang)
        _uncertainty = any(s in extracted.lower() for s in _UNCERTAINTY_SIGNALS)
        needs_pipeline = (
            intent_result.intent != Intent.CONVERSATION
            or _uncertainty
        )
    except Exception as exc:
        logger.warning("Intent classify failed in vision group", extra={"error": str(exc)})
        needs_pipeline = True

    logger.info("Vision group extraction complete", extra={
        "lang":           lang,
        "images_loaded":  loaded,
        "images_total":   len(file_ids),
        "caption_len":    len(caption),
        "extracted_len":  len(extracted),
        "needs_pipeline": needs_pipeline,
    })

    return VisionResult(
        text=extracted,
        needs_pipeline=needs_pipeline,
        intent_result=intent_result if needs_pipeline else None,
    )
