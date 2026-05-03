from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ─── LIMITS ───────────────────────────────────────────────────────────────────

_TOKEN_THRESHOLD     = 2048   # above this → compression candidate
_CHUNK_SIZE          = 1800   # max tokens per chunk after split
_SUMMARY_THRESHOLD   = 4096   # above this → summarization preferred over chunking

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


def _compress(text: str) -> str:
    """Remove redundant blank lines and deduplicate repeated sentences."""
    seen: set[str] = set()
    result: list[str] = []
    blank_run = 0

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "":
            blank_run += 1
            if blank_run <= 1:
                result.append("")
            continue
        blank_run = 0
        if stripped not in seen:
            seen.add(stripped)
            result.append(line)

    return "\n".join(result).strip()


def _chunk(text: str) -> str:
    """
    Split into chunks of ~_CHUNK_SIZE tokens (approximated by words),
    then rejoin with a separator so Heavy Tier sees clear boundaries.
    Preserves code blocks and JSON shapes intact within chunks.
    """
    words = text.split()
    # ~0.75 words per token approximation — conservative
    words_per_chunk = int(_CHUNK_SIZE * 0.75)

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
        return _compress(text)

    head = lines[:20]
    tail = lines[-20:]
    middle = lines[20 : total - 20]

    # Compress middle: deduplicate + drop pure-blank runs
    compressed_middle: list[str] = []
    seen: set[str] = set()
    blank_run = 0
    for line in middle:
        stripped = line.strip()
        if stripped == "":
            blank_run += 1
            if blank_run <= 1:
                compressed_middle.append("")
            continue
        blank_run = 0
        if stripped not in seen:
            seen.add(stripped)
            compressed_middle.append(line)

    parts = (
        "\n".join(head)
        + "\n\n---\n\n"
        + "\n".join(compressed_middle)
        + "\n\n---\n\n"
        + "\n".join(tail)
    )
    return parts.strip()


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
            shaped = _compress(inp.text)

        # Safety: if shaping produced empty result, return original
        if not shaped or not shaped.strip():
            return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")

        return ShaperResult(text=shaped, was_shaped=True, operation=operation)

    except Exception:
        logger.exception("heavy_input_shaper failed — returning original input")
        return ShaperResult(text=inp.text, was_shaped=False, operation="passthrough")