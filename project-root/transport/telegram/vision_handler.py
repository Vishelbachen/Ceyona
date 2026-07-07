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
                           Both are 0 on failure — llm_cost_usd will be 0, billing skipped.
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
    """Return URL for a Telegram Bot API method.

    If TELEGRAM_PROXY_URL is set (Cloudflare Worker), route through /tg/ proxy
    so HF Spaces never connects to api.telegram.org directly.
    """
    if settings.telegram_proxy_url:
        base = settings.telegram_proxy_url.rstrip("/")
        return f"{base}/tg/bot{settings.bot_token}/{method}"
    return f"https://api.telegram.org/bot{settings.bot_token}/{method}"


def _telegram_file_url(file_path: str) -> str:
    """Return URL to download a Telegram file by file_path.

    Routes through Cloudflare Worker proxy when TELEGRAM_PROXY_URL is set.
    Worker path: /tg/file/bot<token>/<file_path>
    """
    if settings.telegram_proxy_url:
        base = settings.telegram_proxy_url.rstrip("/")
        return f"{base}/tg/file/bot{settings.bot_token}/{file_path}"
    return f"https://api.telegram.org/file/bot{settings.bot_token}/{file_path}"



async def _download_image_via_worker(
    file_id: str, *, supabase=None, attachment_ref: dict | None = None, retries: int = 2,
) -> bytes | None:
    """
    Get the bytes of a Telegram photo.

    ARCH-change 2026-07 (attachments): this used to call the Cloudflare
    Worker's /tg/ proxy directly from inside the HF container (getFile +
    file download) — that outbound call showed the same ConnectError class
    as the original sendMessage incident (see architecture_reality.md §1,
    §5). The Worker now downloads photos itself at webhook-receive time and
    uploads them to Supabase Storage (see ceyona-worker/worker.js::
    downloadAndStoreAttachment) — this function reads the bytes back from
    Storage instead, the one outbound call that hasn't shown this failure.

    Falls back to the old direct-to-Worker path only if attachment_ref is
    missing (Worker's own download/upload failed) — see download_telegram_voice
    in speech_to_text.py for the identical pattern and reasoning.
    """
    if attachment_ref and attachment_ref.get("bucket") and attachment_ref.get("path"):
        try:
            if supabase is None:
                raise RuntimeError("supabase client not provided, cannot read from Storage")
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None,
                lambda: supabase.storage.from_(attachment_ref["bucket"]).download(attachment_ref["path"]),
            )
            logger.info("_download_image_via_worker: read from Supabase Storage", extra={
                "file_id": file_id, "bucket": attachment_ref["bucket"],
                "path": attachment_ref["path"], "size": len(image_bytes),
            })
            return image_bytes
        except Exception as exc:
            logger.error(
                "_download_image_via_worker: Storage read failed — should be rare, "
                "see architecture_reality.md §5 if this recurs",
                extra={"file_id": file_id, "error": str(exc), "exc_type": type(exc).__name__},
            )
            return None

    logger.warning(
        "_download_image_via_worker: no _attachment on update — falling back to direct "
        "Worker call; subject to the original ConnectError risk, see architecture_reality.md §4.1",
        extra={"file_id": file_id},
    )
    for attempt in range(retries + 1):
        file_url = await _get_file_url(file_id, retries=0)
        if not file_url:
            if attempt < retries:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            return None
        raw = await _download_image(file_url, retries=0)
        if raw is not None:
            return raw
        if attempt < retries:
            await asyncio.sleep(0.5 * (attempt + 1))
            continue
        return None
    return None

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
                return _telegram_file_url(file_path)
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

