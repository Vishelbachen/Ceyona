# i18n/t.py
# Convenience re-export so any file can do:
#   from i18n.t import t, lang_instruction, ow_lang, normalize_lang, SUPPORTED_LANGS
from i18n.strings import SUPPORTED_LANGS, is_supported, lang_instruction, normalize_lang, ow_lang, t

__all__ = ["t", "lang_instruction", "ow_lang", "normalize_lang", "is_supported", "SUPPORTED_LANGS"]
