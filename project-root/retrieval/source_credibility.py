from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ─── TRUST TIERS ──────────────────────────────────────────────────────────────

class TrustTier(str, Enum):
    AUTHORITATIVE = "authoritative"   # official gov/transport/institutional sources
    TRUSTED       = "trusted"         # established news, major aggregators, wikis
    NEUTRAL       = "neutral"         # unknown — not blocked, not elevated
    DEGRADED      = "degraded"        # low-signal: forums, Q&A spam, SEO farms
    BLOCKED       = "blocked"         # known junk — filtered out before LLM sees it


# ─── DOMAIN TRUST REGISTRY ────────────────────────────────────────────────────
# Single source of truth for domain trust classification.
# Previously _JUNK_DOMAINS lived in external/search.py as a flat frozenset.
# Migrated here to support graduated scoring and centralised governance.
#
# Add new entries here as junk sources are discovered in production.
# Never add to search.py — that module delegates to this one.

_DOMAIN_TRUST: dict[str, TrustTier] = {

    # ── AUTHORITATIVE ─────────────────────────────────────────────────────────
    # Official transport / city / government sources
    "mos.ru":              TrustTier.AUTHORITATIVE,   # Официальный портал Москвы
    "mintrans.ru":         TrustTier.AUTHORITATIVE,   # Министерство транспорта РФ
    "mosgortrans.ru":      TrustTier.AUTHORITATIVE,   # Мосгортранс
    "transport.mos.ru":    TrustTier.AUTHORITATIVE,
    "russianrail.com":     TrustTier.AUTHORITATIVE,
    "rzd.ru":              TrustTier.AUTHORITATIVE,   # РЖД
    "aeroflot.ru":         TrustTier.AUTHORITATIVE,
    # City transport portals — authoritative for local route/stop data
    "voronezh.ru":         TrustTier.AUTHORITATIVE,   # Официальный сайт Воронежа
    "goroda-rossii.ru":    TrustTier.NEUTRAL,          # aggregator, not official
    "transportsb.ru":      TrustTier.AUTHORITATIVE,   # Воронежтранс
    "vmeste-rf.ru":        TrustTier.NEUTRAL,

    # ── TRUSTED ───────────────────────────────────────────────────────────────
    "wikipedia.org":       TrustTier.TRUSTED,
    "wikidata.org":        TrustTier.TRUSTED,
    "openstreetmap.org":   TrustTier.TRUSTED,
    "booking.com":         TrustTier.TRUSTED,
    "hotels.com":          TrustTier.TRUSTED,
    "tripadvisor.com":     TrustTier.TRUSTED,
    "tripadvisor.ru":      TrustTier.TRUSTED,
    "yandex.ru":           TrustTier.TRUSTED,
    "yandex.maps":         TrustTier.TRUSTED,
    "2gis.ru":             TrustTier.TRUSTED,
    "google.com":          TrustTier.TRUSTED,
    "aviasales.ru":        TrustTier.TRUSTED,

    # ── BLOCKED — Route / transport SEO aggregators ───────────────────────────
    # These generate invented specifics: fake bus numbers, non-existent stops,
    # made-up journey times. Root cause of "автобус 27А / площадь Горького" errors.
    "all-routes.ru":       TrustTier.BLOCKED,
    "all-routes.com":      TrustTier.BLOCKED,
    "mapbbcode.org":       TrustTier.BLOCKED,
    "kartagoroda.ru":      TrustTier.BLOCKED,

    # ── BLOCKED — Hotel SEO aggregators ──────────────────────────────────────
    # Use booking.com / hotels.com instead.
    "101hotels.com":       TrustTier.BLOCKED,

    # ── BLOCKED — Q&A spam ───────────────────────────────────────────────────
    "otvet.mail.ru":       TrustTier.BLOCKED,
    "travelask.ru":        TrustTier.BLOCKED,

    # ── BLOCKED — Generic travel SEO farms ───────────────────────────────────
    "tourister.ru":        TrustTier.BLOCKED,
    "turpravda.com":       TrustTier.BLOCKED,
    "votpusk.ru":          TrustTier.BLOCKED,
}

# Score assigned to each tier — used by hybrid_scorer for trust weighting
TIER_SCORES: dict[TrustTier, float] = {
    TrustTier.AUTHORITATIVE: 1.0,
    TrustTier.TRUSTED:       0.8,
    TrustTier.NEUTRAL:       0.5,
    TrustTier.DEGRADED:      0.2,
    TrustTier.BLOCKED:       0.0,
}


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CredibilitySignal:
    domain: str
    tier: TrustTier
    score: float        # 0.0 – 1.0 from TIER_SCORES
    blocked: bool


# ─── CORE ─────────────────────────────────────────────────────────────────────

class SourceCredibility:
    """
    Evaluates trustworthiness of web sources by domain.

    Position in pipeline:
        search.py  →  source_credibility.filter_results()  →  reranker  →  LLM

    Responsibility boundary:
        THIS module:   domain trustworthiness
        reranker:      semantic relevance
        safety_agent:  emergent content safety
        EPK:           policy / cost

    Does NOT:
        interpret content
        make routing decisions
        duplicate reranker logic
    """

    def evaluate(self, url: str) -> CredibilitySignal:
        """
        Return a CredibilitySignal for the given URL.
        Never raises — falls back to NEUTRAL on any parse error.
        """
        domain = _extract_domain(url)
        tier   = _DOMAIN_TRUST.get(domain, TrustTier.NEUTRAL)
        return CredibilitySignal(
            domain=domain,
            tier=tier,
            score=TIER_SCORES[tier],
            blocked=tier == TrustTier.BLOCKED,
        )

    def filter_results(
        self,
        results: list[dict],
        max_results: int = 5,
    ) -> list[dict]:
        """
        Filter and cap web search results by domain credibility.

        - Removes BLOCKED domains entirely.
        - Preserves ordering (reranker handles semantic re-ordering downstream).
        - Caps at max_results after filtering (fewer, better sources > more noise).

        Args:
            results:     list of dicts with at least a "link" key.
            max_results: hard cap on returned results.

        Returns:
            Filtered list, at most max_results long.
        """
        kept: list[dict] = []
        blocked_count = 0

        for r in results:
            signal = self.evaluate(r.get("link", ""))
            if signal.blocked:
                blocked_count += 1
                logger.debug(
                    "source_credibility: blocked domain",
                    extra={"domain": signal.domain, "tier": signal.tier},
                )
                continue
            kept.append(r)

        capped = kept[:max_results]
        removed = len(results) - len(capped)

        if removed > 0:
            logger.info(
                "source_credibility: filtered results",
                extra={
                    "original": len(results),
                    "blocked":  blocked_count,
                    "kept":     len(capped),
                },
            )

        return capped


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    """
    Parse URL and return bare domain without www. prefix.
    Returns empty string on parse failure.
    """
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


# ─── SINGLETON ────────────────────────────────────────────────────────────────

source_credibility = SourceCredibility()