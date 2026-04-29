import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)

# ─── TELEGRAM LIMITS ─────────────────────────────────────────────────────────

_TELEGRAM_MAX_CHARS = 4096

# ─── SUPPORTED LANGUAGES (hardcoded — covers ~95% of Telegram users) ─────────

_MESSAGES: dict[str, dict[str, str]] = {
    "insufficient_balance": {
        "en": "⚠️ *Insufficient balance.*\nPlease top up to continue.",
        "ru": "⚠️ *Недостаточно средств.*\nПополните баланс, чтобы продолжить.",
        "de": "⚠️ *Unzureichendes Guthaben.*\nBitte aufladen, um fortzufahren.",
        "fr": "⚠️ *Solde insuffisant.*\nVeuillez recharger pour continuer.",
        "es": "⚠️ *Saldo insuficiente.*\nPor favor recarga para continuar.",
        "pt": "⚠️ *Saldo insuficiente.*\nPor favor recarregue para continuar.",
        "it": "⚠️ *Saldo insufficiente.*\nRicarica per continuare.",
        "tr": "⚠️ *Yetersiz bakiye.*\nDevam etmek için lütfen bakiye yükleyin.",
        "ar": "⚠️ *رصيد غير كافٍ.*\nيرجى إعادة الشحن للمتابعة.",
        "zh": "⚠️ *余额不足。*\n请充值以继续。",
        "ja": "⚠️ *残高不足です。*\n続けるにはチャージしてください。",
        "ko": "⚠️ *잔액이 부족합니다.*\n계속하려면 충전해 주세요.",
        "pl": "⚠️ *Niewystarczające środki.*\nProszę doładować, aby kontynuować.",
        "uk": "⚠️ *Недостатньо коштів.*\nПоповніть баланс, щоб продовжити.",
        "fa": "⚠️ *موجودی کافی نیست.*\nلطفاً برای ادامه شارژ کنید.",
    },
    "no_response": {
        "en": "⚠️ No response received. Please try again.",
        "ru": "⚠️ Не удалось получить ответ. Попробуйте ещё раз.",
        "de": "⚠️ Keine Antwort erhalten. Bitte versuche es erneut.",
        "fr": "⚠️ Aucune réponse reçue. Veuillez réessayer.",
        "es": "⚠️ No se recibió respuesta. Por favor intenta de nuevo.",
        "pt": "⚠️ Nenhuma resposta recebida. Por favor tente novamente.",
        "it": "⚠️ Nessuna risposta ricevuta. Per favore riprova.",
        "tr": "⚠️ Yanıt alınamadı. Lütfen tekrar deneyin.",
        "ar": "⚠️ لم يتم تلقي أي رد. يرجى المحاولة مرة أخرى.",
        "zh": "⚠️ 未收到回复。请重试。",
        "ja": "⚠️ 返答がありませんでした。もう一度お試しください。",
        "ko": "⚠️ 응답을 받지 못했습니다. 다시 시도해 주세요.",
        "pl": "⚠️ Nie otrzymano odpowiedzi. Proszę spróbować ponownie.",
        "uk": "⚠️ Не вдалося отримати відповідь. Спробуйте ще раз.",
        "fa": "⚠️ پاسخی دریافت نشد. لطفاً دوباره امتحان کنید.",
    },
    "default_deny": {
        "en": "⚠️ Request cannot be processed.",
        "ru": "⚠️ Запрос не может быть выполнен.",
        "de": "⚠️ Anfrage kann nicht verarbeitet werden.",
        "fr": "⚠️ La demande ne peut pas être traitée.",
        "es": "⚠️ La solicitud no puede procesarse.",
        "pt": "⚠️ O pedido não pode ser processado.",
        "it": "⚠️ La richiesta non può essere elaborata.",
        "tr": "⚠️ İstek işlenemiyor.",
        "ar": "⚠️ لا يمكن معالجة الطلب.",
        "zh": "⚠️ 请求无法处理。",
        "ja": "⚠️ リクエストを処理できません。",
        "ko": "⚠️ 요청을 처리할 수 없습니다.",
        "pl": "⚠️ Żądanie nie może być przetworzone.",
        "uk": "⚠️ Запит не може бути виконаний.",
        "fa": "⚠️ درخواست قابل پردازش نیست.",
    },
    "truncation_suffix": {
        "en": "\n\n_...response truncated_",
        "ru": "\n\n_...ответ сокращён_",
        "de": "\n\n_...Antwort gekürzt_",
        "fr": "\n\n_...réponse tronquée_",
        "es": "\n\n_...respuesta truncada_",
        "pt": "\n\n_...resposta truncada_",
        "it": "\n\n_...risposta troncata_",
        "tr": "\n\n_...yanıt kısaltıldı_",
        "ar": "\n\n_...تم اقتصاص الرد_",
        "zh": "\n\n_...回复已截断_",
        "ja": "\n\n_...返答が省略されました_",
        "ko": "\n\n_...응답이 잘렸습니다_",
        "pl": "\n\n_...odpowiedź skrócona_",
        "uk": "\n\n_...відповідь скорочено_",
        "fa": "\n\n_...پاسخ کوتاه شد_",
    },
    "balance_display": {
        "en": "💰 Balance: $1.00",
        "ru": "💰 Баланс: $1.00",
        "de": "💰 Guthaben: $1.00",
        "fr": "💰 Solde : $1.00",
        "es": "💰 Saldo: $1.00",
        "pt": "💰 Saldo: $1.00",
        "it": "💰 Saldo: $1.00",
        "tr": "💰 Bakiye: $1.00",
        "ar": "💰 الرصيد: $1.00",
        "zh": "💰 余额：$1.00",
        "ja": "💰 残高：$1.00",
        "ko": "💰 잔액: $1.00",
        "pl": "💰 Saldo: $1.00",
        "uk": "💰 Баланс: $1.00",
        "fa": "💰 موجودی: $1.00",
    },
    "help_display": {
        "en": "ℹ️ Help",
        "ru": "ℹ️ Помощь",
        "de": "ℹ️ Hilfe",
        "fr": "ℹ️ Aide",
        "es": "ℹ️ Ayuda",
        "pt": "ℹ️ Ajuda",
        "it": "ℹ️ Aiuto",
        "tr": "ℹ️ Yardım",
        "ar": "ℹ️ مساعدة",
        "zh": "ℹ️ 帮助",
        "ja": "ℹ️ ヘルプ",
        "ko": "ℹ️ 도움말",
        "pl": "ℹ️ Pomoc",
        "uk": "ℹ️ Допомога",
        "fa": "ℹ️ راهنما",
    },
    "cancelled": {
        "en": "✅ Cancelled",
        "ru": "✅ Отменено",
        "de": "✅ Abgebrochen",
        "fr": "✅ Annulé",
        "es": "✅ Cancelado",
        "pt": "✅ Cancelado",
        "it": "✅ Annullato",
        "tr": "✅ İptal edildi",
        "ar": "✅ تم الإلغاء",
        "zh": "✅ 已取消",
        "ja": "✅ キャンセルしました",
        "ko": "✅ 취소됨",
        "pl": "✅ Anulowano",
        "uk": "✅ Скасовано",
        "fa": "✅ لغو شد",
    },
    "empty_message": {
        "en": "", "ru": "", "de": "", "fr": "", "es": "", "pt": "",
        "it": "", "tr": "", "ar": "", "zh": "", "ja": "", "ko": "",
        "pl": "", "uk": "", "fa": "",
    },
    "no_user_id": {
        "en": "", "ru": "", "de": "", "fr": "", "es": "", "pt": "",
        "it": "", "tr": "", "ar": "", "zh": "", "ja": "", "ko": "",
        "pl": "", "uk": "", "fa": "",
    },
}

