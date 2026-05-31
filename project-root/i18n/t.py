# i18n/t.py
# Convenience re-export so any file can do:
#   from i18n.t import t, lang_instruction, ow_lang, normalize_lang, SUPPORTED_LANGS
#
# Also exposes get_system_message / format_balance_message as pure i18n helpers.
# These functions MUST NOT live in cognition/ — transport layer is allowed to
# import from i18n but NOT from cognition (architecture.md §19).
# This module is the canonical place for lightweight i18n accessors.
from i18n.strings import (
    SUPPORTED_LANGS,
    is_supported,
    lang_instruction,
    normalize_lang,
    ow_lang,
    t,
)


def get_system_message(key: str, lang: str) -> str:
    """Return a localised system message string. Pure i18n helper — no logic."""
    return t(key, lang) or "⚠️ An error occurred."


def format_balance_message(balance: float, lang: str) -> str:
    """Return a localised balance display string."""
    return t("balance_display", lang, amount=f"{balance:.2f}")


__all__ = [
    "t",
    "lang_instruction",
    "ow_lang",
    "normalize_lang",
    "is_supported",
    "SUPPORTED_LANGS",
    "get_system_message",
    "format_balance_message",
]