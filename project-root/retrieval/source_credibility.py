Оценка доверия к источникам поиска.

Роль:
  Единственная ответственность — оценить trustworthiness источника
  ДО того как его контент попадёт в контекст LLM.

  Это НЕ:
    - semantic reranking     (→ cross_encoder.py)
    - policy enforcement     (→ EPK)
    - safety filtering       (→ safety_agent.py)
    - routing / arbitration  (→ consensus_engine.py)

  Это ТОЛЬКО:
    - оценка доверия к домену и типу источника
    - фильтрация ненадёжных источников из retrieval pipeline
    - взвешивание результатов по trustworthiness

Используется:
  - retrieval/retrieval_engine.py  → filter_web_results()
  - external/search.py             → _filter_results() делегирует сюда
                                     (junk-list из search.py мигрирован сюда)

Интеграционная точка:
  results = retrieve()
  results = source_credibility.filter(results)   ← здесь
  # далее → LLM
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ─── TRUST TIERS ──────────────────────────────────────────────────────────────
# Числовые значения используются как weights при scoring.
# Не менять порядок без обновления _DOMAIN_TRUST и filter().

class TrustTier(IntEnum):
    BLOCKED    = 0   # никогда не показывать LLM
    VERY_LOW   = 1   # SEO-агрегаторы, форумы без верификации
    LOW        = 2   # общие агрегаторы с частично верифицированным контентом
    MEDIUM     = 3   # нейтральные источники, Wikipedia, новостные агрегаторы
    HIGH       = 4   # специализированные сервисы, официальные сайты
    AUTHORITATIVE = 5  # правительственные, академические, верифицированные API


# ─── DOMAIN TRUST REGISTRY ────────────────────────────────────────────────────
# Явные записи перекрывают автоматическую классификацию по паттернам.
# Структура: домен (без www.) → TrustTier
#
# Принципы включения:
#   BLOCKED:       домены, систематически генерирующие галлюцинации в контексте
#   VERY_LOW:      SEO-фермы, агрегаторы без первичного контента
#   HIGH:          сервисы с верифицированными данными реального времени
#   AUTHORITATIVE: официальные источники с подтверждённой точностью

_DOMAIN_TRUST: dict[str, TrustTier] = {

    # ── BLOCKED: систематические источники галлюцинаций ───────────────────────
    "all-routes.ru":       TrustTier.BLOCKED,
    "all-routes.com":      TrustTier.BLOCKED,
    "kartagoroda.ru":      TrustTier.BLOCKED,
    "mapbbcode.org":       TrustTier.BLOCKED,

    # ── VERY_LOW: SEO-агрегаторы без первичного контента ─────────────────────
    "101hotels.com":       TrustTier.VERY_LOW,
    "otvet.mail.ru":       TrustTier.VERY_LOW,
    "travelask.ru":        TrustTier.VERY_LOW,
    "turpravda.com":       TrustTier.VERY_LOW,
    "votpusk.ru":          TrustTier.VERY_LOW,
    "tourister.ru":        TrustTier.VERY_LOW,
    "irecommend.ru":       TrustTier.VERY_LOW,
    "otzovik.com":         TrustTier.VERY_LOW,
    "yell.ru":             TrustTier.VERY_LOW,

    # ── LOW: общие агрегаторы ─────────────────────────────────────────────────
    "tripadvisor.com":     TrustTier.LOW,
    "tripadvisor.ru":      TrustTier.LOW,
    "flamp.ru":            TrustTier.LOW,
    "zoon.ru":             TrustTier.LOW,

    # ── MEDIUM: нейтральные источники ─────────────────────────────────────────
    "wikipedia.org":       TrustTier.MEDIUM,
    "ru.wikipedia.org":    TrustTier.MEDIUM,
    "en.wikipedia.org":    TrustTier.MEDIUM,
    "wikitravel.org":      TrustTier.MEDIUM,
    "ria.ru":              TrustTier.MEDIUM,
    "tass.ru":             TrustTier.MEDIUM,
    "rbc.ru":              TrustTier.MEDIUM,
    "kommersant.ru":       TrustTier.MEDIUM,

    # ── HIGH: верифицированные сервисы с реальными данными ───────────────────
    "yandex.ru":           TrustTier.HIGH,
    "maps.yandex.ru":      TrustTier.HIGH,
    "2gis.ru":             TrustTier.HIGH,
    "2gis.com":            TrustTier.HIGH,
    "booking.com":         TrustTier.HIGH,
    "hotels.com":          TrustTier.HIGH,
    "ostrovok.ru":         TrustTier.HIGH,
    "tutu.ru":             TrustTier.HIGH,   # реальные данные транспорта
    "rasp.yandex.ru":      TrustTier.HIGH,
    "maps.google.com":     TrustTier.HIGH,
    "google.com":          TrustTier.HIGH,

    # ── AUTHORITATIVE: официальные источники ──────────────────────────────────
    "openweathermap.org":  TrustTier.AUTHORITATIVE,
    "mapbox.com":          TrustTier.AUTHORITATIVE,
    "gks.ru":              TrustTier.AUTHORITATIVE,   # Росстат
    "government.ru":       TrustTier.AUTHORITATIVE,
}