_SILENT_KEYS = {"empty_message", "no_user_id"}


def get_system_message(key: str, lang: str) -> str:
    """
    Return localised system message.
    Falls back to English if lang not in registry.
    """
    bucket = _MESSAGES.get(key, {})
    return bucket.get(lang) or bucket.get("en", "")


# ─── I/O CONTRACTS ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: "Intent | None"   # ← было Intent, стало Optional
    tier: Tier
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    truncated: bool = False


# ─── INTERNAL HELPERS ────────────────────────────────────────────────────────

def _truncate(text: str, lang: str) -> tuple[str, bool]:
    suffix = get_system_message("truncation_suffix", lang)
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


# ─── MAIN SYNTHESIZER ────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into final user-facing text.
    Pure function. No I/O. No state.
    """
    if inp.denied:
        if inp.deny_reason in _SILENT_KEYS:
            return SynthesisResult(text="")
        key = inp.deny_reason if inp.deny_reason in _MESSAGES else "default_deny"
        return SynthesisResult(text=get_system_message(key, inp.lang))

    if not inp.raw_text or not inp.raw_text.strip():
        return SynthesisResult(text=get_system_message("no_response", inp.lang))

    final, truncated = _truncate(inp.raw_text.strip(), inp.lang)
    return SynthesisResult(text=final, truncated=truncated)