from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)

# ─── TELEGRAM LIMITS ──────────────────────────────────────────────────────────

_TELEGRAM_MAX_CHARS = 4096

# ─── TON WALLET ───────────────────────────────────────────────────────────────

_TON_WALLET = "UQA78muNWF-tW4bhePG8GMdXzj1RuByOtf1XAwZ9VDOBElSA"

# ─── SUPPORTED LANGUAGES ──────────────────────────────────────────────────────

_SUPPORTED_LANGS = {
    "en", "ru", "de", "fr", "es", "pt", "it", "tr", "ar",
    "zh", "ja", "ko", "pl", "uk", "fa", "nl", "sv", "no",
    "da", "fi", "cs", "sk", "ro", "hu", "bg", "hr", "sr",
    "he", "vi", "th", "id", "ms", "hi", "bn", "ur",
    "az", "kk", "uz", "ka", "hy", "mn", "sw", "am",
}

# ─── SYSTEM MESSAGES ──────────────────────────────────────────────────────────

_MESSAGES: dict[str, dict[str, str]] = {

    # ── balance ───────────────────────────────────────────────────────────────
    "insufficient_balance": {
        "en": (
            "⚠️ *Insufficient balance.*\n\n"
            "To continue, please top up your account via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "After sending, your balance will be updated automatically."
        ),
        "ru": (
            "⚠️ *Недостаточно средств.*\n\n"
            "Для продолжения пополните счёт через TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "После перевода баланс обновится автоматически."
        ),
        "de": (
            "⚠️ *Unzureichendes Guthaben.*\n\n"
            "Bitte lade dein Konto über TON auf:\n"
            f"`{_TON_WALLET}`\n\n"
            "Nach der Überweisung wird dein Guthaben automatisch aktualisiert."
        ),
        "fr": (
            "⚠️ *Solde insuffisant.*\n\n"
            "Veuillez recharger votre compte via TON :\n"
            f"`{_TON_WALLET}`\n\n"
            "Après le virement, votre solde sera mis à jour automatiquement."
        ),
        "es": (
            "⚠️ *Saldo insuficiente.*\n\n"
            "Por favor recarga tu cuenta vía TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Tras el envío, tu saldo se actualizará automáticamente."
        ),
        "pt": (
            "⚠️ *Saldo insuficiente.*\n\n"
            "Por favor recarregue sua conta via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Após o envio, seu saldo será atualizado automaticamente."
        ),
        "it": (
            "⚠️ *Saldo insufficiente.*\n\n"
            "Ricarica il tuo account tramite TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Dopo il trasferimento il saldo verrà aggiornato automaticamente."
        ),
        "tr": (
            "⚠️ *Yetersiz bakiye.*\n\n"
            "Lütfen TON aracılığıyla hesabınızı doldurun:\n"
            f"`{_TON_WALLET}`\n\n"
            "Gönderdikten sonra bakiyeniz otomatik olarak güncellenecektir."
        ),
        "ar": (
            "⚠️ *رصيد غير كافٍ.*\n\n"
            "يرجى شحن حسابك عبر TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "بعد الإرسال سيتم تحديث رصيدك تلقائياً."
        ),
        "zh": (
            "⚠️ *余额不足。*\n\n"
            "请通过 TON 充值您的账户：\n"
            f"`{_TON_WALLET}`\n\n"
            "转账后余额将自动更新。"
        ),
        "ja": (
            "⚠️ *残高不足です。*\n\n"
            "TON でアカウントをチャージしてください：\n"
            f"`{_TON_WALLET}`\n\n"
            "送金後、残高は自動的に更新されます。"
        ),
        "ko": (
            "⚠️ *잔액이 부족합니다.*\n\n"
            "TON을 통해 계정을 충전해 주세요:\n"
            f"`{_TON_WALLET}`\n\n"
            "전송 후 잔액이 자동으로 업데이트됩니다."
        ),
        "pl": (
            "⚠️ *Niewystarczające środki.*\n\n"
            "Doładuj konto przez TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Po przelewie saldo zostanie automatycznie zaktualizowane."
        ),
        "uk": (
            "⚠️ *Недостатньо коштів.*\n\n"
            "Поповніть рахунок через TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Після переказу баланс оновиться автоматично."
        ),
        "fa": (
            "⚠️ *موجودی کافی نیست.*\n\n"
            "لطفاً حساب خود را از طریق TON شارژ کنید:\n"
            f"`{_TON_WALLET}`\n\n"
            "پس از ارسال، موجودی شما به‌صورت خودکار به‌روز می‌شود."
        ),
        "nl": (
            "⚠️ *Onvoldoende saldo.*\n\n"
            "Laad uw account op via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Na de overschrijving wordt uw saldo automatisch bijgewerkt."
        ),
        "sv": (
            "⚠️ *Otillräckligt saldo.*\n\n"
            "Fyll på ditt konto via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Efter överföringen uppdateras ditt saldo automatiskt."
        ),
        "no": (
            "⚠️ *Utilstrekkelig saldo.*\n\n"
            "Fyll på kontoen din via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Etter overføringen oppdateres saldoen automatisk."
        ),
        "da": (
            "⚠️ *Utilstrækkelig saldo.*\n\n"
            "Optank din konto via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Efter overførslen opdateres din saldo automatisk."
        ),
        "fi": (
            "⚠️ *Saldo ei riitä.*\n\n"
            "Lataa tilisi TON:n kautta:\n"
            f"`{_TON_WALLET}`\n\n"
            "Siirron jälkeen saldosi päivittyy automaattisesti."
        ),
        "he": (
            "⚠️ *יתרה לא מספיקה.*\n\n"
            "אנא טען את החשבון שלך דרך TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "לאחר ההעברה היתרה תתעדכן אוטומטית."
        ),
        "hi": (
            "⚠️ *अपर्याप्त शेष।*\n\n"
            "कृपया TON के माध्यम से अपना खाता टॉप अप करें:\n"
            f"`{_TON_WALLET}`\n\n"
            "भेजने के बाद आपका बैलेंस अपने आप अपडेट हो जाएगा।"
        ),
        "id": (
            "⚠️ *Saldo tidak mencukupi.*\n\n"
            "Silakan isi ulang akun Anda melalui TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Setelah pengiriman, saldo Anda akan diperbarui secara otomatis."
        ),
        "az": (
            "⚠️ *Balans kifayət deyil.*\n\n"
            "Zəhmət olmasa TON vasitəsilə hesabınızı doldurun:\n"
            f"`{_TON_WALLET}`\n\n"
            "Göndərdikdən sonra balansınız avtomatik yenilənəcək."
        ),
        "kk": (
            "⚠️ *Баланс жеткіліксіз.*\n\n"
            "TON арқылы шотыңызды толтырыңыз:\n"
            f"`{_TON_WALLET}`\n\n"
            "Жібергеннен кейін баланс автоматты түрде жаңартылады."
        ),
        "uz": (
            "⚠️ *Balans yetarli emas.*\n\n"
            "Iltimos, TON orqali hisobingizni to'ldiring:\n"
            f"`{_TON_WALLET}`\n\n"
            "Yuborilgandan so'ng balans avtomatik yangilanadi."
        ),
        "ka": (
            "⚠️ *არასაკმარისი ბალანსი.*\n\n"
            "გთხოვთ შეავსოთ ანგარიში TON-ის მეშვეობით:\n"
            f"`{_TON_WALLET}`\n\n"
            "გადარიცხვის შემდეგ ბალანსი ავტომატურად განახლდება."
        ),
        "hy": (
            "⚠️ *Անբավարար մնացորդ։*\n\n"
            "Խնդրում ենք համալրել հաշիվը TON-ի միջոցով:\n"
            f"`{_TON_WALLET}`\n\n"
            "Ուղարկելուց հետո մնացորդը ավտոմատ կթարմացվի:"
        ),
        "cs": (
            "⚠️ *Nedostatečný zůstatek.*\n\n"
            "Prosím dobijte svůj účet přes TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Po převodu bude váš zůstatek automaticky aktualizován."
        ),
        "ro": (
            "⚠️ *Sold insuficient.*\n\n"
            "Vă rugăm să reîncărcați contul prin TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "După transfer, soldul se va actualiza automat."
        ),
        "hu": (
            "⚠️ *Elégtelen egyenleg.*\n\n"
            "Kérjük, töltse fel fiókját TON-on keresztül:\n"
            f"`{_TON_WALLET}`\n\n"
            "Az átutalás után az egyenleg automatikusan frissül."
        ),
        "th": (
            "⚠️ *ยอดเงินไม่เพียงพอ*\n\n"
            "กรุณาเติมเงินในบัญชีผ่าน TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "หลังจากส่งแล้ว ยอดเงินจะอัปเดตโดยอัตโนมัติ"
        ),
        "vi": (
            "⚠️ *Số dư không đủ.*\n\n"
            "Vui lòng nạp tiền vào tài khoản qua TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Sau khi gửi, số dư sẽ được cập nhật tự động."
        ),
        "ms": (
            "⚠️ *Baki tidak mencukupi.*\n\n"
            "Sila tambah nilai akaun anda melalui TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Selepas penghantaran, baki anda akan dikemas kini secara automatik."
        ),
        "bn": (
            "⚠️ *অপর্যাপ্ত ব্যালেন্স।*\n\n"
            "অনুগ্রহ করে TON এর মাধ্যমে আপনার অ্যাকাউন্ট টপ আপ করুন:\n"
            f"`{_TON_WALLET}`\n\n"
            "পাঠানোর পরে আপনার ব্যালেন্স স্বয়ংক্রিয়ভাবে আপডেট হবে।"
        ),
        "ur": (
            "⚠️ *ناکافی بیلنس۔*\n\n"
            "براہ کرم TON کے ذریعے اپنا اکاؤنٹ ٹاپ اپ کریں:\n"
            f"`{_TON_WALLET}`\n\n"
            "بھیجنے کے بعد آپ کا بیلنس خود بخود اپ ڈیٹ ہو جائے گا۔"
        ),
        "bg": (
            "⚠️ *Недостатъчен баланс.*\n\n"
            "Моля, заредете акаунта си чрез TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "След превода балансът ще се актуализира автоматично."
        ),
        "hr": (
            "⚠️ *Nedovoljan saldo.*\n\n"
            "Molimo dopunite račun putem TON-a:\n"
            f"`{_TON_WALLET}`\n\n"
            "Nakon prijenosa saldo će se automatski ažurirati."
        ),
        "sr": (
            "⚠️ *Недовољан салдо.*\n\n"
            "Молимо допуните налог преко TON-а:\n"
            f"`{_TON_WALLET}`\n\n"
            "Након преноса салдо ће се аутоматски ажурирати."
        ),
        "sk": (
            "⚠️ *Nedostatočný zostatok.*\n\n"
            "Prosím dobite si účet cez TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Po prevode bude váš zostatok automaticky aktualizovaný."
        ),
        "mn": (
            "⚠️ *Үлдэгдэл хүрэлцэхгүй байна.*\n\n"
            "TON-оор дансаа цэнэглэнэ үү:\n"
            f"`{_TON_WALLET}`\n\n"
            "Илгээсний дараа үлдэгдэл автоматаар шинэчлэгдэнэ."
        ),
    },

    # ── no LLM response received ──────────────────────────────────────────────
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
        "ka": "⚠️ პასუხი არ მიღებულა. გთხოვთ სცადოთ თავიდან.",
        "hy": "⚠️ Պատասխան չստացվեց: Խնդրում ենք կրկին փորձել:",
        "mn": "⚠️ Хариу ирсэнгүй. Дахин оролдоно уу.",
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
        "ka": "⚠️ მოთხოვნის დამუშავება ვერ მოხერხდა. გთხოვთ სხვაგვარად ჩამოაყალიბოთ.",
        "hy": "⚠️ Հնարավոր չեղավ մշակել հարցումը: Խնդրում ենք վերաձևակերպել:",
        "mn": "⚠️ Хүсэлтийг боловсруулах боломжгүй байна. Өөрөөр найруулна уу.",
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
        "ka": "🚫 ეს მოთხოვნა ჩემს წესებს ეწინააღმდეგება. გთხოვთ სხვა რამ სცადოთ.",
        "hy": "🚫 Այս հարցումը հակասում է իմ կանոններին: Խնդրում ենք փորձել մեկ այլ բան:",
        "mn": "🚫 Энэ хүсэлт миний дүрмийг зөрчиж байна. Өөр зүйл туршина уу.",
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
        "ka": "⏳ თქვენ ძალიან სწრაფად აგზავნით შეტყობინებებს. გთხოვთ დაიცადოთ.",
        "hy": "⏳ Դուք շատ արագ եք ուղարկում հաղորդագրություններ: Խնդրում ենք սպասել:",
        "mn": "⏳ Та хэт хурдан мессеж илгээж байна. Түр хүлээнэ үү.",
    },

    # ── truncation suffix ─────────────────────────────────────────────────────
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
        "ka": "\n\n_…პასუხი შეკვეცილია_",
        "hy": "\n\n_…պատասխանը կրճատված է_",
        "mn": "\n\n_…хариу таслагдсан_",
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
        "ka": (
            "ℹ️ *დახმარება*\n\n"
            "მე ვარ თქვენი AI ასისტენტი. შეგიძლიათ:\n"
            "• დამისვათ ნებისმიერი კითხვა\n"
            "• მოითხოვოთ კოდი, ანალიზი ან შემოქმედებითი წერა\n"
            "• ჰკითხოთ ამინდი ან ვებ ძიება\n"
            "• შეამოწმოთ ბალანსი /balance-ით\n\n"
            "ავტომატურად ვპასუხობ თქვენს ენაზე."
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
        "ka": "💰 ბალანსი: ${amount}",
        "hy": "💰 Մնացորդ: ${amount}",
        "mn": "💰 Үлдэгдэл: ${amount}",
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
        "ka": "✅ გაუქმებულია.",
        "hy": "✅ Չեղարկված է:",
        "mn": "✅ Цуцлагдсан.",
    },

    # ── silent keys ───────────────────────────────────────────────────────────
    "empty_message": {"_silent": "true"},
    "no_user_id":    {"_silent": "true"},
}

