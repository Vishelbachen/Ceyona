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

# qwen3.6-27b: vision model (models.md §26.1)
# Role here: image content extraction only — NOT solving, NOT answering.
_VISION_MODEL   = "qwen/qwen3.6-27b"
_GROQ_ENDPOINT  = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT        = 30.0


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VisionResult:
    """
    text           — extracted image content (text, description, or error message).
    needs_pipeline — True  → forward `text` into the main orchestrator pipeline.
                     False → deliver `text` directly to the user.
    intent_result  — pre-computed IntentResult; passed to OrchestratorRequest as
                     forced_intent to avoid a second classify() call in the pipeline.
                     None when needs_pipeline is False.
    failed         — True → vision extraction failed entirely. Caller MUST NOT
                     inject `text` into pipeline or user_message — it contains
                     an error string that would cause the LLM to hallucinate.
                     Caller should send a localized error message directly.
    vision_input_tokens  — actual input tokens from Groq API response (for billing).
    vision_output_tokens — actual output tokens from Groq API response (for billing).
                           Both are 0 on failure — cost_usd will be 0, billing skipped.
    """
    text: str
    needs_pipeline: bool
    intent_result: object | None = None   # IntentResult — typed as object to avoid circular import
    failed: bool = False
    vision_input_tokens: int = 0
    vision_output_tokens: int = 0


# ─── INTENT BUILDER ───────────────────────────────────────────────────────────
# Retained for potential future use or extension points.
# handle_vision() and handle_vision_group() no-caption paths no longer call this —
# they return intent_result=None and needs_pipeline=True, delegating routing to
# the orchestrator. The caption path calls classify() directly.

def _build_vision_intent(intent_enum, lang: str) -> object:
    """
    Build a fully populated IntentResult for the vision no-caption path.

    Uses _resolve_routing() as the single RoutingProfile authority and
    build_system_prompt() for the system prompt — identical to the classify() path.

    Returns an IntentResult. Typed as object to avoid circular import at module level.
    Caller imports are deferred inside the routing block (same pattern as classify()).
    """
    from cognition.intent_engine import (
        IntentResult,
        _resolve_routing,
        build_system_prompt,
    )
    routing = _resolve_routing(intent_enum)
    return IntentResult(
        intent=intent_enum,
        confidence=1.0,
        system_prompt=build_system_prompt(intent_enum, lang),
        requires_retrieval=routing.retrieval_required,
        requires_tools=False,
        routing=routing,
    )


# ─── TELEGRAM FILE HELPERS ────────────────────────────────────────────────────

def _telegram_api(method: str) -> str:
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


async def _get_file_url(file_id: str, *, retries: int = 2) -> str | None:
    _RETRYABLE_STATUS = {429, 500, 502, 503}
    for attempt in range(retries + 1):
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
        except httpx.HTTPStatusError as exc:
            if attempt < retries and exc.response.status_code in _RETRYABLE_STATUS:
                logger.warning("getFile retryable HTTP error — retrying", extra={
                    "file_id": file_id, "status": exc.response.status_code, "attempt": attempt + 1,
                })
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            logger.error("getFile HTTP error", extra={
                "file_id": file_id,
                "status": exc.response.status_code,
                "exc_type": type(exc).__name__,
            })
            return None
        except Exception as exc:
            if attempt < retries:
                logger.warning("getFile network error — retrying", extra={
                    "file_id": file_id,
                    "error": str(exc) or "(empty)",
                    "exc_type": type(exc).__name__,
                    "attempt": attempt + 1,
                })
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            logger.error("getFile failed", extra={
                "file_id": file_id,
                "error": str(exc) or "(empty)",
                "exc_type": type(exc).__name__,
            })
            return None
    return None


