from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Speech-to-Text (ASR) adapter. Per architecture.md §12, models1.md §12.
#
# Authority boundary:
#   MUST NOT: influence EPK, select execution tier, alter TruthMode
#   MAY:      transcribe audio via Groq Whisper API, return raw transcript
#
# Provider: Groq (api.groq.com)
# Models:
#   whisper-large-v3        → PRIMARY ASR  ($0.111 / hour)
#   whisper-large-v3-turbo  → FAST ASR     ($0.040 / hour)
#
# Activation: is_voice_input = True ONLY.
# Output feeds into update_handler as text, continuing normal pipeline.
#
# Billing: audio_seconds recorded in UsageEntry (separate from LLM tokens).
# usage_meter.record() must receive audio_seconds for correct speech billing.
#
# Invocation pattern:
#   telegram voice message → download file → transcribe() → text → pipeline
#
# Position in lifecycle:
#   Voice Input → Safety Gate Pass 1 (on transcript) → Feature Extraction
#   → Safety Gate Pass 2 → Multilingual Normalization → EPK → ...

_PRIMARY_MODEL = "whisper-large-v3"
_TURBO_MODEL   = "whisper-large-v3-turbo"

# Maximum audio file size Groq's transcription endpoint accepts when the body
# is sent directly (25 MB). This is a Groq/Whisper limit, NOT a Storage/bucket
# limit — Storage may hold larger files; this handler decides what it can
# send to this specific model. See app/settings.py for the bucket-level
# housekeeping limit, which is deliberately not tied to this number.
_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Formats Groq's transcription endpoint documents as natively supported:
# flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm (console.groq.com/docs/speech-to-text).
# CORRECTION (2026-07): "ogg" was previously missing from this set, based on an
# incorrect assumption that "Groq Whisper does not accept OGG/Opus" — that claim
# is not supported by Groq's documentation, which lists ogg without a codec
# caveat. "ogg"/"oga" are included below so Telegram voice messages (OGG/Opus)
# skip the WAV conversion path entirely. If a live Telegram OGG/Opus file is
# ever rejected by Groq in practice, that would mean the Opus codec specifically
# is the exception (not "ogg" generally) — see _convert_to_wav's docstring for
# what to do in that case.
_GROQ_SUPPORTED_EXTENSIONS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "flac", "ogg", "oga"}

# VAD silencedetect parameters (ffmpeg).
# noise: -35dB — captures typical recording noise floor without triggering on whisper.
# d: 0.5s — minimum silence duration to count as a silence event.
# Rationale: Telegram voice messages start and end with a brief silence burst from
# PTT button click; 0.5s threshold avoids false positives on that artifact.
_VAD_NOISE_FLOOR = "-35dB"
_VAD_MIN_DURATION = "0.5"


async def is_silent(audio_bytes: bytes, source_ext: str = "ogg") -> bool:
    """
    Voice Activity Detection via ffmpeg silencedetect filter.

    Returns True if the audio contains no detectable speech — i.e. the entire
    recording never produces a silence_end event (never left silence state).

    Called BEFORE transcribe() to avoid sending silent audio to Whisper,
    which returns an empty or hallucinated transcript and causes a confusing
    generic error message to the user.

    Failure mode: if ffmpeg is unavailable or crashes → returns False (pass-through).
    The audio then proceeds to Whisper which will return an empty transcript,
    handled by the existing asr_failed branch. No silent audio is lost.

    Position in lifecycle (models.md §12, architecture.md §12):
        download_telegram_voice → [HERE] → transcribe() → pipeline
    """
    in_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{source_ext}", delete=False) as f:
            f.write(audio_bytes)
            in_path = f.name

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", in_path,
            "-af", f"silencedetect=noise={_VAD_NOISE_FLOOR}:d={_VAD_MIN_DURATION}",
            "-f", "null", "-",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        output = stderr.decode(errors="replace")

        # silencedetect emits "silence_end: <t>" each time audio rises above the
        # noise floor. If no silence_end appears, the recording never contained
        # a moment of audible sound — it was fully silent.
        has_speech = "silence_end" in output

        logger.debug(
            "VAD result",
            extra={"silent": not has_speech, "ext": source_ext, "bytes": len(audio_bytes)},
        )
        return not has_speech

    except Exception as exc:
        logger.warning(
            "VAD ffmpeg failed — treating as non-silent (pass-through to Whisper)",
            extra={"error": str(exc)},
        )
        return False  # safe default: don't block, let Whisper decide

    finally:
        if in_path and os.path.exists(in_path):
            os.unlink(in_path)


