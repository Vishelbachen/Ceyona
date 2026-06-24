from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── ROLE ─────────────────────────────────────────────────────────────────────
# Text-to-Speech (TTS) adapter. Per architecture.md §12, models.md §12.
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
# allam-2-7b role: Arabic normalization before TTS (models.md §2).
# allam is called by multilingual_preprocessor, not here.
# TTS receives already-normalized Arabic text.
#
# Audio pipeline:
#   Groq Orpheus → WAV (response_format="wav") → ffmpeg → OGG Opus → sendVoice
#   ffmpeg is guaranteed present — installed in Dockerfile.
#   Telegram sendVoice requires OGG Opus. WAV is NOT accepted by sendVoice.
#
# Voice IDs (verified from Groq docs, Jun 2026):
#   English: autumn, diana, hannah, austin, daniel, troy
#   Arabic:  fahad, sultan, noura, lulwa, aisha, abdullah
#   "default" is NOT a valid voice ID — Groq returns HTTP 400.
#
# Vocal directions ([cheerful], [whisper]):
#   Supported by orpheus-v1-english ONLY.
#   NOT supported by orpheus-arabic-saudi.
#
# CHUNKING (models.md §27.7 — 200 chars/request hard limit):
#   Orpheus accepts max 200 characters per API call (official Groq docs, Jun 2026).
#   Long text is split into sentence-aware chunks ≤ _MAX_CHARS_PER_CHUNK chars.
#   Each chunk is synthesised in sequence; WAV payloads are concatenated before
#   OGG conversion. Concatenation is raw PCM-aware (strips WAV headers from all
#   chunks except the first, then reattaches a single header).
#   char_count reflects TOTAL characters across all chunks (for billing).
#
# Position in lifecycle:
#   Response Synthesizer → [HERE] → Telegram sendVoice
#   Runs AFTER synthesis, before Event Store write.

_ENGLISH_MODEL = "canopylabs/orpheus-v1-english"
_ARABIC_MODEL  = "canopylabs/orpheus-arabic-saudi"

# Hard limit per Groq official docs (Jun 2026). models.md §27.7.
# Previous value was 5000 — incorrect.
_MAX_CHARS_PER_CHUNK = 200

# Valid voice IDs per model — verified from Groq docs (Jun 2026).
# "default" is NOT a valid value and returns HTTP 400.
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


def _split_into_chunks(text: str, max_chars: int = _MAX_CHARS_PER_CHUNK) -> list[str]:
    """
    Split text into chunks of at most max_chars characters.

    Strategy: sentence-aware splitting.
    1. Try to break at sentence boundaries (. ! ? followed by space or end).
    2. If a sentence itself exceeds max_chars, split at the last space within
       the limit (word boundary).
    3. If no space found within limit, hard-cut at max_chars (last resort).

    Returns a list of non-empty strings, each ≤ max_chars characters.
    """
    import re

    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    # Split into sentences first (keep delimiters attached).
    sentence_re = re.compile(r'(?<=[.!?…])\s+')
    sentences = sentence_re.split(text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Sentence fits in current chunk with a space separator.
        candidate = (current + " " + sentence).strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
            continue

        # Flush current chunk before starting a new one.
        if current:
            chunks.append(current)
            current = ""

        # Sentence itself fits cleanly.
        if len(sentence) <= max_chars:
            current = sentence
            continue

        # Sentence is too long — split at word boundaries.
        words = sentence.split(" ")
        word_buf = ""
        for word in words:
            candidate = (word_buf + " " + word).strip() if word_buf else word
            if len(candidate) <= max_chars:
                word_buf = candidate
            else:
                if word_buf:
                    chunks.append(word_buf)
                # If single word exceeds max_chars, hard-cut.
                if len(word) > max_chars:
                    for i in range(0, len(word), max_chars):
                        chunks.append(word[i:i + max_chars])
                    word_buf = ""
                else:
                    word_buf = word
        if word_buf:
            current = word_buf

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def _concat_wav_chunks(wav_chunks: list[bytes]) -> bytes:
    """
    Concatenate multiple WAV byte payloads into a single valid WAV file.

    WAV structure: 44-byte header + raw PCM data.
    Strategy: keep the header from the first chunk, strip headers from all
    subsequent chunks, concatenate raw PCM, update the data-size fields.

    Assumes all chunks share the same sample rate, bit depth, and channel count
    (guaranteed here since all come from the same Orpheus model/voice combo).

    Falls back to simple byte concatenation if parsing fails — ffmpeg is
    tolerant of concatenated WAV files with minor header inconsistencies.
    """
    if not wav_chunks:
        return b""
    if len(wav_chunks) == 1:
        return wav_chunks[0]

    try:
        import struct

        # Parse first chunk to get the header (44 bytes standard PCM WAV).
        first = wav_chunks[0]
        if len(first) < 44 or first[:4] != b"RIFF":
            # Not a standard WAV — fall back to concat.
            return b"".join(wav_chunks)

        pcm_parts: list[bytes] = [first[44:]]  # PCM data from first chunk

        for chunk in wav_chunks[1:]:
            if len(chunk) >= 44 and chunk[:4] == b"RIFF":
                pcm_parts.append(chunk[44:])
            else:
                # Unexpected format — append raw (ffmpeg will cope).
                pcm_parts.append(chunk)

        all_pcm = b"".join(pcm_parts)
        total_data_size = len(all_pcm)
        total_riff_size = total_data_size + 36  # 44 - 8 (RIFF + size field itself)

        # Rebuild header from first chunk, patching the size fields.
        header = bytearray(first[:44])
        struct.pack_into("<I", header, 4, total_riff_size)   # ChunkSize at offset 4
        struct.pack_into("<I", header, 40, total_data_size)  # Subchunk2Size at offset 40

        return bytes(header) + all_pcm

    except Exception as exc:
        logger.warning("WAV concat failed — falling back to raw join", extra={"error": str(exc)})
        return b"".join(wav_chunks)


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


async def _synthesize_chunk(
    text: str,
    model: str,
    voice: str,
) -> bytes | None:
    """
    Synthesise a single chunk (≤ _MAX_CHARS_PER_CHUNK chars) via Groq Orpheus.

    Returns raw WAV bytes on success, None on any error.
    Errors are logged but not raised — caller decides how to handle partial failures.
    """
    import httpx
    from app.settings import settings

    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "response_format": "wav",
    }

    try:
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
                "Orpheus TTS chunk error",
                extra={
                    "status": response.status_code,
                    "model": model,
                    "voice": voice,
                    "chunk_len": len(text),
                    "body": response.text[:200],
                },
            )
            return None

        wav = response.content
        if not wav:
            logger.error("Orpheus TTS chunk: empty response", extra={"model": model})
            return None

        return wav

    except Exception as exc:
        logger.error(
            "Orpheus TTS chunk exception",
            extra={"model": model, "voice": voice, "error": str(exc)},
        )
        return None