async def _download_image(url: str, *, retries: int = 1) -> bytes | None:
    """
    Download image bytes from a Telegram file URL.

    Retries once on transient errors (429 rate-limit, 5xx server errors).
    Telegram Bot API can return 429 when too many getFile/download requests
    are made concurrently — a single retry after 0.5 s resolves most cases.
    Other errors (404, network timeout) are not retried.
    """
    _RETRYABLE = {429, 500, 502, 503}
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(url)
                r.raise_for_status()
                return r.content
        except httpx.HTTPStatusError as exc:
            if attempt < retries and exc.response.status_code in _RETRYABLE:
                logger.warning(
                    "Image download retryable error — retrying",
                    extra={"status": exc.response.status_code, "attempt": attempt + 1},
                )
                await asyncio.sleep(0.5)
                continue
            logger.error(
                "Image download failed",
                extra={"url": url[:80], "error": str(exc)},
            )
            return None
        except Exception as exc:
            logger.error("Image download failed", extra={"url": url[:80], "error": str(exc)})
            return None
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
    "Attempt identification only when the artwork contains strong, specific clues. "
    "If clues are weak or ambiguous, say so and keep the answer descriptive instead of forcing "
    "a franchise/game/anime guess. State your confidence explicitly.\n\n"
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
    "OUTPUT FORMAT: plain prose, no headers, no bullet points. "
    "Do not open with meta-commentary that describes the image rather than its content "
    "('The image shows', 'This image depicts', or equivalents in any language). "
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

    logger.info("[vision_input] single image received", extra={
        "file_id":     file_id,
        "caption_len": len(caption),
        "lang":        lang,
    })

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
        "reasoning_effort": "none",  # mandatory per models.md §26.1
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
            _usage = data.get("usage", {})
            _vision_input_tokens  = _usage.get("prompt_tokens", 0)
            _vision_output_tokens = _usage.get("completion_tokens", 0)

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

    logger.info("[after_extraction] single image extracted", extra={
        "extracted_len":    len(extracted),
        "extracted_preview": extracted[:120],
    })

    # ── routing: caption → classify; no caption → pipeline ───────────────────
    # Classifier works on USER INPUT only — never on extracted (LLM output).
    #
    # Semantic contract:
    #   caption present → user asked something → classify(caption) → route accordingly
    #   no caption      → user just sent a photo → intent_result=None, needs_pipeline=True
    #                     orchestrator owns the routing decision (CONVERSATION default)
    #
    # "No caption = orchestrator" is NOT a shortcut — it is the correct contract:
    # a photo without a question has no user intent for the classifier to evaluate.
    # Classifying extracted text caused ANALYSIS/INSTRUCTION misrouting (QA-mode
    # artifacts). needs_pipeline=True lets update_handler hand off to orchestrator,
    # which applies its own fallback routing without a pre-computed intent.

    intent_result = None
    needs_pipeline = True
    try:
        from cognition.intent_engine import Intent, classify

        _extracted_lower = extracted.lower()
        _has_uncertainty = any(s in _extracted_lower for s in _UNCERTAINTY_SIGNALS)

        if caption.strip():
            # User asked something — classify the actual question.
            intent_result = await classify(caption.strip(), lang=lang)
            needs_pipeline = (
                _has_uncertainty
                or intent_result.intent != Intent.CONVERSATION
            )
        else:
            # No caption — photo only. No user intent to classify.
            # Contract: intent_result=None, needs_pipeline=True.
            # Orchestrator receives the extracted text and handles routing via
            # its own fallback (CONVERSATION default for bare descriptions).
            # Classifying extracted text caused ANALYSIS/INSTRUCTION misrouting
            # (LLM output ≠ user input); _build_vision_intent was a workaround
            # that still bypassed the update_handler routing contract.
            intent_result = None
            needs_pipeline = True  # always — orchestrator owns the routing decision

    except Exception as exc:
        logger.warning("Intent classify failed in vision, defaulting to pipeline",
                       extra={"error": str(exc)})
        needs_pipeline = True

    logger.info("[final_routing] single image routed", extra={
        "lang":           lang,
        "caption_len":    len(caption),
        "extracted_len":  len(extracted),
        "needs_pipeline": needs_pipeline,
        "intent":         intent_result.intent.value if intent_result else None,
        "routing.depth":  intent_result.routing.reasoning_depth if intent_result else None,
        "routing.truth":  intent_result.routing.truth_mode if intent_result else None,
    })

    return VisionResult(
        text=extracted,
        needs_pipeline=needs_pipeline,
        intent_result=intent_result if needs_pipeline else None,
        vision_input_tokens=_vision_input_tokens,
        vision_output_tokens=_vision_output_tokens,
    )