import logging

import httpx

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
    """Convert nanoTON to USD using live price."""
    ton = nano_to_ton(nano)
    price = await get_ton_price_usd()
    return ton * price


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