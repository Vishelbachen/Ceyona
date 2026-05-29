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
    """
    text: str
    needs_pipeline: bool
    intent_result: object | None = None   # IntentResult — typed as object to avoid circular import
    failed: bool = False


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

    # ── routing: caption → classify; no caption → CONVERSATION (describe) ──────
    # Classifier works on USER INPUT only — never on extracted (LLM output).
    #
    # Semantic contract:
    #   caption present → user asked something → classify(caption) → route accordingly
    #   no caption      → user just sent a photo → intent = CONVERSATION → describe directly
    #
    # "No caption = CONVERSATION" is NOT a hardcode — it is a semantic truth:
    # a photo without a question has no user intent to classify. The correct
    # response is always a description. Letting orchestrator classify the
    # extracted text causes ANALYSIS/INSTRUCTION misrouting (QA-mode artifacts).

    intent_result = None
    needs_pipeline = True
    try:
        from cognition.intent_engine import Intent, IntentResult, classify

        _extracted_lower = extracted.lower()
        _has_uncertainty = any(s in _extracted_lower for s in _UNCERTAINTY_SIGNALS)

        if caption.strip():
            # User asked something — classify the actual question
            intent_result = await classify(caption.strip(), lang=lang)
            needs_pipeline = (
                _has_uncertainty
                or intent_result.intent != Intent.CONVERSATION
            )
        else:
            # No caption — photo only. Contract: describe it.
            # Force CONVERSATION so orchestrator delivers extracted directly.
            intent_result = IntentResult(
                intent=Intent.CONVERSATION,
                confidence=1.0,
                requires_tools=False,
            )
            needs_pipeline = _has_uncertainty  # only pipeline if extractor was uncertain
    except Exception as exc:
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
    "Attempt to identify character and franchise. State confidence explicitly.\n\n"
    "RULE 3 — REAL PERSON (photograph of an actual human):\n"
    "Describe ONLY visible details: clothing, hair, pose, expression, background. "
    "NEVER name, identify, or guess who the person is.\n\n"
    "RULE 4 — OTHER (product, place, animal, object, screenshot, UI, meme):\n"
    "Describe clearly: objects, colours, layout, any visible text, context.\n\n"
    "ABSOLUTE RULES — these override everything:\n"
    "- Describe only. Never solve, analyse, validate, verify, or interpret.\n"
    "- Never produce tables, checklists, or validation results.\n"
    "- Never write OK, fixed, satisfied, correct, or similar judgement words.\n\n"
    "OUTPUT FORMAT: plain prose, no headers, no bullet points. "
    "Do NOT open with meta-commentary like \'The images show\', \'These images represent\', "
    "\'Изображения представляют собой\', \'На изображениях\', or any similar phrase. "
    "Start each image description directly with its content. "
    "Separate image descriptions with a blank line."
)

# _GROUP_SYNTHESIS_SYSTEM_TEMPLATE: verbosity_rule and image_count injected in code.
# image_count >= 5 → verbosity_rule = "1-2 sentences per image"  (brief: large album)
# image_count  < 5 → verbosity_rule = "2-3 sentences per image"  (balanced: small album)
# Determined in code, not by LLM — prevents model from guessing what "many" means.
_GROUP_SYNTHESIS_SYSTEM_TEMPLATE = (
    "You are an image description assistant. Your only role is to describe what is in the images.\n\n"
    "You have received descriptions of {image_count} image(s) from a single album.\n\n"
    "Response length: {verbosity_rule}.\n\n"
    "ABSOLUTE RULES — these override everything:\n"
    "- Each image must be described individually. Do NOT merge images into a single story or narrative.\n"
    "- Describe only. Never solve, analyse, validate, verify, or check.\n"
    "- Never produce tables, checklists, or validation results.\n"
    "- Never write OK, fixed, satisfied, correct, or similar judgement words.\n"
    "- Do NOT infer intentions, personality, or context about the sender.\n\n"
    "Format: describe each image in turn. Do not force numbering if it looks mechanical.\n"
    "Start directly with the content. No meta-commentary, no preamble."
)


async def _call_groq_vision(
    image_bytes_list: list[bytes],
    caption: str,
    *,
    retry_on_400: bool = True,
) -> str | None:
    """
    Send a batch of images to Groq vision API.

    On HTTP 400 (payload too large / image count exceeded):
    - if retry_on_400=True and batch > 1: split in half, call both halves
      concurrently, join results with a blank line separator.
    - if retry_on_400=True and batch == 1: single image still fails → return None.
    - if retry_on_400=False: return None immediately (prevents infinite recursion).

    Returns extracted text string, or None on unrecoverable error.
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
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            ) or None

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
            parts = [p for p in (left, right) if isinstance(p, str) and p]
            return "\n\n".join(parts) if parts else None

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