@dataclass(frozen=True)
class TranscriptResult:
    text: str               # raw transcript from Whisper
    model_used: str         # which Whisper model was used
    audio_seconds: float    # duration for billing
    success: bool
    error: str = ""


async def transcribe(
    audio_bytes: bytes | None = None,
    filename: str = "voice.ogg",
    lang: str | None = None,
    use_turbo: bool = False,
    audio_url: str | None = None,
) -> TranscriptResult:
    """
    Transcribe audio using Groq Whisper — either from local bytes or from a
    URL Groq fetches itself.

    Args:
        audio_bytes: raw audio content (OGG/MP3/WAV/M4A/...). Required unless
                     audio_url is given.
        filename:    original filename with extension (helps Groq detect
                     format; also used to decide whether a WAV conversion
                     fallback is needed in the bytes path).
        lang:        optional ISO 639-1 language hint (e.g. "ru", "ar")
                     None = auto-detect (Whisper handles this well)
        use_turbo:   use whisper-large-v3-turbo instead of primary
                     (faster + cheaper, slightly lower accuracy)
        audio_url:   if given, sent as Groq's `url=` parameter instead of
                     uploading bytes — Groq fetches the file itself. Prefer
                     this over audio_bytes when the caller doesn't need
                     local bytes for anything else (VAD, conversion). See
                     transcribe_attachment() for the actual decision logic;
                     this function just does whichever one it's given.

    Returns TranscriptResult.
    On any error: success=False, text="", error=message.
    Never raises — caller (update_handler) handles errors.

    Billing note: audio_seconds is estimated from file size when
    Groq does not return duration directly (bytes path only — a URL-fetched
    file has no local size to estimate from, so duration is 0.0 unless Groq
    reports it). Actual billing is per audio hour transcribed — record
    audio_seconds in UsageEntry.
    """
    if not audio_url and not audio_bytes:
        return TranscriptResult(
            text="", model_used="", audio_seconds=0.0,
            success=False, error="neither audio_bytes nor audio_url provided",
        )

    if audio_bytes is not None and len(audio_bytes) > _MAX_FILE_SIZE_BYTES:
        return TranscriptResult(
            text="", model_used="", audio_seconds=0.0,
            success=False,
            error=f"audio file too large: {len(audio_bytes)} bytes (max {_MAX_FILE_SIZE_BYTES})",
        )

    model = _TURBO_MODEL if use_turbo else _PRIMARY_MODEL

    try:
        import httpx
        from app.settings import settings

        data = {"model": model}
        if lang:
            data["language"] = lang

        if audio_url:
            # URL path: Groq fetches the file itself, no local conversion
            # possible or needed here — the caller (transcribe_attachment)
            # is responsible for only reaching this branch with a file Groq
            # can already read (see its docstring for why WAV conversion,
            # when needed, happens before this call, not after).
            data["url"] = audio_url
            files = None
        else:
            # Convert to WAV only if the format isn't one Groq documents as
            # supported (see _GROQ_SUPPORTED_EXTENSIONS comment above — this
            # is a real fallback adapter now, not a default path for OGG).
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext not in _GROQ_SUPPORTED_EXTENSIONS:
                logger.info("Converting %s to WAV for Groq compatibility", filename)
                audio_bytes = await _convert_to_wav(audio_bytes, source_ext=ext)
                filename = filename.rsplit(".", 1)[0] + ".wav"

            # Groq Whisper uses multipart/form-data — not the standard chat completions endpoint
            files = {"file": (filename, audio_bytes, _mime_type(filename))}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files=files,
                data=data,
            )

        if response.status_code != 200:
            logger.error(
                "Whisper API error",
                extra={"status": response.status_code, "model": model},
            )
            return TranscriptResult(
                text="", model_used=model, audio_seconds=0.0,
                success=False,
                error=f"Whisper API status {response.status_code}: {response.text[:200]}",
            )

        body = response.json()
        transcript = body.get("text", "").strip()
        # Groq may return duration in seconds; fall back to size estimate.
        # URL path has no local bytes to estimate from — if Groq doesn't
        # report duration for a URL-fetched file, audio_seconds is 0.0 and
        # billing falls back to whatever usage_meter does for that case.
        audio_seconds = float(body.get("duration", 0)) or (
            _estimate_duration(len(audio_bytes)) if audio_bytes is not None else 0.0
        )

        if not transcript:
            return TranscriptResult(
                text="", model_used=model, audio_seconds=audio_seconds,
                success=False, error="empty transcript",
            )

        logger.info(
            "Whisper transcription complete",
            extra={"model": model, "chars": len(transcript), "seconds": audio_seconds},
        )
        return TranscriptResult(
            text=transcript,
            model_used=model,
            audio_seconds=audio_seconds,
            success=True,
        )

    except Exception as exc:
        logger.error(
            "Whisper transcription failed",
            extra={"model": model, "error": str(exc)},
        )
        return TranscriptResult(
            text="", model_used=model, audio_seconds=0.0,
            success=False, error=str(exc),
        )


