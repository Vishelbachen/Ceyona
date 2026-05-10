# i18n/t.py
# Convenience re-export so any file can do:
#   from i18n.t import t, lang_instruction, ow_lang, normalize_lang, SUPPORTED_LANGS
from i18n.strings import t, lang_instruction, ow_lang, normalize_lang, is_supported, SUPPORTED_LANGS

__all__ = ["t", "lang_instruction", "ow_lang", "normalize_lang", "is_supported", "SUPPORTED_LANGS"]
