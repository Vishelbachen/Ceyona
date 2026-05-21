from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Text-to-Speech (TTS) adapter. Per architecture.md §12, models1.md §12.
#
# Authority boundary:
#   MUST NOT: influence EPK, select execution tier, alter TruthMode
#   MAY:      synthesize audio from text via Groq Orpheus API
#
# Provider: Groq (api.groq.com)
# Models:
#   canopylabs/orpheus-v1-english    → English TTS  ($22.00 / 1M chars)
#   canopylabs/orpheus-arabic-saudi  → Arabic TTS   ($40.00 / 1M chars)
#
# Activation: is_voice_input = True AND response text available.
# Output: OGG Opus bytes sent to Telegram as voice message (sendVoice).
#
# Billing: tts_characters recorded in UsageEntry (separate from LLM tokens).
# Billing is per character, not per token.
#
# Language routing:
#   lang == "ar" → orpheus-arabic-saudi + arabic voice
#   all others   → orpheus-v1-english + english voice
#
# allam-2-7b role: Arabic normalization before TTS (models1.md §2).
# allam is called by multilingual_preprocessor, not here.
# TTS receives already-normalized Arabic text.
#
# Audio pipeline:
#   Groq Orpheus → WAV (response_format="wav") → ffmpeg → OGG Opus → sendVoice
#   ffmpeg is guaranteed present — installed in Dockerfile.
#   Telegram sendVoice requires OGG Opus. WAV is NOT accepted by sendVoice.
#
# Voice IDs (verified from Groq docs, May 2026):
#   English: autumn, diana, hannah, austin, daniel, troy
#   Arabic:  fahad, sultan, noura, lulwa, aisha
#   "default" is NOT a valid voice ID — Groq returns HTTP 400.
#
# Vocal directions ([cheerful], [whisper]):
#   Supported by orpheus-v1-english ONLY.
#   NOT supported by orpheus-arabic-saudi.
#
# Position in lifecycle:
#   Response Synthesizer → [HERE] → Telegram sendVoice
#   Runs AFTER synthesis, before Event Store write.

_ENGLISH_MODEL = "canopylabs/orpheus-v1-english"
_ARABIC_MODEL  = "canopylabs/orpheus-arabic-saudi"

# Orpheus has a practical limit on single-call synthesis
_MAX_CHARS_PER_CALL = 5000

# Valid voice IDs per model — verified from Groq docs (May 2026).
# "default" is NOT a valid value and returns HTTP 400.
# English voices: autumn, diana, hannah, austin, daniel, troy
# Arabic voices:  fahad, sultan, noura, lulwa, aisha
_ENGLISH_VOICE = "diana"   # female, natural — suitable for conversational assistant
_ARABIC_VOICE  = "noura"   # female, clear — suitable for conversational assistant


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes      # OGG Opus bytes (ready for Telegram sendVoice)
    model_used: str
    char_count: int         # for billing: tts_characters
    success: bool
    error: str = ""


def _select_model(lang: str) -> str:
    """Route to Arabic or English Orpheus model based on detected language."""
    return _ARABIC_MODEL if lang == "ar" else _ENGLISH_MODEL


def _select_voice(lang: str) -> str:
    """Return a valid Orpheus voice ID for the given language."""
    return _ARABIC_VOICE if lang == "ar" else _ENGLISH_VOICE