async def transcribe_attachment(
    attachment,  # infra.attachment.Attachment — typed as untyped to avoid import cycle at module load
    lang: str | None = None,
    use_turbo: bool = False,
) -> TranscriptResult:
    """
    Target-architecture entry point: transcribe a voice message given as an
    Attachment (infra/attachment.py), instead of raw bytes.

    Order of operations, and why it's in this order (not simply "use URL if
    supported"):
      1. attachment.bytes() — VAD (is_silent) needs real bytes locally
         regardless of whether Groq can fetch by URL; there is no way to run
         ffmpeg's silencedetect against a remote URL without downloading it
         first, so this download is not optional even in the URL-first case.
      2. is_silent() on those bytes — unchanged from the pre-Attachment path.
      3. If a WAV conversion fallback is needed (format not in
         _GROQ_SUPPORTED_EXTENSIONS — should be rare now that "ogg" is
         included), it happens here, on the bytes we already have.
      4. Only now do we decide bytes vs. URL for the actual Groq call:
         - settings.groq_whisper_accepts_signed_url == True → request a
           signed URL for this attachment and send audio_url= (skips
           re-uploading bytes we already hold; saves the multipart body).
         - otherwise → send the bytes we already downloaded for VAD.
         Either way, the attachment itself never talks to Telegram — the
         bytes came from Supabase Storage in step 1.

    This keeps the "URL vs bytes" decision entirely inside this handler,
    informed by a settings flag — Attachment itself has no opinion on it.
    """
    raw = await attachment.bytes()

    _ext = attachment.filename.rsplit(".", 1)[-1].lower() if "." in attachment.filename else "ogg"

    if await is_silent(raw, source_ext=_ext):
        return TranscriptResult(
            text="", model_used="", audio_seconds=0.0,
            success=False, error="silent audio (VAD)",
        )

    from app.settings import settings

    if settings.groq_whisper_accepts_signed_url:
        url = await attachment.signed_url()
        return await transcribe(audio_url=url, lang=lang, use_turbo=use_turbo)

    return await transcribe(audio_bytes=raw, filename=attachment.filename, lang=lang, use_turbo=use_turbo)


