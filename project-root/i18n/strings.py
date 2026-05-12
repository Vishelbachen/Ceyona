from __future__ import annotations

# ─── SUPPORTED LANGUAGES ──────────────────────────────────────────────────────

SUPPORTED_LANGS = {
    "en", "ru", "de", "fr", "es", "pt", "it", "tr", "ar",
    "zh", "ja", "ko", "pl", "uk", "fa", "nl", "sv", "no",
    "da", "fi", "cs", "sk", "ro", "hu", "bg", "hr", "sr",
    "he", "vi", "th", "id", "ms", "hi", "bn", "ur",
    "az", "kk", "uz", "ka", "hy", "mn", "sw", "am",
    # Extended language support
    "ha", "yo", "ig", "so", "ku", "ps", "ug", "tt",
}

# Maps bot lang codes to OpenWeatherMap lang codes
OW_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh_cn", "ja": "ja", "ko": "kr",
    "pl": "pl", "uk": "ua", "fa": "fa", "nl": "nl",
    "sv": "sv", "no": "no", "da": "da", "fi": "fi",
    "he": "he", "vi": "vi", "th": "th", "id": "id",
    "ms": "ms", "hi": "hi", "bn": "bn", "ur": "ur",
    "az": "az", "kk": "en", "uz": "uz", "ka": "ka",
    "hy": "hy", "mn": "en", "si": "en", "km": "en",
    "lo": "en", "my": "en", "am": "en", "sw": "en",
    "cs": "cz", "sk": "sk", "ro": "ro", "hu": "hu",
    "bg": "bg", "hr": "hr", "sr": "sr",
    # Languages without OWM support → English descriptions
    "ha": "en", "yo": "en", "ig": "en", "so": "en",
    "ps": "en", "ku": "en", "ug": "en", "tt": "en",
}

# Maps lang code to LLM instruction ("reply only in X")
LANG_INSTRUCTIONS: dict[str, str] = {
    "ru": "Отвечай ТОЛЬКО на русском языке.",
    "en": "Reply ONLY in English.",
    "de": "Antworte NUR auf Deutsch.",
    "fr": "Réponds UNIQUEMENT en français.",
    "es": "Responde SÓLO en español.",
    "uk": "Відповідай ТІЛЬКИ українською мовою.",
    "tr": "YALNIZCA Türkçe yanıtla.",
    "ar": "أجب باللغة العربية فقط.",
    "zh": "只用中文回答。",
    "ja": "日本語のみで答えてください。",
    "ko": "한국어로만 답하세요.",
    "pl": "Odpowiadaj TYLKO po polsku.",
    "it": "Rispondi SOLO in italiano.",
    "pt": "Responda APENAS em português.",
    "fa": "فقط به فارسی پاسخ بده.",
    "nl": "Antwoord ALLEEN in het Nederlands.",
    "sv": "Svara BARA på svenska.",
    "no": "Svar KUN på norsk.",
    "da": "Svar KUN på dansk.",
    "fi": "Vastaa VAIN suomeksi.",
    "he": "ענה רק בעברית.",
    "hi": "केवल हिंदी में जवाब दें।",
    "id": "Jawab HANYA dalam bahasa Indonesia.",
    "az": "YALNIZ Azərbaycanca cavab ver.",
    "kk": "ТЕК қазақша жауап бер.",
    "uz": "FAQAT o'zbekcha javob bering.",
    "ka": "უპასუხე ᲛᲮᲝᲚᲝᲓ ქართულად.",
    "hy": "Պատասխանիր ՄԻԱՅՆ հայերեն.",
    "mn": "ЗӨВХӨН монголоор хариулна уу.",
    "bg": "Отговаряй САМО на български.",
    "hr": "Odgovaraj SAMO na hrvatskom.",
    "sr": "Одговарај САМО на српском.",
    "cs": "Odpovídej POUZE česky.",
    "sk": "Odpovedaj IBA po slovensky.",
    "ro": "Răspunde DOAR în română.",
    "hu": "Csak magyarul válaszolj.",
    "th": "ตอบเป็นภาษาไทยเท่านั้น",
    "vi": "Chỉ trả lời bằng tiếng Việt.",
    "ms": "Jawab HANYA dalam Bahasa Malaysia.",
    "bn": "শুধু বাংলায় উত্তর দাও।",
    "ur": "صرف اردو میں جواب دیں۔",
    "sw": "Jibu kwa Kiswahili tu.",
    "am": "በአማርኛ ብቻ መልስ ስጥ።",
    "ha": "Amsa KAWAI da Hausa.",
    "yo": "Dahun NIKAN ni Yorùbá.",
    "ig": "Zaghachi NAANỊ n'Igbo.",
    "so": "Ku jawaab KALIYA Soomaali.",
    "ku": "Bersivê TENÊ bi Kurdî bide.",
    "ps": "یوازې پښتو کې ځواب ورکړئ.",
    "ug": "پەقەت ئۇيغۇرچە جاۋاب بېرىڭ.",
    "tt": "Тик татарча жавап бир.",
}