async def handle_vision_attachment(
    attachment,  # infra.attachment.Attachment — typed as untyped to avoid import cycle at module load
    caption: str = "",
    lang: str = "en",
) -> VisionResult:
    """
    Target-architecture entry point: extract image content given an
    Attachment (infra/attachment.py), instead of a raw Telegram file_id.

    Unlike voice (see speech_to_text.transcribe_attachment), vision has no
    step that requires local bytes before the model call — there's no VAD
    equivalent, and resizing is only needed on the bytes path (see below).
    So when settings.groq_vision_accepts_signed_url is True, this skips
    attachment.bytes() entirely: no download, no base64, no resize — just
    a signed URL handed straight to Groq's image_url field.

    Falls back to the base64 path (attachment.bytes() + resize + encode)
    when the flag is False — e.g. before the signed-URL-reachability check
    described in that setting's docstring has been confirmed empirically.
    """
    from i18n.t import t
    err_text = t("vision_error", lang)

    logger.info("[vision_input] single image received (attachment)", extra={
        "kind":        attachment.kind,
        "caption_len": len(caption),
        "lang":        lang,
    })

    from app.settings import settings

    if settings.groq_vision_accepts_signed_url:
        url = await attachment.signed_url()
        return await _handle_vision_core(image_url=url, caption=caption, lang=lang, err_text=err_text)

    image_bytes = await attachment.bytes()
    if not image_bytes:
        return VisionResult(text=err_text, needs_pipeline=False)
    return await _handle_vision_core(image_bytes=image_bytes, caption=caption, lang=lang, err_text=err_text)


