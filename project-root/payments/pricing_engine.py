import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_NANO = 1_000_000_000        # 1 TON = 1_000_000_000 nanoTON
_COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=the-open-network&vs_currencies=usd"
)
_TIMEOUT = 10.0
_FALLBACK_TON_USD = 3.0      # fallback if CoinGecko is unavailable


async def get_ton_price_usd() -> float:
    """
    Fetch current TON/USD price from CoinGecko.
    Falls back to _FALLBACK_TON_USD on error.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(_COINGECKO_URL)
            response.raise_for_status()
            data = response.json()
            price = data["the-open-network"]["usd"]
            logger.info("TON price fetched", extra={"ton_usd": price})
            return float(price)
    except Exception as exc:
        logger.warning(
            "TON price fetch failed, using fallback",
            extra={"error": str(exc), "fallback": _FALLBACK_TON_USD},
        )
        return _FALLBACK_TON_USD


def nano_to_ton(nano: int) -> float:
    """Convert nanoTON to TON."""
    return nano / _NANO


def ton_to_nano(ton: float) -> int:
    """Convert TON to nanoTON."""
    return int(ton * _NANO)


async def nano_to_usd(nano: int) -> float:
    """Convert nanoTON to USD using live price and platform topup_rate.

    Returns USD credits to add to user balance.
    topup_rate < 1.0 activates platform margin at top-up time — the only
    place margin is applied. All per-request deductions use raw cost only.
    See economic.md §8 and app/settings.py (topup_rate).
    """
    ton = nano_to_ton(nano)
    price = await get_ton_price_usd()
    return ton * price * settings.topup_rate


async def usd_to_nano(usd: float) -> int:
    """Convert USD to nanoTON using live price."""
    price = await get_ton_price_usd()
    if price <= 0:
        return 0
    ton = usd / price
    return ton_to_nano(ton)


def apply_margin(usd: float, margin: float = 1.3) -> float:
    """
    Apply platform margin to cost.
    Default 1.3 = 30% markup over raw LLM cost.
    """
    return usd * margin


# qwen/qwen3.6-27b vision extraction rates (Groq, Jun 2026)
# Replaces llama-4-scout-17b-16e-instruct (deprecated Jul 17, 2026).
# Source: groq.com/pricing, Jun 22, 2026 — same rates as GENERAL tier.
# $0.60 input / $3.00 output per 1M tokens.
# models.md §26.1 — Role A (Vision Extraction), economic.md §1.1.
_VISION_RATES: dict[str, float] = {"input": 0.60, "output": 3.00}


def vision_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Compute raw cost for a qwen/qwen3.6-27b vision extraction call.

    This is the single authoritative billing function for vision tokens.
    Called by update_handler before the balance guard — always based on
    actual token counts from the Groq API response, never estimated.

    Falls back to 0.001 conservative estimate at the call site when tokens
    are unavailable (failed=True path in vision_handler).

    Model: qwen/qwen3.6-27b (replaces llama-4-scout, deprecated Jul 17, 2026).
    Rates: $0.60 input / $3.00 output per 1M tokens (economic.md §1.1).
    """
    return (
        input_tokens * _VISION_RATES["input"]
        + output_tokens * _VISION_RATES["output"]
    ) / 1_000_000