_TON_WALLET = "UQA78muNWF-tW4bhePG8GMdXzj1RuByOtf1XAwZ9VDOBElSA"

# ─── ALL STRINGS ──────────────────────────────────────────────────────────────
# Ported directly from cognition/response_synthesizer._MESSAGES
# with full Unicode preserved.

_STRINGS: dict[str, dict[str, str]] = {

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

    # ── no grounded data (Truth Enforcement — STRICT mode) ───────────────────
    "no_grounded_data": {
        "en": "🔍 I couldn't find reliable information to answer this. Please provide more context or try a different question.",
        "ru": "🔍 Не удалось найти достоверную информацию для ответа. Уточните запрос или попробуйте другой вопрос.",
        "de": "🔍 Ich konnte keine zuverlässigen Informationen finden. Bitte präzisiere deine Frage.",
        "fr": "🔍 Je n'ai pas trouvé d'informations fiables. Veuillez préciser votre question.",
        "es": "🔍 No encontré información confiable para responder. Por favor aclara tu pregunta.",
        "pt": "🔍 Não encontrei informações confiáveis. Por favor, reformule sua pergunta.",
        "it": "🔍 Non ho trovato informazioni affidabili. Per favore chiarisci la domanda.",
        "tr": "🔍 Güvenilir bilgi bulunamadı. Lütfen sorunuzu netleştirin.",
        "ar": "🔍 لم أتمكن من العثور على معلومات موثوقة. يرجى توضيح سؤالك.",
        "zh": "🔍 未找到可靠信息来回答此问题。请提供更多背景或换一个问题。",
        "ja": "🔍 信頼できる情報が見つかりませんでした。質問を明確にしてみてください。",
        "ko": "🔍 신뢰할 수 있는 정보를 찾지 못했습니다. 질문을 구체화해 주세요.",
        "pl": "🔍 Nie znalazłem wiarygodnych informacji. Proszę doprecyzować pytanie.",
        "uk": "🔍 Не вдалося знайти достовірну інформацію. Уточніть запит.",
        "fa": "🔍 اطلاعات قابل اعتمادی یافت نشد. لطفاً سؤال خود را دقیق‌تر بیان کنید.",
        "nl": "🔍 Geen betrouwbare informatie gevonden. Probeer uw vraag te verduidelijken.",
        "sv": "🔍 Hittade ingen tillförlitlig information. Försök förtydliga din fråga.",
        "no": "🔍 Fant ingen pålitelig informasjon. Prøv å presisere spørsmålet.",
        "da": "🔍 Fandt ingen pålidelig information. Prøv at præcisere spørgsmålet.",
        "fi": "🔍 Luotettavia tietoja ei löydy. Yritä tarkentaa kysymystäsi.",
        "he": "🔍 לא נמצא מידע אמין. אנא נסח את השאלה בצורה ברורה יותר.",
        "hi": "🔍 विश्वसनीय जानकारी नहीं मिली। कृपया अपना प्रश्न स्पष्ट करें।",
        "id": "🔍 Tidak ditemukan informasi yang dapat dipercaya. Coba perjelas pertanyaan Anda.",
        "az": "🔍 Etibarlı məlumat tapılmadı. Zəhmət olmasa sualınızı dəqiqləşdirin.",
        "kk": "🔍 Сенімді ақпарат табылмады. Сұрақты нақтылап көріңіз.",
        "uz": "🔍 Ishonchli ma'lumot topilmadi. Iltimos savolingizni aniqlashtiring.",
        "ka": "🔍 სანდო ინფორმაცია ვერ მოიძებნა. გთხოვთ დააზუსტოთ კითხვა.",
        "hy": "🔍 Հուսալի տեղեկություն չի գտնվել: Խնդրում ենք հստակեցնել հարցը:",
        "mn": "🔍 Найдвартай мэдээлэл олдсонгүй. Асуултаа тодруулна уу.",
        "cs": "🔍 Nepodařilo se najít spolehlivé informace. Zkuste otázku upřesnit.",
        "ro": "🔍 Nu am găsit informații de încredere. Vă rugăm să clarificați întrebarea.",
        "hu": "🔍 Nem találtam megbízható információt. Kérjük, pontosítsa a kérdést.",
        "th": "🔍 ไม่พบข้อมูลที่เชื่อถือได้ กรุณาระบุคำถามให้ชัดเจนขึ้น",
        "vi": "🔍 Không tìm thấy thông tin đáng tin cậy. Vui lòng làm rõ câu hỏi.",
        "ms": "🔍 Tiada maklumat yang boleh dipercayai ditemui. Sila jelaskan soalan anda.",
        "bn": "🔍 নির্ভরযোগ্য তথ্য পাওয়া যায়নি। অনুগ্রহ করে প্রশ্নটি স্পষ্ট করুন।",
        "ur": "🔍 قابل اعتماد معلومات نہیں ملی۔ براہ کرم اپنا سوال واضح کریں۔",
        "bg": "🔍 Не намерих надеждна информация. Моля, уточнете въпроса.",
        "hr": "🔍 Nisu pronađene pouzdane informacije. Molimo pojasnite pitanje.",
        "sr": "🔍 Нису пронађене поуздане информације. Молимо прецизирајте питање.",
        "sk": "🔍 Nenašli sa spoľahlivé informácie. Skúste otázku upresniť.",
    },

    # ── vision error ─────────────────────────────────────────────────────────
    "vision_error": {
        "en": "⚠️ Failed to process the image. Please try again.",
        "ru": "⚠️ Не удалось обработать изображение. Попробуйте ещё раз.",
        "de": "⚠️ Bild konnte nicht verarbeitet werden. Bitte erneut versuchen.",
        "fr": "⚠️ Impossible de traiter l'image. Veuillez réessayer.",
        "es": "⚠️ No se pudo procesar la imagen. Inténtelo de nuevo.",
        "pt": "⚠️ Não foi possível processar a imagem. Tente novamente.",
        "it": "⚠️ Impossibile elaborare l'immagine. Riprova.",
        "tr": "⚠️ Görüntü işlenemedi. Lütfen tekrar deneyin.",
        "ar": "⚠️ تعذّر معالجة الصورة. يرجى المحاولة مرة أخرى.",
        "zh": "⚠️ 无法处理该图片。请重试。",
        "ja": "⚠️ 画像を処理できませんでした。もう一度お試しください。",
        "ko": "⚠️ 이미지를 처리할 수 없었습니다. 다시 시도해 주세요.",
        "pl": "⚠️ Nie udało się przetworzyć obrazu. Spróbuj ponownie.",
        "uk": "⚠️ Не вдалося обробити зображення. Спробуйте ще раз.",
        "fa": "⚠️ پردازش تصویر ناموفق بود. لطفاً دوباره امتحان کنید.",
        "nl": "⚠️ Kon de afbeelding niet verwerken. Probeer het opnieuw.",
        "sv": "⚠️ Det gick inte att behandla bilden. Försök igen.",
        "no": "⚠️ Kunne ikke behandle bildet. Vennligst prøv igjen.",
        "da": "⚠️ Kunne ikke behandle billedet. Prøv venligst igen.",
        "fi": "⚠️ Kuvan käsittely epäonnistui. Yritä uudelleen.",
        "he": "⚠️ לא ניתן לעבד את התמונה. אנא נסה שנית.",
        "hi": "⚠️ छवि को प्रोसेस नहीं किया जा सका। कृपया पुनः प्रयास करें।",
        "id": "⚠️ Gagal memproses gambar. Silakan coba lagi.",
        "az": "⚠️ Şəkli emal etmək mümkün olmadı. Zəhmət olmasa yenidən cəhd edin.",
        "kk": "⚠️ Суретті өңдеу мүмкін болмады. Қайталап көріңіз.",
        "uz": "⚠️ Rasmni qayta ishlash imkoni bo'lmadi. Iltimos qayta urinib ko'ring.",
        "ka": "⚠️ სურათის დამუშავება ვერ მოხერხდა. გთხოვთ სცადოთ თავიდან.",
        "hy": "⚠️ Չհաջողվեց մշակել պատկերը: Խնդրում ենք կրկին փորձել:",
        "mn": "⚠️ Зургийг боловсруулж чадсангүй. Дахин оролдоно уу.",
    },

    # ── silent keys ───────────────────────────────────────────────────────────
    "empty_message": {"_silent": "true"},
    "no_user_id":    {"_silent": "true"},

    # ── emotional fallback — when LLM unavailable for a pure emotional reaction ─
    # Used by synthesize() as last resort before no_response.
    "emotional_fallback": {
        "ru": "Понимаю, это неприятно. Расскажи, что случилось — постараюсь помочь.",
        "en": "That sounds rough. Want to tell me more about what happened?",
        "de": "Das klingt wirklich frustrierend. Erzähl mir, was passiert ist.",
        "fr": "Ça a l'air difficile. Dis-moi ce qui s'est passé.",
        "es": "Entiendo, eso es difícil. Cuéntame qué pasó.",
        "pt": "Entendo, isso é difícil. Me conta o que aconteceu.",
        "it": "Capisco, sembra brutto. Dimmi cosa è successo.",
        "tr": "Anlıyorum, bu zor. Ne olduğunu anlatır mısın?",
        "ar": "أفهم ذلك، يبدو صعباً. أخبرني ماذا حدث.",
        "zh": "听起来很糟。跟我说说发生了什么？",
        "ja": "それは大変だったね。何があったか話してみて。",
        "ko": "힘들었겠네요. 무슨 일이 있었는지 얘기해줄래요?",
        "pl": "Rozumiem, to musi być frustrujące. Opowiedz, co się stało.",
        "uk": "Розумію, це неприємно. Розкажи, що сталося.",
        "fa": "می‌فهمم، این سخته. بگو چی شده.",
        "nl": "Dat klinkt vervelend. Vertel me wat er is gebeurd.",
        "sv": "Det låter jobbigt. Berätta vad som hände.",
        "no": "Det høres tøft ut. Fortell meg hva som skjedde.",
        "da": "Det lyder svært. Fortæl mig hvad der skete.",
        "fi": "Kuulostaa raskaalta. Kerro mitä tapahtui.",
        "he": "נשמע קשה. ספר לי מה קרה.",
        "hi": "समझ सकता हूँ, यह मुश्किल है। बताओ क्या हुआ।",
        "id": "Kedengarannya berat. Ceritakan apa yang terjadi.",
        "az": "Anlayıram, bu çətindir. De görüm nə baş verdi.",
        "kk": "Түсінемін, бұл ауыр. Не болғанын айтшы.",
        "uz": "Tushunaman, bu qiyin. Nima bo'lganini ayt.",
        "ka": "მესმის, ეს ძნელია. მიამბე, რა მოხდა.",
        "hy": "Հասկանում եմ, դա ծանր է: Պատմիր՝ ինչ եղավ:",
        "mn": "Ойлгож байна, энэ хэцүү. Юу болсноо хэлж өгнө үү.",
        "sw": "Naelewa, ni vigumu. Niambie kilichotokea.",
        "am": "እረዳለሁ፣ ይህ ከባድ ነው። ምን እንደሆነ ንገረኝ።",
        "bg": "Разбирам, това е неприятно. Разкажи ми какво се е случило.",
        "hr": "Razumijem, to zvuči teško. Ispričaj mi što se dogodilo.",
        "sr": "Разумем, то звучи тешко. Причај ми шта се догодило.",
        "cs": "Chápu, to musí být nepříjemné. Řekni mi, co se stalo.",
        "sk": "Chápem, musí to byť nepríjemné. Povedz mi, čo sa stalo.",
        "ro": "Înțeleg, sună greu. Spune-mi ce s-a întâmplat.",
        "hu": "Értem, ez nehéz lehet. Mesélj, mi történt.",
        "vi": "Nghe có vẻ khó khăn. Kể cho tôi nghe chuyện gì đã xảy ra.",
        "th": "ฟังดูยากเลย บอกฉันหน่อยได้ไหมว่าเกิดอะไรขึ้น?",
        "ms": "Kedengarannya berat. Ceritakan apa yang berlaku.",
        "bn": "বুঝতে পারছি, এটা কঠিন। কী হয়েছে বলো।",
        "ur": "سمجھ سکتا ہوں، یہ مشکل ہے۔ بتاؤ کیا ہوا۔",
    },
}

_SILENT_KEYS: frozenset[str] = frozenset({"empty_message", "no_user_id"})


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def t(key: str, lang: str, **kwargs: str) -> str:
    if key in _SILENT_KEYS:
        return ""
    bucket = _STRINGS.get(key, {})
    text = bucket.get(lang) or bucket.get("en", "")
    for k, v in kwargs.items():
        text = text.replace("${" + k + "}", v)
    return text


def lang_instruction(lang: str) -> str:
    return LANG_INSTRUCTIONS.get(lang, "Reply in the same language the user wrote in.")


def ow_lang(lang: str) -> str:
    return OW_LANG_MAP.get(lang, "en")


def is_supported(lang: str) -> bool:
    return lang in SUPPORTED_LANGS


def normalize_lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"