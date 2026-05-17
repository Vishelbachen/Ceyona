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
# Output: raw audio bytes (WAV) sent to Telegram as voice message.
#
# Billing: tts_characters recorded in UsageEntry (separate from LLM tokens).
# Billing is per character, not per token.
#
# Language routing:
#   lang == "ar" → orpheus-arabic-saudi
#   all others   → orpheus-v1-english
#
# allam-2-7b role: Arabic normalization before TTS (models1.md §2).
# allam is called by multilingual_preprocessor, not here.
# TTS receives already-normalized Arabic text.
#
# Telegram audio format:
#   Telegram voice messages require OGG Opus format.
#   Orpheus returns WAV — conversion via pydub/ffmpeg or direct OGG if supported.
#   For now: send as audio file (sendAudio), not voice (sendVoice),
#   which accepts WAV/MP3 without format conversion requirement.
#
# Position in lifecycle:
#   Response Synthesizer → [HERE] → Telegram sendAudio
#   Runs AFTER synthesis, before Event Store write.

_ENGLISH_MODEL = "canopylabs/orpheus-v1-english"
_ARABIC_MODEL  = "canopylabs/orpheus-arabic-saudi"

# Orpheus has a practical limit on single-call synthesis
_MAX_CHARS_PER_CALL = 5000


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes      # raw audio content (WAV)
    model_used: str
    char_count: int         # for billing: tts_characters
    success: bool
    error: str = ""


def _select_model(lang: str) -> str:
    """Route to Arabic or English Orpheus model based on detected language."""
    return _ARABIC_MODEL if lang == "ar" else _ENGLISH_MODEL


async def synthesize(
    text: str,
    lang: str = "en",
) -> SynthesisResult:
    """
    Convert text to speech using Groq Orpheus.

    Args:
        text: response text to synthesize (already corrected by synthesizer)
        lang: user language code — determines model selection

    Returns SynthesisResult.
    On any error: success=False, audio_bytes=b"", error=message.
    Never raises — caller (update_handler) handles errors gracefully
    (falls back to text-only response on TTS failure).

    Billing: record char_count as tts_characters in UsageEntry.
    """
    if not text or not text.strip():
        return SynthesisResult(
            audio_bytes=b"", model_used="", char_count=0,
            success=False, error="empty text",
        )

    # Truncate to practical limit — long texts would timeout
    text_to_synth = text[:_MAX_CHARS_PER_CALL]
    model = _select_model(lang)
    char_count = len(text_to_synth)

    try:
        import httpx
        from app.settings import settings

        # Groq TTS endpoint (OpenAI-compatible audio/speech)
        payload = {
            "model": model,
            "input": text_to_synth,
            "voice": "default",          # Orpheus default voice
            "response_format": "wav",    # WAV → easiest for Telegram sendAudio
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
                extra={"status": response.status_code, "model": model},
            )
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False,
                error=f"TTS API status {response.status_code}: {response.text[:200]}",
            )

        audio_bytes = response.content
        if not audio_bytes:
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False, error="empty audio response",
            )

        logger.info(
            "Orpheus TTS complete",
            extra={"model": model, "chars": char_count, "audio_bytes": len(audio_bytes)},
        )
        return SynthesisResult(
            audio_bytes=audio_bytes,
            model_used=model,
            char_count=char_count,
            success=True,
        )

    except Exception as exc:
        logger.error(
            "Orpheus TTS failed",
            extra={"model": model, "error": str(exc)},
        )
        return SynthesisResult(
            audio_bytes=b"", model_used=model, char_count=char_count,
            success=False, error=str(exc),
        )