# ─── PATTERN-BASED CLASSIFICATION ────────────────────────────────────────────
# Применяется когда домен не в _DOMAIN_TRUST.
# Паттерны проверяются по порядку, первое совпадение побеждает.

@dataclass(frozen=True)
class _DomainPattern:
    pattern: re.Pattern
    tier: TrustTier
    reason: str

_DOMAIN_PATTERNS: list[_DomainPattern] = [
    # Правительственные домены
    _DomainPattern(re.compile(r"\.gov\.(ru|ua|by|kz|uz)$"), TrustTier.AUTHORITATIVE, "government"),
    _DomainPattern(re.compile(r"\.gov$"),                    TrustTier.AUTHORITATIVE, "government"),
    _DomainPattern(re.compile(r"\.edu$"),                    TrustTier.HIGH,          "academic"),
    _DomainPattern(re.compile(r"\.ac\.\w{2}$"),              TrustTier.HIGH,          "academic"),

    # Официальные транспортные ресурсы
    _DomainPattern(re.compile(r"(transport|metro|bus|avto|railway|rzd)\.\w"),
                   TrustTier.HIGH, "transport_official"),

    # SEO-паттерны — домены с типичными SEO-суффиксами
    _DomainPattern(re.compile(r"(top|best|rating|rank|otzyv|review)"),
                   TrustTier.VERY_LOW, "seo_pattern"),
    _DomainPattern(re.compile(r"\d{2,}(hotels?|tours?|travel)"),
                   TrustTier.VERY_LOW, "seo_aggregator"),
]


# ─── SCORING ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CredibilityScore:
    domain: str
    tier: TrustTier
    score: float          # 0.0 – 1.0, производное от tier
    reason: str           # для логирования
    is_blocked: bool      # True → никогда не попадёт в контекст LLM


def _extract_domain(url: str) -> str:
    """Извлечь домен без www. Пустая строка при ошибке."""
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def _tier_to_score(tier: TrustTier) -> float:
    """Конвертация TrustTier в float weight для downstream использования."""
    return tier.value / TrustTier.AUTHORITATIVE.value