async def download_telegram_voice(
    file_id: str,
    bot_token: str,
    *,
    supabase=None,
    attachment_ref: dict | None = None,
    retries: int = 2,
) -> tuple[bytes, str]:
    """
    Get the bytes of a Telegram voice/audio message.

    ARCH-change 2026-07 (attachments): this function used to call the
    Cloudflare Worker's /tg/ proxy directly (getFile + file download) from
    inside the HF container — and that outbound call showed the exact same
    ConnectError/ConnectTimeout class as the original sendMessage incident
    (see architecture_reality.md §1 and §5). The Worker now downloads the
    attachment itself (at webhook-receive time, before the update is even
    enqueued — see ceyona-worker/worker.js::downloadAndStoreAttachment) and
    uploads it to Supabase Storage. This function's job is now just to read
    those bytes back from Storage — the one outbound call that has never
    shown this failure class.

    `attachment_ref` is the `_attachment` dict the Worker attached to the
    update payload: {bucket, path, mime_type, size, file_id, kind}. When
    present, this function reads straight from Storage and never touches
    Telegram at all.

    Falls back to the old direct-to-Worker path ONLY if attachment_ref is
    missing — this happens if the Worker's own download/upload failed after
    its retries (see worker.js's honest fallback: it still enqueues the
    update without `_attachment` rather than silently dropping it). This
    fallback keeps voice messages working (in degraded form, subject to the
    original ConnectError risk) instead of failing outright in that edge case,
    but it's expected to be rare — see architecture_reality.md for what to
    check if it turns out not to be rare.

    Returns (audio_bytes, filename).
    Raises RuntimeError on failure.
    """
    if attachment_ref and attachment_ref.get("bucket") and attachment_ref.get("path"):
        try:
            audio_bytes = await _download_from_storage(
                supabase, attachment_ref["bucket"], attachment_ref["path"],
            )
            filename = attachment_ref["path"].rsplit("/", 1)[-1] or "voice.ogg"
            logger.info(
                "download_telegram_voice: read from Supabase Storage",
                extra={"file_id": file_id, "bucket": attachment_ref["bucket"],
                       "path": attachment_ref["path"], "size": len(audio_bytes)},
            )
            return audio_bytes, filename
        except Exception as exc:
            logger.error(
                "download_telegram_voice: Storage read failed — this should be rare, "
                "since Supabase is the one outbound call that hasn't shown ConnectError; "
                "see architecture_reality.md §5 if this recurs",
                extra={"file_id": file_id, "error": str(exc), "exc_type": type(exc).__name__},
            )
            raise RuntimeError(f"Storage read failed: {exc}") from exc

    logger.warning(
        "download_telegram_voice: no _attachment on update — falling back to direct "
        "Worker call (Worker's own download must have failed); this path is subject "
        "to the original ConnectError risk, see architecture_reality.md §4.1",
        extra={"file_id": file_id},
    )
    return await _download_telegram_voice_via_worker_fallback(
        file_id=file_id, bot_token=bot_token, retries=retries,
    )


async def _download_from_storage(supabase, bucket: str, path: str) -> bytes:
    """Thin wrapper so the sync supabase-py Storage call doesn't block the
    event loop — mirrors how ResilientSupabase's own table() calls are used
    elsewhere in this codebase (sync client, run via asyncio where needed)."""
    if supabase is None:
        raise RuntimeError("download_telegram_voice: supabase client not provided, cannot read from Storage")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: supabase.storage.from_(bucket).download(path)
    )