async def _synthesise_batch_descriptions(descriptions: list[str], lang: str) -> str:
    """
    Merge multiple batch descriptions into one coherent response via a single LLM call.
    Used when an album had to be split into multiple batches.
    Falls back to newline-joined descriptions if LLM call fails.

    verbosity_rule is determined by image count in code — not left to LLM interpretation:
      >= 5 images → brief (1-2 sentences per image)
       < 5 images → balanced (2-3 sentences per image)
    """
    image_count = len(descriptions)
    verbosity_rule = (
        "1-2 sentences per image" if image_count >= 5 else "2-3 sentences per image"
    )
    system_prompt = _GROUP_SYNTHESIS_SYSTEM_TEMPLATE.format(
        image_count=image_count,
        verbosity_rule=verbosity_rule,
    )
    combined = "\n\n".join(f"Part {i+1}:\n{d}" for i, d in enumerate(descriptions))
    payload = {
        "model": _VISION_MODEL,
        "max_tokens": RUNTIME.tier_configs[Tier.GENERAL].max_output_tokens,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": combined},
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
            result = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            return result if result else combined
    except Exception as exc:
        logger.warning("Synthesis call failed — using joined descriptions", extra={"error": str(exc)})
        return combined


async def handle_vision_group(
    file_ids: list[str],
    caption: str = "",
    lang: str = "en",
) -> VisionResult:
    """
    Process a Telegram media group (album) with adaptive batching.

    Downloads all images concurrently, splits into batches of MAX_IMAGES_PER_BATCH,
    calls Groq vision per batch (with automatic split-retry on 400), then synthesises
    all batch descriptions into one coherent response.

    Returns VisionResult with failed=True if extraction could not be completed —
    caller must NOT inject the text into the pipeline in that case.

    Falls back to handle_vision() if the group has only one item.
    """
    from i18n.t import t
    err_text = t("vision_error", lang)

    if not file_ids:
        return VisionResult(text=err_text, needs_pipeline=False, failed=True)

    if len(file_ids) == 1:
        return await handle_vision(file_id=file_ids[0], caption=caption, lang=lang)

    # ── download all images concurrently, throttled ───────────────────────────
    _sem = asyncio.Semaphore(3)

    async def _fetch(fid: str) -> bytes | None:
        async with _sem:
            url = await _get_file_url(fid)
            if not url:
                return None
            raw = await _download_image(url)
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

    descriptions: list[str] = []
    for idx, res in enumerate(batch_results):
        if isinstance(res, Exception) or res is None:
            logger.warning(
                "Vision group: batch extraction failed",
                extra={"batch_index": idx, "error": str(res) if isinstance(res, Exception) else "None"},
            )
            continue
        descriptions.append(res)

    if not descriptions:
        logger.error("Vision group: all batches failed", extra={"loaded": loaded})
        return VisionResult(text=err_text, needs_pipeline=False, failed=True)

    # ── synthesise batch descriptions ─────────────────────────────────────────
    if len(descriptions) == 1:
        extracted = descriptions[0]
    else:
        extracted = await _synthesise_batch_descriptions(descriptions, lang)

    logger.info("Vision group extraction complete", extra={
        "lang":          lang,
        "images_loaded": loaded,
        "images_total":  len(file_ids),
        "batches":       len(batches),
        "descriptions":  len(descriptions),
        "extracted_len": len(extracted),
    })

    # ── routing: caption → classify; no caption → CONVERSATION (describe) ──────
    # Same semantic contract as handle_vision().
    # extracted = multi-image description generated by LLM → never classify.
    # caption   = what the user typed with the album      → classify if present.
    #
    # No caption = user just sent an album → intent = CONVERSATION → describe.
    # Letting orchestrator classify extracted causes ANALYSIS/INSTRUCTION misrouting.

    intent_result = None
    needs_pipeline = True
    try:
        from cognition.intent_engine import Intent, IntentResult, classify

        _uncertainty = any(s in extracted.lower() for s in _UNCERTAINTY_SIGNALS)

        if caption.strip():
            intent_result = await classify(caption.strip(), lang=lang)
            needs_pipeline = (
                _uncertainty
                or intent_result.intent != Intent.CONVERSATION
            )
        else:
            # No caption — album only. Contract: describe it.
            intent_result = IntentResult(
                intent=Intent.CONVERSATION,
                confidence=1.0,
                requires_tools=False,
            )
            needs_pipeline = _uncertainty  # only pipeline if extractor was uncertain
    except Exception as exc:
        logger.warning("Intent classify failed in vision group", extra={"error": str(exc)})
        needs_pipeline = True

    return VisionResult(
        text=extracted,
        needs_pipeline=needs_pipeline,
        intent_result=intent_result if needs_pipeline else None,
        failed=False,
    )