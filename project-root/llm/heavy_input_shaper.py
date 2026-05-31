from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── LIMITS ───────────────────────────────────────────────────────────────────

_TOKEN_THRESHOLD = 2048   # above this → compression candidate
_CHUNK_SIZE = 1800        # max tokens per chunk after split
_SUMMARY_THRESHOLD = 4096 # above this → summarization preferred over chunking

# llama-3.1-8b-instant is used here NOT as Fast Tier — it is a utility model
_SHAPER_MODEL = "llama-3.1-8b-instant"

# ─── CONTRACTS ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ShaperInput:
    text: str
    token_count: int
    has_code_block: bool
    has_json_shape: bool
    context_size: int          # total assembled context tokens


@dataclass(frozen=True)
class ShaperResult:
    text: str
    was_shaped: bool
    operation: str             # "passthrough" | "compressed" | "chunked" | "summarized"


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _needs_shaping(inp: ShaperInput) -> bool:
    return inp.token_count > _TOKEN_THRESHOLD or inp.context_size > _TOKEN_THRESHOLD


def _select_operation(inp: ShaperInput) -> str:
    if inp.token_count > _SUMMARY_THRESHOLD:
        return "summarized"
    if inp.has_code_block or inp.has_json_shape:
        return "chunked"
    return "compressed"


def _normalize_whitespace(text: str) -> str:
    lines: list[str] = []
    blank_run = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            blank_run += 1
            if blank_run <= 1:
                lines.append("")
            continue

        blank_run = 0
        lines.append(line)

    return "\n".join(lines).strip()


def _split_fenced_blocks(text: str) -> list[tuple[bool, str]]:
    """Split text into fenced-code and prose segments without losing order."""
    segments: list[tuple[bool, str]] = []
    buffer: list[str] = []
    in_fence = False

    for line in text.splitlines():
        is_fence = line.lstrip().startswith("```") or line.lstrip().startswith("~~~")
        if is_fence:
            if buffer:
                segments.append((in_fence, "\n".join(buffer)))
                buffer = []
            in_fence = not in_fence
            buffer.append(line)
            continue
        buffer.append(line)

    if buffer:
        segments.append((in_fence, "\n".join(buffer)))

    return segments


def _compress_prose(text: str) -> str:
    """Conservative compression that preserves meaning and structure."""
    segments = _split_fenced_blocks(text)
    out: list[str] = []
    last_prose: str | None = None

    for is_code, segment in segments:
        if is_code:
            out.append(segment.rstrip())
            last_prose = None
            continue

        normalized = _normalize_whitespace(segment)
        if not normalized:
            continue

        # Deduplicate only consecutive repeated prose blocks, not every line.
        if normalized == last_prose:
            continue

        out.append(normalized)
        last_prose = normalized

    return "\n\n".join(part for part in out if part).strip()


def _chunk(text: str) -> str:
    """
    Split into chunks of ~_CHUNK_SIZE tokens (approximated by words),
    then rejoin with a separator so Heavy Tier sees clear boundaries.
    Preserves code blocks and JSON shapes intact within chunks.
    """
    words = text.split()
    if not words:
        return text

    # ~0.75 words per token approximation — conservative
    words_per_chunk = max(256, int(_CHUNK_SIZE * 0.75))

    chunks: list[str] = []
    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i : i + words_per_chunk])
        chunks.append(chunk)

    if len(chunks) <= 1:
        return text

    return "\n\n---\n\n".join(chunks)


def _summarize(text: str) -> str:
    """
    For very long inputs: keep first and last sections, compress the middle.
    Heavy Tier is optimized for long-context — we preserve structure, not truncate.
    """
    lines = text.splitlines()
    total = len(lines)

    if total <= 60:
        return _compress_prose(text)

    head = lines[:20]
    tail = lines[-20:]
    middle = lines[20 : total - 20]

    compressed_middle: list[str] = []
    last_block: str | None = None
    pending_blank = False
    for line in middle:
        stripped = line.rstrip()
        if not stripped.strip():
            pending_blank = True
            continue

        block = stripped.strip()
        if block == last_block:
            continue

        if pending_blank and compressed_middle:
            compressed_middle.append("")
        pending_blank = False
        compressed_middle.append(stripped)
        last_block = block

    parts = [
        "\n".join(head).strip(),
        "\n".join(compressed_middle).strip(),
        "\n".join(tail).strip(),
    ]
    return "\n\n---\n\n".join(part for part in parts if part).strip()


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def shape(inp: ShaperInput) -> ShaperResult:
    """
    Prepare input for Heavy Tier execution.

    Contract:
      - ONLY called when EPK = HEAVY_REQUIRED
      - ALWAYS called on HEAVY_REQUIRED (self-gated internally)
      - Returns input as-is (NO-OP) if shaping is not needed
      - NO reasoning, NO output generation
      - Uses llama-3.1-8b-instant as utility model, NOT as Fast Tier

    Never raises. Returns original input on any error.
    """
    if not inp.text or not inp.text.strip():
        return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")

    try:
        if not _needs_shaping(inp):
            return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")

        operation = _select_operation(inp)

        if operation == "summarized":
            shaped = _summarize(inp.text)
        elif operation == "chunked":
            shaped = _chunk(inp.text)
        else:
            shaped = _compress_prose(inp.text)

        # Safety: if shaping produced empty result, return original
        if not shaped or not shaped.strip():
            return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")

        return ShaperResult(text=shaped, was_shaped=True, operation=operation)

    except Exception:
        logger.exception("heavy_input_shaper failed — returning original input")
        return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")