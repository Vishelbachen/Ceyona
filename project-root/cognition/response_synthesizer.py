"""
cognition/response_synthesizer.py

ROLE: Final output authority. Assembles, formats, applies correction,
      and finalises the user-facing response.

INVARIANTS:
  - FINAL OUTPUT AUTHORITY — nothing downstream modifies text
  - Pure function: synthesize() has NO I/O, NO state
  - Calls meta/correction.py at step 4 (inline, non-authoritative)
  - NEVER returns an empty string to the caller — always a meaningful message
  - All user-facing strings are localised via get_system_message()
  - Language is always respected: system messages match user's lang
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)

# ─── TELEGRAM LIMITS ──────────────────────────────────────────────────────────

_TELEGRAM_MAX_CHARS = 4096

# ─── SUPPORTED LANGUAGES ──────────────────────────────────────────────────────
# Covers ~98% of Telegram's user base.
# Add new langs here — system messages below are the only touch point.

_SUPPORTED_LANGS = {
    "en", "ru", "de", "fr", "es", "pt", "it", "tr", "ar",
    "zh", "ja", "ko", "pl", "uk", "fa", "nl", "sv", "no",
    "da", "fi", "cs", "sk", "ro", "hu", "bg", "hr", "sr",
    "he", "vi", "th", "id", "ms", "hi", "bn", "ur",
    "az", "kk", "uz",
}

# ─── SYSTEM MESSAGES ──────────────────────────────────────────────────────────
# Keys map to deny_reason or explicit UI states.
# Rule: every key MUST have "en" as the guaranteed fallback.

_MESSAGES: dict[str, dict[str, str]] = {

    # ── balance ───────────────────────────────────────────────────────────────
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
        "ko": "⚠️ *잔액이 부족합니다.*\n계속하려면 충전해 주세요。",
        "pl": "⚠️ *Niewystarczające środki.*\nProszę doładować, aby kontynuować.",
        "uk": "⚠️ *Недостатньо коштів.*\nПоповніть баланс, щоб продовжити.",
        "fa": "⚠️ *موجودی کافی نیست.*\nلطفاً برای ادامه شارژ کنید.",
        "nl": "⚠️ *Onvoldoende saldo.*\nGelieve op te laden om door te gaan.",
        "sv": "⚠️ *Otillräckligt saldo.*\nVänligen fyll på för att fortsätta.",
        "no": "⚠️ *Utilstrekkelig saldo.*\nVennligst fyll på for å fortsette.",
        "da": "⚠️ *Utilstrækkelig saldo.*\nVenligst optank for at fortsætte.",
        "fi": "⚠️ *Saldo ei riitä.*\nLisää saldoa jatkaaksesi.",
        "he": "⚠️ *יתרה לא מספיקה.*\nאנא טען כדי להמשיך.",
        "hi": "⚠️ *अपर्याप्त शेष।*\nजारी रखने के लिए कृपया राशि जोड़ें।",
        "id": "⚠️ *Saldo tidak mencukupi.*\nSilakan isi ulang untuk melanjutkan.",
        "az": "⚠️ *Balans kifayət deyil.*\nDavam etmək üçün zəhmət olmasa yükləyin.",
        "kk": "⚠️ *Баланс жеткіліксіз.*\nЖалғастыру үшін балансты толтырыңыз.",
        "uz": "⚠️ *Balans yetarli emas.*\nDavom etish uchun iltimos to'ldiring.",
    },

    # ── no LLM response received ───────────────────────────────────────────────
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
        "nl": "⚠️ Geen antwoord ontvangen. Probeer het opnieuw.",
        "sv": "⚠️ Inget svar mottaget. Försök igen.",
        "no": "⚠️ Ingen respons mottatt. Vennligst prøv igjen.",
        "da": "⚠️ Intet svar modtaget. Prøv venligst igen.",
        "fi": "⚠️ Vastausta ei saatu. Yritä uudelleen.",
        "he": "⚠️ לא התקבלה תגובה. אנא נסה שנית.",
        "hi": "⚠️ कोई प्रतिक्रिया नहीं मिली। कृपया पुनः प्रयास करें।",
        "id": "⚠️ Tidak ada respons. Silakan coba lagi.",
        "az": "⚠️ Cavab alınmadı. Zəhmət olmasa yenidən cəhd edin.",
        "kk": "⚠️ Жауап алынбады. Қайталап көріңіз.",
        "uz": "⚠️ Javob olinmadi. Iltimos qayta urinib ko'ring.",
    },

    # ── generic deny ──────────────────────────────────────────────────────────
    "default_deny": {
        "en": "⚠️ I couldn't process that request. Please rephrase or try again.",
        "ru": "⚠️ Не удалось обработать запрос. Попробуйте переформулировать.",
        "de": "⚠️ Die Anfrage konnte nicht verarbeitet werden. Bitte umformulieren.",
        "fr": "⚠️ Impossible de traiter la demande. Veuillez reformuler.",
        "es": "⚠️ No pude procesar esa solicitud. Por favor reformula.",
        "pt": "⚠️ Não consegui processar esse pedido. Por favor reformule.",
        "it": "⚠️ Non riesco a elaborare la richiesta. Per favore riformula.",
        "tr": "⚠️ İstek işlenemedi. Lütfen yeniden ifade edin.",
        "ar": "⚠️ تعذّر معالجة الطلب. حاول إعادة الصياغة.",
        "zh": "⚠️ 无法处理该请求。请换种说法再试。",
        "ja": "⚠️ リクエストを処理できませんでした。言い方を変えてお試しください。",
        "ko": "⚠️ 요청을 처리할 수 없었습니다. 다르게 표현해 보세요.",
        "pl": "⚠️ Nie mogłem przetworzyć tego żądania. Proszę przeformułować.",
        "uk": "⚠️ Не вдалося обробити запит. Спробуйте переформулювати.",
        "fa": "⚠️ این درخواست قابل پردازش نیست. لطفاً دوباره بیان کنید.",
        "nl": "⚠️ Kon dat verzoek niet verwerken. Probeer het anders te formuleren.",
        "sv": "⚠️ Kunde inte behandla den begäran. Försök omformulera.",
        "no": "⚠️ Kunne ikke behandle den forespørselen. Prøv å omformulere.",
        "da": "⚠️ Kunne ikke behandle den forespørgsel. Prøv at omformulere.",
        "fi": "⚠️ Pyyntöä ei voitu käsitellä. Yritä muotoilla uudelleen.",
        "he": "⚠️ לא ניתן לעבד את הבקשה. נסה לנסח מחדש.",
        "hi": "⚠️ इस अनुरोध को प्रोसेस नहीं किया जा सका। कृपया दोबारा लिखें।",
        "id": "⚠️ Tidak dapat memproses permintaan itu. Coba ungkapkan kembali.",
        "az": "⚠️ Bu sorğu işlənə bilmədi. Zəhmət olmasa yenidən ifadə edin.",
        "kk": "⚠️ Сұранысты өңдеу мүмкін болмады. Қайта тұжырымдап көріңіз.",
        "uz": "⚠️ Bu so'rovni qayta ishlash imkoni bo'lmadi. Iltimos qayta ifodalang.",
    },

    # ── safety block ──────────────────────────────────────────────────────────
    "safety_block": {
        "en": "🚫 That request goes against my guidelines. Please try something else.",
        "ru": "🚫 Этот запрос нарушает мои правила. Попробуйте другое.",
        "de": "🚫 Diese Anfrage verstößt gegen meine Richtlinien. Bitte anderes versuchen.",
        "fr": "🚫 Cette demande enfreint mes directives. Essayez autre chose.",
        "es": "🚫 Esa solicitud va contra mis pautas. Por favor intenta otra cosa.",
        "pt": "🚫 Esse pedido vai contra as minhas diretrizes. Por favor tente outra coisa.",
        "it": "🚫 Questa richiesta va contro le mie linee guida. Prova qualcos'altro.",
        "tr": "🚫 Bu istek kurallarıma aykırı. Lütfen başka bir şey deneyin.",
        "ar": "🚫 هذا الطلب يخالف قواعدي. الرجاء تجربة شيء آخر.",
        "zh": "🚫 该请求违反了我的准则。请尝试其他内容。",
        "ja": "🚫 そのリクエストはガイドラインに違反しています。他のことをお試しください。",
        "ko": "🚫 해당 요청은 내 지침에 위배됩니다. 다른 것을 시도해 보세요.",
        "pl": "🚫 To żądanie narusza moje wytyczne. Proszę spróbować czegoś innego.",
        "uk": "🚫 Цей запит порушує мої правила. Спробуйте щось інше.",
        "fa": "🚫 این درخواست با دستورالعمل‌های من مغایرت دارد. چیز دیگری امتحان کنید.",
        "nl": "🚫 Dat verzoek gaat in tegen mijn richtlijnen. Probeer iets anders.",
        "sv": "🚫 Den begäran strider mot mina riktlinjer. Försök med något annat.",
        "no": "🚫 Den forespørselen er mot retningslinjene mine. Prøv noe annet.",
        "da": "🚫 Den forespørgsel er imod mine retningslinjer. Prøv noget andet.",
        "fi": "🚫 Pyyntö rikkoo ohjeistustani. Kokeile jotain muuta.",
        "he": "🚫 הבקשה הזו מפרה את ההנחיות שלי. אנא נסה משהו אחר.",
        "hi": "🚫 वह अनुरोध मेरे दिशानिर्देशों के खिलाफ है। कृपया कुछ और आज़माएं।",
        "id": "🚫 Permintaan itu bertentangan dengan pedoman saya. Silakan coba yang lain.",
        "az": "🚫 Bu sorğu qaydalarıma ziddir. Zəhmət olmasa başqa şey sınayın.",
        "kk": "🚫 Бұл сұраныс ережелерімді бұзады. Басқа нәрсе сынап көріңіз.",
        "uz": "🚫 Bu so'rov qoidalarimga zid. Iltimos boshqa narsa sinab ko'ring.",
    },

    # ── rate limiting ─────────────────────────────────────────────────────────
    "rate_limited": {
        "en": "⏳ You're sending messages too fast. Please wait a moment.",
        "ru": "⏳ Вы отправляете сообщения слишком быстро. Подождите немного.",
        "de": "⏳ Du sendest Nachrichten zu schnell. Bitte kurz warten.",
        "fr": "⏳ Vous envoyez des messages trop vite. Patientez un instant.",
        "es": "⏳ Estás enviando mensajes demasiado rápido. Espera un momento.",
        "pt": "⏳ Está enviando mensagens rápido demais. Por favor aguarde.",
        "it": "⏳ Stai inviando messaggi troppo velocemente. Aspetta un momento.",
        "tr": "⏳ Çok hızlı mesaj gönderiyorsunuz. Lütfen biraz bekleyin.",
        "ar": "⏳ أنت ترسل رسائل بسرعة كبيرة. الرجاء الانتظار لحظة.",
        "zh": "⏳ 您发送消息太快了。请稍等片刻。",
        "ja": "⏳ メッセージの送信が速すぎます。少々お待ちください。",
        "ko": "⏳ 메시지를 너무 빨리 보내고 있습니다. 잠시 기다려 주세요.",
        "pl": "⏳ Wysyłasz wiadomości zbyt szybko. Poczekaj chwilę.",
        "uk": "⏳ Ви надсилаєте повідомлення занадто швидко. Зачекайте хвилину.",
        "fa": "⏳ پیام‌ها را خیلی سریع ارسال می‌کنید. لطفاً کمی صبر کنید.",
        "nl": "⏳ U stuurt berichten te snel. Even wachten alstublieft.",
        "sv": "⏳ Du skickar meddelanden för snabbt. Vänta lite.",
        "no": "⏳ Du sender meldinger for raskt. Vent litt.",
        "da": "⏳ Du sender beskeder for hurtigt. Vent venligst lidt.",
        "fi": "⏳ Lähetät viestejä liian nopeasti. Odota hetki.",
        "he": "⏳ אתה שולח הודעות מהר מדי. אנא המתן רגע.",
        "hi": "⏳ आप बहुत तेज़ी से संदेश भेज रहे हैं। कृपया थोड़ा रुकें।",
        "id": "⏳ Anda mengirim pesan terlalu cepat. Harap tunggu sebentar.",
        "az": "⏳ Siz mesajları çox sürətli göndərirsiniz. Zəhmət olmasa bir az gözləyin.",
        "kk": "⏳ Сіз хабарларды тым жылдам жіберіп жатырсыз. Біраз күте тұрыңыз.",
        "uz": "⏳ Xabarlarni juda tez yuboryapsiz. Iltimos bir oz kuting.",
    },

    # ── truncation suffix (appended when response is cut) ────────────────────
    "truncation_suffix": {
        "en": "\n\n_…response truncated_",
        "ru": "\n\n_…ответ сокращён_",
        "de": "\n\n_…Antwort gekürzt_",
        "fr": "\n\n_…réponse tronquée_",
        "es": "\n\n_…respuesta truncada_",
        "pt": "\n\n_…resposta truncada_",
        "it": "\n\n_…risposta troncata_",
        "tr": "\n\n_…yanıt kısaltıldı_",
        "ar": "\n\n_…تم اقتصاص الرد_",
        "zh": "\n\n_…回复已截断_",
        "ja": "\n\n_…返答が省略されました_",
        "ko": "\n\n_…응답이 잘렸습니다_",
        "pl": "\n\n_…odpowiedź skrócona_",
        "uk": "\n\n_…відповідь скорочено_",
        "fa": "\n\n_…پاسخ کوتاه شد_",
        "nl": "\n\n_…antwoord afgekapt_",
        "sv": "\n\n_…svar avkortat_",
        "no": "\n\n_…svar avkortet_",
        "da": "\n\n_…svar afkortet_",
        "fi": "\n\n_…vastaus katkaistu_",
        "he": "\n\n_…התגובה קוצרה_",
        "hi": "\n\n_…प्रतिक्रिया काटी गई_",
        "id": "\n\n_…respons dipotong_",
        "az": "\n\n_…cavab qısaldıldı_",
        "kk": "\n\n_…жауап қысқартылды_",
        "uz": "\n\n_…javob qisqartirildi_",
    },

    # ── help text ─────────────────────────────────────────────────────────────
    "help_display": {
        "en": (
            "ℹ️ *Help*\n\n"
            "I'm your AI assistant. You can:\n"
            "• Ask me anything\n"
            "• Request code, analysis, or creative writing\n"
            "• Ask for weather or web searches\n"
            "• Check your balance with /balance\n\n"
            "I reply in your language automatically."
        ),
        "ru": (
            "ℹ️ *Помощь*\n\n"
            "Я ваш ИИ-ассистент. Вы можете:\n"
            "• Задать любой вопрос\n"
            "• Попросить код, анализ или текст\n"
            "• Узнать погоду или сделать поиск\n"
            "• Проверить баланс через /balance\n\n"
            "Я отвечаю на вашем языке автоматически."
        ),
        "de": (
            "ℹ️ *Hilfe*\n\n"
            "Ich bin dein KI-Assistent. Du kannst:\n"
            "• Alles fragen\n"
            "• Code, Analysen oder kreative Texte anfordern\n"
            "• Wetter oder Websuche anfragen\n"
            "• Mit /balance dein Guthaben prüfen\n\n"
            "Ich antworte automatisch in deiner Sprache."
        ),
        "fr": (
            "ℹ️ *Aide*\n\n"
            "Je suis votre assistant IA. Vous pouvez :\n"
            "• Poser n'importe quelle question\n"
            "• Demander du code, une analyse ou un texte créatif\n"
            "• Demander la météo ou une recherche web\n"
            "• Vérifier votre solde avec /balance\n\n"
            "Je réponds automatiquement dans votre langue."
        ),
        "es": (
            "ℹ️ *Ayuda*\n\n"
            "Soy tu asistente de IA. Puedes:\n"
            "• Preguntar lo que quieras\n"
            "• Pedir código, análisis o escritura creativa\n"
            "• Consultar el clima o buscar en la web\n"
            "• Ver tu saldo con /balance\n\n"
            "Respondo automáticamente en tu idioma."
        ),
        "ar": (
            "ℹ️ *مساعدة*\n\n"
            "أنا مساعدك الذكي. يمكنك:\n"
            "• السؤال عن أي شيء\n"
            "• طلب كود أو تحليل أو كتابة إبداعية\n"
            "• الاستفسار عن الطقس أو البحث على الويب\n"
            "• التحقق من رصيدك بـ /balance\n\n"
            "أرد تلقائياً بلغتك."
        ),
        "zh": (
            "ℹ️ *帮助*\n\n"
            "我是您的AI助手。您可以：\n"
            "• 问我任何问题\n"
            "• 请求代码、分析或创意写作\n"
            "• 查询天气或搜索网页\n"
            "• 用 /balance 查看余额\n\n"
            "我会自动用您的语言回复。"
        ),
    },

    # ── balance display ───────────────────────────────────────────────────────
    "balance_display": {
        "en": "💰 Balance: ${amount}",
        "ru": "💰 Баланс: ${amount}",
        "de": "💰 Guthaben: ${amount}",
        "fr": "💰 Solde : ${amount}",
        "es": "💰 Saldo: ${amount}",
        "pt": "💰 Saldo: ${amount}",
        "it": "💰 Saldo: ${amount}",
        "tr": "💰 Bakiye: ${amount}",
        "ar": "💰 الرصيد: ${amount}",
        "zh": "💰 余额：${amount}",
        "ja": "💰 残高：${amount}",
        "ko": "💰 잔액: ${amount}",
        "pl": "💰 Saldo: ${amount}",
        "uk": "💰 Баланс: ${amount}",
        "fa": "💰 موجودی: ${amount}",
    },

    # ── callback / UI states ──────────────────────────────────────────────────
    "cancelled": {
        "en": "✅ Cancelled.",
        "ru": "✅ Отменено.",
        "de": "✅ Abgebrochen.",
        "fr": "✅ Annulé.",
        "es": "✅ Cancelado.",
        "pt": "✅ Cancelado.",
        "it": "✅ Annullato.",
        "tr": "✅ İptal edildi.",
        "ar": "✅ تم الإلغاء.",
        "zh": "✅ 已取消。",
        "ja": "✅ キャンセルしました。",
        "ko": "✅ 취소됨.",
        "pl": "✅ Anulowano.",
        "uk": "✅ Скасовано.",
        "fa": "✅ لغو شد.",
    },

    # ── silent keys — no message sent ─────────────────────────────────────────
    "empty_message":  {"_silent": "true"},
    "no_user_id":     {"_silent": "true"},
}

# Keys that intentionally produce no output
_SILENT_KEYS: frozenset[str] = frozenset({"empty_message", "no_user_id"})

# ─── PUBLIC API: LOCALISED MESSAGE LOOKUP ─────────────────────────────────────

def get_system_message(key: str, lang: str) -> str:
    """
    Return a localised system message for the given key and language.
    Falls back to English if lang not available.
    Returns "" for silent keys.
    """
    if key in _SILENT_KEYS:
        return ""
    bucket = _MESSAGES.get(key, {})
    return bucket.get(lang) or bucket.get("en", "⚠️ An error occurred.")


def format_balance_message(balance: float, lang: str) -> str:
    """Return a localised balance string with the amount substituted."""
    template = get_system_message("balance_display", lang)
    return template.replace("${amount}", f"{balance:.2f}")


# ─── I/O CONTRACTS ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: "Intent | None"
    tier: Tier
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    truncated: bool = False


# ─── INTERNAL PIPELINE ────────────────────────────────────────────────────────

def _assemble(raw: str) -> str:
    """Step 1: take raw LLM output as-is."""
    return raw


def _structure(text: str, intent: "Intent | None") -> str:
    """Step 2: intent-aware light structuring (currently a passthrough)."""
    # Future: add intent-specific post-processing (e.g., code block wrapping)
    return text


def _format(text: str) -> str:
    """Step 3: normalise whitespace, strip leading/trailing blank lines."""
    lines = text.splitlines()
    # Remove excessive blank lines (max 2 consecutive)
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _apply_correction(text: str) -> str:
    """
    Step 4: apply meta/correction.py.
    correction.py is owned by meta/ but executed here — it has NO authority.
    It may clean up formatting or fix minor issues; it cannot change meaning.
    If correction raises, we silently skip it (synthesizer intent preserved).
    """
    try:
        from meta.correction import apply
        corrected = apply(text)
        # Safety: if correction returns empty, discard and keep original
        return corrected if corrected and corrected.strip() else text
    except Exception:
        return text


def _truncate(text: str, lang: str) -> tuple[str, bool]:
    """Step 5a: enforce Telegram 4096-char limit."""
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    suffix = get_system_message("truncation_suffix", lang)
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


def _finalize(text: str, lang: str) -> tuple[str, bool]:
    """Step 5: truncate and return."""
    return _truncate(text, lang)


# ─── MAIN SYNTHESIZER ─────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into the final user-facing message.

    Pipeline:
      1. assemble     — accept raw text
      2. structure    — intent-aware shaping
      3. format       — whitespace normalisation
      4. correction   — meta/correction