async def _convert_wav_to_ogg(wav_bytes: bytes) -> bytes:
    """
    Convert WAV bytes to OGG Opus using ffmpeg.

    Required because:
    - Groq Orpheus returns WAV (response_format="wav")
    - Telegram sendVoice requires OGG Opus

    Uses the same ffmpeg subprocess pattern as speech_to_text._convert_to_wav.
    ffmpeg is guaranteed present — it is installed in Dockerfile.

    Raises RuntimeError if ffmpeg fails (caller catches and falls back to text).
    """
    import asyncio
    import os
    import tempfile

    in_path = out_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in:
            f_in.write(wav_bytes)
            in_path = f_in.name

        out_path = in_path.rsplit(".", 1)[0] + ".ogg"

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", in_path,
            "-c:a", "libopus",       # Opus codec — required by Telegram sendVoice
            "-b:a", "32k",           # 32kbps — sufficient for speech
            "-ar", "48000",          # 48kHz — Groq TTS fixed sample rate
            "-ac", "1",              # mono
            out_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg WAV→OGG failed: {stderr.decode()[:300]}")

        with open(out_path, "rb") as f:
            return f.read()

    finally:
        if in_path and os.path.exists(in_path):
            os.unlink(in_path)
        if out_path and os.path.exists(out_path):
            os.unlink(out_path)


async def synthesize(
    text: str,
    lang: str = "en",
) -> SynthesisResult:
    """
    Convert text to speech using Groq Orpheus.

    Args:
        text: response text to synthesize (already corrected by synthesizer)
        lang: user language code — determines model and voice selection

    Returns SynthesisResult with OGG Opus bytes (ready for Telegram sendVoice).
    On any error: success=False, audio_bytes=b"", error=message.
    Never raises — caller (update_handler) handles errors gracefully
    (falls back to text-only response on TTS failure).

    Billing: record char_count as tts_characters in UsageEntry.

    Voice IDs (verified Groq docs, May 2026):
      English: diana (default), autumn, hannah, austin, daniel, troy
      Arabic:  noura (default), fahad, sultan, lulwa, aisha
    "default" is NOT a valid voice ID — returns HTTP 400.

    Audio pipeline:
      Groq Orpheus → WAV → ffmpeg → OGG Opus → Telegram sendVoice
    """
    if not text or not text.strip():
        return SynthesisResult(
            audio_bytes=b"", model_used="", char_count=0,
            success=False, error="empty text",
        )

    # Truncate to practical limit — long texts would timeout
    text_to_synth = text[:_MAX_CHARS_PER_CALL]
    model = _select_model(lang)
    voice = _select_voice(lang)
    char_count = len(text_to_synth)

    try:
        import httpx

        from app.settings import settings

        # Groq TTS endpoint (OpenAI-compatible audio/speech).
        # voice: must be a valid Orpheus voice ID — "default" returns HTTP 400.
        # response_format: "wav" — only format supported by Groq Orpheus (May 2026).
        # Output is converted to OGG Opus before returning (for Telegram sendVoice).
        payload = {
            "model": model,
            "input": text_to_synth,
            "voice": voice,
            "response_format": "wav",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            logger.error(
                "Orpheus TTS API error",
                extra={"status": response.status_code, "model": model, "voice": voice},
            )
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False,
                error=f"TTS API status {response.status_code}: {response.text[:200]}",
            )

        wav_bytes = response.content
        if not wav_bytes:
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False, error="empty audio response",
            )

        # Convert WAV → OGG Opus for Telegram sendVoice compatibility
        try:
            ogg_bytes = await _convert_wav_to_ogg(wav_bytes)
        except Exception as conv_exc:
            logger.error(
                "WAV→OGG conversion failed",
                extra={"model": model, "error": str(conv_exc)},
            )
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False, error=f"audio conversion failed: {conv_exc}",
            )

        logger.info(
            "Orpheus TTS complete",
            extra={
                "model": model, "voice": voice,
                "chars": char_count,
                "wav_bytes": len(wav_bytes),
                "ogg_bytes": len(ogg_bytes),
            },
        )
        return SynthesisResult(
            audio_bytes=ogg_bytes,
            model_used=model,
            char_count=char_count,
            success=True,
        )

    except Exception as exc:
        logger.error(
            "Orpheus TTS failed",
            extra={"model": model, "voice": voice, "error": str(exc)},
        )
        return SynthesisResult(
            audio_bytes=b"", model_used=model, char_count=char_count,
            success=False, error=str(exc),
        )
