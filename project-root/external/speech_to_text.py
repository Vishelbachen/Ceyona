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

# Maximum audio file size Groq accepts (25 MB)
_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Formats natively supported by Groq Whisper API
_GROQ_SUPPORTED_EXTENSIONS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "flac"}


@dataclass(frozen=True)
class TranscriptResult:
    text: str               # raw transcript from Whisper
    model_used: str         # which Whisper model was used
    audio_seconds: float    # duration for billing
    success: bool
    error: str = ""


async def transcribe(
    audio_bytes: bytes,
    filename: str = "voice.ogg",
    lang: str | None = None,
    use_turbo: bool = False,
) -> TranscriptResult:
    """
    Transcribe audio bytes using Groq Whisper.

    Args:
        audio_bytes: raw audio content (OGG/MP3/WAV/M4A)
        filename:    original filename with extension (helps Groq detect format)
        lang:        optional ISO 639-1 language hint (e.g. "ru", "ar")
                     None = auto-detect (Whisper handles this well)
        use_turbo:   use whisper-large-v3-turbo instead of primary
                     (faster + cheaper, slightly lower accuracy)

    Returns TranscriptResult.
    On any error: success=False, text="", error=message.
    Never raises — caller (update_handler) handles errors.

    Billing note: audio_seconds is estimated from file size when
    Groq does not return duration directly. Actual billing is per
    audio hour transcribed — record audio_seconds in UsageEntry.
    """
    if not audio_bytes:
        return TranscriptResult(
            text="", model_used="", audio_seconds=0.0,
            success=False, error="empty audio bytes",
        )

    if len(audio_bytes) > _MAX_FILE_SIZE_BYTES:
        return TranscriptResult(
            text="", model_used="", audio_seconds=0.0,
            success=False,
            error=f"audio file too large: {len(audio_bytes)} bytes (max {_MAX_FILE_SIZE_BYTES})",
        )

    model = _TURBO_MODEL if use_turbo else _PRIMARY_MODEL

    try:
        import httpx
        from app.settings import settings

        # Convert OGG/OGA (Telegram voice) to WAV — Groq Whisper does not accept OGG/Opus
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in _GROQ_SUPPORTED_EXTENSIONS:
            logger.info("Converting %s to WAV for Groq compatibility", filename)
            audio_bytes = await _convert_to_wav(audio_bytes, source_ext=ext)
            filename = filename.rsplit(".", 1)[0] + ".wav"

        # Groq Whisper uses multipart/form-data — not the standard chat completions endpoint
        files = {"file": (filename, audio_bytes, _mime_type(filename))}
        data  = {"model": model}
        if lang:
            data["language"] = lang

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
        # Groq may return duration in seconds; fall back to size estimate
        audio_seconds = float(body.get("duration", 0)) or _estimate_duration(len(audio_bytes))

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


async def download_telegram_voice(
    file_id: str,
    bot_token: str,
    *,
    retries: int = 2,
) -> tuple[bytes, str]:
    """
    Download a Telegram voice/audio file by file_id.

    Returns (audio_bytes, filename).
    Raises RuntimeError on download failure.

    Two-step process:
      1. getFile → get file_path
      2. download from file.telegram.org/{bot_token}/{file_path}

    Retries up to `retries` times on network-level errors (ConnectError,
    RemoteProtocolError, etc.) and 429/5xx HTTP errors — these occur on
    HuggingFace Spaces under load bursts. Backoff: 0.5s, 1.0s.
    """
    import httpx

    _RETRYABLE_STATUS = {429, 500, 502, 503}
    api_base = f"https://api.telegram.org/bot{bot_token}"

    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: resolve file_path
                try:
                    r = await client.get(f"{api_base}/getFile", params={"file_id": file_id})
                except Exception as exc:
                    raise RuntimeError(
                        f"getFile network error: {type(exc).__name__}: {exc or 'no message'}"
                    ) from exc

                if r.status_code in _RETRYABLE_STATUS:
                    raise RuntimeError(f"getFile retryable status: {r.status_code}")
                if r.status_code != 200:
                    raise RuntimeError(f"getFile failed: {r.status_code} {r.text[:200]}")

                file_info = r.json().get("result", {})
                file_path = file_info.get("file_path", "")
                if not file_path:
                    raise RuntimeError("getFile returned empty file_path")

                # Step 2: download
                download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                try:
                    r2 = await client.get(download_url)
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
                    "download_telegram_voice retrying",
                    extra={"attempt": attempt + 1, "error": str(exc), "file_id": file_id},
                )
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            raise

        filename = file_path.split("/")[-1] or "voice.ogg"
        return r2.content, filename


# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def _convert_to_wav(audio_bytes: bytes, source_ext: str = "oga") -> bytes:
    """
    Convert audio bytes to WAV (16kHz mono) using ffmpeg.
    Required for OGG/Opus files from Telegram — not supported by Groq Whisper API.
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