def evaluate(url: str) -> CredibilityScore:
    """
    Оценить trustworthiness источника по URL.
    Детерминированная. Без I/O. Без side effects.

    Приоритет:
      1. Явная запись в _DOMAIN_TRUST
      2. Паттерн из _DOMAIN_PATTERNS
      3. DEFAULT: MEDIUM (неизвестный источник — не блокировать, но и не доверять)
    """
    domain = _extract_domain(url)

    # 1. Явная запись
    if domain in _DOMAIN_TRUST:
        tier = _DOMAIN_TRUST[domain]
        return CredibilityScore(
            domain=domain,
            tier=tier,
            score=_tier_to_score(tier),
            reason="explicit_registry",
            is_blocked=(tier == TrustTier.BLOCKED),
        )

    # 2. Паттерн
    for dp in _DOMAIN_PATTERNS:
        if dp.pattern.search(domain):
            return CredibilityScore(
                domain=domain,
                tier=dp.tier,
                score=_tier_to_score(dp.tier),
                reason=f"pattern:{dp.reason}",
                is_blocked=(dp.tier == TrustTier.BLOCKED),
            )

    # 3. Default
    return CredibilityScore(
        domain=domain,
        tier=TrustTier.MEDIUM,
        score=_tier_to_score(TrustTier.MEDIUM),
        reason="unknown_domain",
        is_blocked=False,
    )


# ─── FILTER API ───────────────────────────────────────────────────────────────
# Используется в retrieval_engine и search.py

# Минимальный tier для попадания в контекст LLM.
# VERY_LOW и ниже → отфильтровываются.
_MIN_TIER = TrustTier.LOW


def filter_results(
    results: list[dict],
    min_tier: TrustTier = _MIN_TIER,
    max_results: int = 5,
) -> list[dict]:
    """
    Отфильтровать список результатов поиска по credibility.
    Входной формат: [{"title": str, "link": str, "snippet": str}, ...]
    Возвращает отфильтрованный и ограниченный список.

    Порядок сохраняется (изначальный ranking SerpAPI).
    Credibility не перестраивает порядок — это задача reranker'а.
    """
    passed: list[dict] = []
    blocked_count = 0
    low_trust_count = 0

    for r in results:
        url = r.get("link", "")
        cred = evaluate(url)

        if cred.is_blocked:
            blocked_count += 1
            logger.debug(
                "source_credibility: BLOCKED",
                extra={"domain": cred.domain, "url": url[:80]},
            )
            continue

        if cred.tier < min_tier:
            low_trust_count += 1
            logger.debug(
                "source_credibility: below min_tier",
                extra={
                    "domain": cred.domain,
                    "tier":   cred.tier.name,
                    "min":    min_tier.name,
                },
            )
            continue

        # Аннотировать результат credibility-метаданными для downstream
        passed.append({
            **r,
            "_credibility": {
                "domain": cred.domain,
                "tier":   cred.tier.name,
                "score":  round(cred.score, 3),
                "reason": cred.reason,
            },
        })

    kept = passed[:max_results]

    if blocked_count or low_trust_count or len(results) > len(kept):
        logger.info(
            "source_credibility: filter complete",
            extra={
                "input":       len(results),
                "blocked":     blocked_count,
                "low_trust":   low_trust_count,
                "kept":        len(kept),
            },
        )

    return kept


def score_documents(
    documents: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """
    Применить credibility-weighting к результатам pgvector (content, score).
    Используется в retrieval_engine после similarity_search.

    Документы из памяти не имеют URL — credibility не применяется,
    возвращаются as-is. Этот метод зарезервирован для будущих случаев
    когда memory records будут содержать source metadata.
    """
    # Memory records сейчас не содержат source URL — пропускаем без изменений.
    # Когда MemoryRecord получит поле source_url, здесь добавится weighting.
    return documents


# ─── SINGLETON ────────────────────────────────────────────────────────────────
# Stateless — синглтон только для единообразия с остальными сервисами.

class SourceCredibility:
    """
    Публичный фасад для использования через dependency injection.
    Все методы делегируют module-level функциям.
    Stateless — не хранит состояния между вызовами.
    """

    def evaluate(self, url: str) -> CredibilityScore:
        return evaluate(url)

    def filter_results(
        self,
        results: list[dict],
        min_tier: TrustTier = _MIN_TIER,
        max_results: int = 5,
    ) -> list[dict]:
        return filter_results(results, min_tier=min_tier, max_results=max_results)

    def score_documents(
        self,
        documents: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        return score_documents(documents)


source_credibility = SourceCredibility()