_SILENT_KEYS: frozenset[str] = frozenset({"empty_message", "no_user_id"})


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def get_system_message(key: str, lang: str) -> str:
    if key in _SILENT_KEYS:
        return ""
    bucket = _MESSAGES.get(key, {})
    return bucket.get(lang) or bucket.get("en", "⚠️ An error occurred.")


def format_balance_message(balance: float, lang: str) -> str:
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
    return raw


def _structure(text: str, intent: "Intent | None") -> str:
    return text


def _format(text: str) -> str:
    lines = text.splitlines()
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
    try:
        from meta.correction import apply
        corrected = apply(text)
        return corrected if corrected and corrected.strip() else text
    except Exception:
        return text


def _truncate(text: str, lang: str) -> tuple[str, bool]:
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    suffix = get_system_message("truncation_suffix", lang)
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


def _finalize(text: str, lang: str) -> tuple[str, bool]:
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
      5. finalize     — truncate to Telegram limit
    """
    lang = inp.lang if inp.lang in _SUPPORTED_LANGS else "en"

    # ── DENY path ─────────────────────────────────────────────────────────────
    if inp.denied:
        key = inp.deny_reason if inp.deny_reason in _MESSAGES else "default_deny"
        if key in _SILENT_KEYS:
            return SynthesisResult(text="")
        return SynthesisResult(text=get_system_message(key, lang))

    # ── no LLM response ───────────────────────────────────────────────────────
    if not inp.raw_text or not inp.raw_text.strip():
        return SynthesisResult(text=get_system_message("no_response", lang))

    # ── normal pipeline ───────────────────────────────────────────────────────
    text = _assemble(inp.raw_text)
    text = _structure(text, inp.intent)
    text = _format(text)
    text = _apply_correction(text)
    text, truncated = _finalize(text, lang)

    return SynthesisResult(text=text, truncated=truncated)