async def synthesize(
    text: str,
    lang: str = "en",
) -> SynthesisResult:
    """
    Convert text to speech using Groq Orpheus with 200-char chunking.

    Args:
        text: response text to synthesize (already corrected by synthesizer)
        lang: user language code — determines model and voice selection

    Chunking contract (models.md §27.7):
        Orpheus max input is 200 chars/request (Groq official docs, Jun 2026).
        Text is split sentence-aware into chunks ≤ 200 chars.
        Each chunk is synthesised sequentially (not concurrently — Groq TTS
        does not guarantee ordering under concurrent requests for the same session).
        WAV payloads are header-merged, then converted to OGG Opus once.
        char_count = total characters across all chunks (for billing accuracy).

    Returns SynthesisResult with OGG Opus bytes (ready for Telegram sendVoice).
    On any error: success=False, audio_bytes=b"", error=message.
    Never raises — caller (update_handler) handles errors gracefully
    (falls back to text-only response on TTS failure).
    """
    if not text or not text.strip():
        return SynthesisResult(
            audio_bytes=b"", model_used="", char_count=0,
            success=False, error="empty text",
        )

    model = _select_model(lang)
    voice = _select_voice(lang)

    chunks = _split_into_chunks(text.strip())
    if not chunks:
        return SynthesisResult(
            audio_bytes=b"", model_used=model, char_count=0,
            success=False, error="text produced no chunks after splitting",
        )

    char_count = sum(len(c) for c in chunks)

    logger.info(
        "Orpheus TTS: synthesising",
        extra={
            "model": model, "voice": voice,
            "total_chars": char_count,
            "chunks": len(chunks),
        },
    )

    # Synthesise chunks sequentially — order must be preserved.
    wav_chunks: list[bytes] = []
    for idx, chunk in enumerate(chunks):
        wav = await _synthesize_chunk(chunk, model, voice)
        if wav is None:
            logger.error(
                "Orpheus TTS: chunk failed — aborting synthesis",
                extra={"chunk_index": idx, "chunk_len": len(chunk), "total_chunks": len(chunks)},
            )
            return SynthesisResult(
                audio_bytes=b"", model_used=model, char_count=char_count,
                success=False, error=f"chunk {idx}/{len(chunks)} synthesis failed",
            )
        wav_chunks.append(wav)

    # Merge WAV payloads into a single valid WAV file.
    merged_wav = _concat_wav_chunks(wav_chunks)

    # Convert merged WAV → OGG Opus for Telegram sendVoice.
    try:
        ogg_bytes = await _convert_wav_to_ogg(merged_wav)
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
            "chunks": len(chunks),
            "total_chars": char_count,
            "merged_wav_bytes": len(merged_wav),
            "ogg_bytes": len(ogg_bytes),
        },
    )
    return SynthesisResult(
        audio_bytes=ogg_bytes,
        model_used=model,
        char_count=char_count,
        success=True,
    )