async def _download_telegram_voice_via_worker_fallback(
    file_id: str,
    bot_token: str,
    *,
    retries: int = 2,
) -> tuple[bytes, str]:
    """
    FALLBACK ONLY — see download_telegram_voice's docstring for when this
    path is used. This is the pre-2026-07 implementation, kept as-is (same
    ConnectError exposure it always had) rather than deleted, since it's
    still better than nothing when the Worker's own download failed.

    Two-step process, routed through the Cloudflare Worker's /tg/ proxy:
      1. getFile  → {TELEGRAM_PROXY_URL}/tg/bot{token}/getFile → file_path
      2. download → {TELEGRAM_PROXY_URL}/tg/file/bot{token}/{file_path}

    Retries up to `retries` times on network-level errors (ConnectError,
    RemoteProtocolError, etc.) and 429/5xx HTTP errors — these occur on
    HuggingFace Spaces under load bursts. Backoff: 0.5s, 1.0s.
    """
    import httpx
    from app.settings import settings

    _RETRYABLE_STATUS = {429, 500, 502, 503}

    base = settings.telegram_proxy_url.rstrip("/")
    if base:
        get_file_url = f"{base}/tg/bot{bot_token}/getFile"
    else:
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Step 1: getFile → file_path
                try:
                    r = await client.get(get_file_url, params={"file_id": file_id})
                except Exception as exc:
                    raise RuntimeError(
                        f"getFile network error: {type(exc).__name__}: {exc or 'no message'}"
                    ) from exc

                if r.status_code in _RETRYABLE_STATUS:
                    raise RuntimeError(f"getFile retryable status: {r.status_code}")
                if r.status_code != 200:
                    raise RuntimeError(f"getFile failed: {r.status_code} {r.text[:200]}")

                result = r.json()
                if not result.get("ok"):
                    raise RuntimeError(f"getFile failed: {result.get('description', 'unknown')}")

                file_path = result["result"]["file_path"]
                if base:
                    file_url = f"{base}/tg/file/bot{bot_token}/{file_path}"
                else:
                    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

                # Step 2: download the actual file bytes
                try:
                    r2 = await client.get(file_url)
                except Exception as exc:
                    raise RuntimeError(
                        f"Voice download network error: {type(exc).__name__}: {exc or 'no message'}"
                    ) from exc

                if r2.status_code in _RETRYABLE_STATUS:
                    raise RuntimeError(f"Voice download retryable status: {r2.status_code}")
                if r2.status_code != 200:
                    raise RuntimeError(f"File download failed: {r2.status_code}")

                filename = file_path.split("/")[-1] or "voice.ogg"
                return r2.content, filename

        except RuntimeError as exc:
            _is_retryable = any(s in str(exc) for s in ("network error", "retryable status"))
            if attempt < retries and _is_retryable:
                logger.warning(
                    "download_telegram_voice retrying (fallback path)",
                    extra={"attempt": attempt + 1, "error": str(exc), "file_id": file_id},
                )
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise

    raise RuntimeError("download_telegram_voice: exhausted retries (fallback path)")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def _convert_to_wav(audio_bytes: bytes, source_ext: str = "oga") -> bytes:
    """
    Convert audio bytes to WAV (16kHz mono) using ffmpeg.

    Fallback adapter, not a default path: only invoked (see transcribe())
    when the incoming file's extension isn't one Groq documents as
    supported. As of 2026-07, "ogg"/"oga" ARE in that supported set (see
    _GROQ_SUPPORTED_EXTENSIONS), so Telegram voice messages normally skip
    this entirely. This function exists for whatever format Groq's API
    doesn't accept — either a future format change on Groq's side, or an
    attachment kind this project doesn't send from Telegram today.

    Raises RuntimeError if ffmpeg fails.
    """
    in_path = out_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{source_ext}", delete=False) as f_in:
            f_in.write(audio_bytes)
            in_path = f_in.name

        out_path = in_path.rsplit(".", 1)[0] + ".wav"

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", in_path,
            "-ar", "16000", "-ac", "1",
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()[:300]}")

        with open(out_path, "rb") as f:
            return f.read()

    finally:
        if in_path and os.path.exists(in_path):
            os.unlink(in_path)
        if out_path and os.path.exists(out_path):
            os.unlink(out_path)


def _mime_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "ogg":  "audio/ogg",
        "oga":  "audio/ogg",
        "mp3":  "audio/mpeg",
        "wav":  "audio/wav",
        "m4a":  "audio/mp4",
        "mp4":  "audio/mp4",
        "webm": "audio/webm",
        "flac": "audio/flac",
    }.get(ext, "audio/ogg")


def _estimate_duration(size_bytes: int) -> float:
    """
    Rough duration estimate from file size for billing fallback.
    OGG Opus at Telegram quality ≈ 16 kbps → 2000 bytes/sec.
    """
    return size_bytes / 2000.0