async def handle_vision(
    file_id: str,
    caption: str = "",
    lang: str = "en",
    supabase=None,
    attachment_ref: dict | None = None,
) -> VisionResult:
    """
    LEGACY entry point — kept for the fallback path used when the incoming
    update has no `_attachment` (Worker's own download/upload failed; see
    update_handler.py's build_attachment_or_none()). New code should go
    through handle_vision_attachment() with an infra.attachment.Attachment
    built from `_attachment`; this function still does its own Telegram-
    proxy download for that degraded case only.

    Step 1 — qwen/qwen3.6-27b extracts image content (text or description).
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
    image_bytes = await _download_image_via_worker(file_id, supabase=supabase, attachment_ref=attachment_ref)
    if not image_bytes:
        return VisionResult(text=err_text, needs_pipeline=False)

    return await _handle_vision_core(image_bytes=image_bytes, caption=caption, lang=lang, err_text=err_text)


async def _handle_vision_core(
    *,
    caption: str,
    lang: str,
    err_text: str,
    image_bytes: bytes | None = None,
    image_url: str | None = None,
) -> VisionResult:
    """
    Shared extraction + routing logic for both the URL path and the bytes
    path. Exactly one of image_bytes / image_url is expected to be set by
    the caller.
    """
    if image_url:
        user_content: list[dict] = [
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        if caption.strip():
            user_content.append({"type": "text", "text": caption.strip()})
        # No local bytes to size-check in the URL path — use the FAST budget
        # by default; GENERAL-tier extraction length only matters for dense
        # UI screenshots, which the bytes path detects by resized size. If
        # URL-path extraction starts truncating on complex images in
        # practice, this is the place to revisit (e.g. a quick HEAD/range
        # check on the URL, or always using the GENERAL budget for the URL
        # path since we no longer pay the base64 token cost that made FAST
        # worth defaulting to).
        _extraction_max_tokens = RUNTIME.tier_configs[Tier.FAST].max_output_tokens
    else:
        # ── resize to prevent 413 Payload Too Large ───────────────────────
        # Groq vision endpoint rejects images > ~4MB base64.
        # Resize to max 1280px on longest side before encoding.
        # Uses only stdlib (no Pillow dependency) via a pure-Python JPEG resize,
        # or falls back to raw bytes if resize fails (still better than guaranteed 413).
        image_bytes = _resize_image_if_needed(image_bytes)
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        user_content = [
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

# ─── MULTI-IMAGE (ALBUM) HANDLER ──────────────────────────────────────────────

# Safe default: 4 images per Groq vision request.
# Groq does not publish a hard per-request image count limit — the real constraint
# is total token budget (each image ≈ 1500–2000 tokens at 1280px).
# Production observation: 9 images → HTTP 400; 1-4 → stable; 5 → usually ok.
# MAX_IMAGES_PER_BATCH = 4 gives stable headroom. On 400, we retry with batch/2.
_MAX_IMAGES_PER_BATCH = 4

_GROUP_EXTRACTION_SYSTEM = (
    "You are an image description assistant. Your only role is to describe images.\n\n"
    "For each image, apply the first matching rule:\n\n"
    "RULE 1 — TEXT IMAGE (exam, problem, formula, table, code, handwriting, diagram):\n"
    "Transcribe ALL text EXACTLY as written. Preserve structure.\n\n"
    "RULE 2 — DRAWN / ANIMATED CHARACTER (anime, manga, game art, cartoon, illustration):\n"
    "Describe visible appearance: hair colour/style, clothing, accessories, art style. "
    "Attempt identification only when there are strong, specific clues; otherwise keep the description "
    "descriptive and avoid forcing a franchise or anime guess. State confidence explicitly.\n\n"
    "RULE 3 — REAL PERSON (photograph of an actual human):\n"
    "Describe ONLY visible details: clothing, hair, pose, expression, background. "
    "NEVER name, identify, or guess who the person is.\n\n"
    "RULE 4 — OTHER (product, place, animal, object, screenshot, UI, meme):\n"
    "Describe clearly: objects, colours, layout, any visible text, context.\n\n"
    "ABSOLUTE RULES — these override everything:\n"
    "- Describe only. Never solve, analyse, validate, verify, or interpret.\n"
    "- Never produce tables, checklists, or validation results.\n"
    "- Never write OK, fixed, satisfied, correct, or similar judgement words.\n\n"
    "OUTPUT FORMAT — mandatory: "
    "Return a JSON array. One element per image, in order. Each element is a plain string "
    "containing the description of that image — no keys, no nesting, no metadata. "
    "Example for 3 images: [\"description of first\", \"description of second\", \"description of third\"] "
    "Each description: plain prose, starts directly with the visible content. "
    "No JSON keys. No markdown. No prose outside the array. Output the array only."
)

# _GROUP_SYNTHESIS_SYSTEM_TEMPLATE: verbosity_rule injected in code.
# image_count >= 5 → verbosity_rule = "1-2 sentences per image"  (brief: large album)
# image_count  < 5 → verbosity_rule = "2-3 sentences per image"  (balanced: small album)
# Determined in code, not by LLM — prevents model from guessing what "many" means.
_GROUP_SYNTHESIS_SYSTEM_TEMPLATE = (
    "Describe each image independently. "
    "Each description should be a short, self-contained paragraph focused only on what is directly visible. "
    "Response length: {verbosity_rule}. "
    "Use direct, concrete language without generic introductory phrases. "
    "Avoid meta-commentary, evaluation, or speculation. "
    "Do not infer relationships or intent unless clearly visible in the image. "
    "Do not speculate about why the images were sent together. "
    "Use natural paragraph separation instead of rigid formatting."
)


@dataclass(frozen=True)
class _VisionBatchResult:
    """Internal result from a single Groq vision batch call.

    descriptions: structured list — one entry per image in the batch.
    Extraction prompt returns JSON array; parser fills this field.
    Falls back to [raw_text] if JSON parse fails.
    text: raw LLM output, kept for logging and fallback only.
    """
    descriptions: list  # list[str] — one description per image
    text: str           # raw LLM output (logging / fallback)
    input_tokens: int
    output_tokens: int


async def _call_groq_vision(
    image_bytes_list: list[bytes],
    caption: str,
    *,
    retry_on_400: bool = True,
) -> _VisionBatchResult | None:
    """
    Send a batch of images to Groq vision API.

    On HTTP 400 (payload too large / image count exceeded):
    - if retry_on_400=True and batch > 1: split in half, call both halves
      concurrently, join results with a blank line separator.
    - if retry_on_400=True and batch == 1: single image still fails → return None.
    - if retry_on_400=False: return None immediately (prevents infinite recursion).

    Returns _VisionBatchResult with text and actual token counts, or None on error.
    Token counts are used by handle_vision_group to compute exact billed cost.
    """
    user_content: list[dict] = []
    for img_bytes in image_bytes_list:
        b64 = base64.b64encode(img_bytes).decode("ascii")
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    if caption.strip():
        user_content.append({"type": "text", "text": caption.strip()})

    _max_tokens = RUNTIME.tier_configs[Tier.GENERAL].max_output_tokens
    payload = {
        "model": _VISION_MODEL,
        "max_tokens": _max_tokens,
        "temperature": 0.1,
        "reasoning_effort": "none",  # mandatory per models.md §26.1
        "messages": [
            {"role": "system", "content": _GROUP_EXTRACTION_SYSTEM},
            {"role": "user",   "content": user_content},
        ],
    }

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
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not text:
                return None
            _usage = data.get("usage", {})

            # Parse structured JSON array from extraction prompt.
            # Extraction now returns: ["desc1", "desc2", ...] — one string per image.
            # Fallback: wrap raw text as single-element list (maintains contract downstream).
            import json as _json
            _descriptions: list[str] = []
            try:
                _raw = text.strip()
                # Strip possible markdown code fences the model might add
                if _raw.startswith("```"):
                    _raw = _raw.split("```")[1]
                    if _raw.startswith("json"):
                        _raw = _raw[4:]
                    _raw = _raw.strip()
                parsed = _json.loads(_raw)
                if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                    _descriptions = [x.strip() for x in parsed if x.strip()]
                else:
                    logger.warning("Groq vision: unexpected JSON structure — using raw text fallback")
                    _descriptions = [text]
            except (_json.JSONDecodeError, Exception) as _e:
                logger.warning("Groq vision: JSON parse failed — using raw text fallback",
                               extra={"error": str(_e), "preview": text[:80]})
                _descriptions = [text]

            return _VisionBatchResult(
                descriptions=_descriptions,
                text=text,
                input_tokens=_usage.get("prompt_tokens", 0),
                output_tokens=_usage.get("completion_tokens", 0),
            )

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400 and retry_on_400 and len(image_bytes_list) > 1:
            # Split batch in half and retry both halves concurrently.
            mid = len(image_bytes_list) // 2
            logger.warning(
                "Groq vision 400 — splitting batch and retrying",
                extra={"batch_size": len(image_bytes_list), "mid": mid},
            )
            left, right = await asyncio.gather(
                _call_groq_vision(image_bytes_list[:mid], caption, retry_on_400=False),
                _call_groq_vision(image_bytes_list[mid:], caption="", retry_on_400=False),
                return_exceptions=True,
            )
            parts = [p for p in (left, right) if isinstance(p, _VisionBatchResult)]
            if not parts:
                return None
            # Merge structured descriptions from both halves — preserves order.
            merged_descriptions = []
            for p in parts:
                merged_descriptions.extend(p.descriptions)
            merged_text = "\n\n".join(p.text for p in parts)
            return _VisionBatchResult(
                descriptions=merged_descriptions,
                text=merged_text,
                input_tokens=sum(p.input_tokens for p in parts),
                output_tokens=sum(p.output_tokens for p in parts),
            )

        logger.error("Groq vision group HTTP error", extra={
            "status": exc.response.status_code,
            "body":   exc.response.text[:300],
            "batch_size": len(image_bytes_list),
        })
        return None

    except Exception as exc:
        logger.error("Groq vision group call failed", extra={
            "error": str(exc),
            "batch_size": len(image_bytes_list),
        })
        return None


async def _merge_descriptions(all_descriptions: list[str]) -> str:
    """
    Merge structured per-image descriptions into the final album response.

    Architecture contract:
    - Input: list[str] — one clean description per image, already extracted
      by _call_groq_vision via JSON array output format.
    - No LLM call needed: descriptions are already clean, unnumbered prose.
    - Separator: blank line between images — standard Telegram paragraph spacing.

    This replaces the previous LLM synthesis step which received raw prose
    (potentially numbered) and reproduced that numbering in output.
    Structured extraction eliminates the source of the artifact — no downstream
    cleanup needed.
    """
    return "\n\n".join(desc.strip() for desc in all_descriptions if desc.strip())


async def handle_vision_group(
    file_ids: list[str],
    caption: str = "",
    lang: str = "en",
    supabase=None,
    attachment_refs: dict[str, dict] | None = None,
) -> VisionResult:
    """
    Process a Telegram media group (album) with adaptive batching.

    Downloads all images concurrently, splits into batches of MAX_IMAGES_PER_BATCH,
    calls Groq vision per batch (with automatic split-retry on 400), then synthesises
    all batch descriptions into one coherent response.

    Returns VisionResult with failed=True if extraction could not be completed —
    caller must NOT inject the text into the pipeline in that case.

    Falls back to handle_vision() if the group has only one item.

    KNOWN GAP (2026-07, attachments): unlike the single-photo path in
    handle_vision(), this multi-image path does NOT yet read from Supabase
    Storage — attachment_refs, if provided, is threaded through only for the
    single-item fallback below. Albums (>1 photo) still call
    _download_image_via_worker() per-image with attachment_ref=None, which
    falls back to the direct-to-Worker download — still subject to the
    ConnectError class described in architecture_reality.md. Reason: albums
    arrive via MediaGroupAggregator (Redis-buffered, one MediaGroupItem per
    photo — see media_group_aggregator.py), which doesn't currently carry
    the Worker's per-photo _attachment ref through its serialization. Wiring
    that through is a reasonable follow-up but wasn't done here to keep this
    change scoped to the failure actually reproduced in logs (single photo,
    single voice) — see architecture_reality.md §5 for the pattern to
    follow if album downloads start showing the same ConnectError.
    """
    from i18n.t import t
    err_text = t("vision_error", lang)

    if not file_ids:
        return VisionResult(text=err_text, needs_pipeline=False, failed=True)

    logger.info("[vision_input] album received", extra={
        "image_count": len(file_ids),
        "caption_len": len(caption),
        "lang":        lang,
    })

    if len(file_ids) == 1:
        single_ref = (attachment_refs or {}).get(file_ids[0])
        return await handle_vision(file_id=file_ids[0], caption=caption, lang=lang,
                                    supabase=supabase, attachment_ref=single_ref)

    # ── image count guardrail ─────────────────────────────────────────────────
    # Llama-4-scout degrades beyond ~6 images per context: attention spreads thin,
    # partial images are silently dropped, output quality collapses.
    # Hard limit at orchestrator level — correct place per architecture.md.
    _MAX_GROUP_IMAGES = 6
    if len(file_ids) > _MAX_GROUP_IMAGES:
        from i18n.t import t as _t
        return VisionResult(
            text=_t("too_many_images", lang),
            needs_pipeline=False,
            failed=False,
        )

    # ── download all images concurrently, throttled ───────────────────────────
    _sem = asyncio.Semaphore(3)

    async def _fetch(fid: str) -> bytes | None:
        async with _sem:
            raw = await _download_image_via_worker(fid)
            if not raw:
                return None
            return _resize_image_if_needed(raw)

    fetch_results = await asyncio.gather(*[_fetch(fid) for fid in file_ids], return_exceptions=True)

    image_bytes_list: list[bytes] = []
    for idx, res in enumerate(fetch_results):
        if isinstance(res, Exception) or res is None:
            logger.warning(
                "Vision group: failed to load image",
                extra={"index": idx, "error": str(res) if isinstance(res, Exception) else "None"},
            )
            continue
        image_bytes_list.append(res)

    loaded = len(image_bytes_list)
    if loaded == 0:
        return VisionResult(text=err_text, needs_pipeline=False, failed=True)

    logger.info("Vision group: images loaded", extra={
        "loaded": loaded, "total": len(file_ids),
    })

    # ── split into batches of MAX_IMAGES_PER_BATCH ────────────────────────────
    batches = [
        image_bytes_list[i : i + _MAX_IMAGES_PER_BATCH]
        for i in range(0, loaded, _MAX_IMAGES_PER_BATCH)
    ]

    # ── call Groq vision for each batch concurrently ──────────────────────────
    batch_results = await asyncio.gather(
        *[
            _call_groq_vision(
                batch,
                caption if idx == 0 else "",  # caption only on first batch
                retry_on_400=True,
            )
            for idx, batch in enumerate(batches)
        ],
        return_exceptions=True,
    )

    all_descriptions: list[str] = []  # flat list — one str per image across all batches
    _group_input_tokens  = 0
    _group_output_tokens = 0
    for idx, res in enumerate(batch_results):
        if isinstance(res, Exception) or res is None:
            logger.warning(
                "Vision group: batch extraction failed",
                extra={"batch_index": idx, "error": str(res) if isinstance(res, Exception) else "None"},
            )
            continue
        # Extend with structured per-image descriptions from this batch.