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

# Maps ambiguous/non-obvious lang codes to canonical English names.
# Only codes where raw ISO 639-1 would be misread by the LLM are listed.
# Standard codes (ru→Russian, fr→French, de→German, etc.) are passed directly —
# the model knows them. Aliases cover regional variants and lesser-known codes.
_LANG_ALIASES: dict[str, str] = {
    "zh": "Chinese",
    "pt-br": "Brazilian Portuguese",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "sr": "Serbian",
    "bs": "Bosnian",
    "ug": "Uyghur",
    "tt": "Tatar",
}
_TON_WALLET = "UQA78muNWF-tW4bhePG8GMdXzj1RuByOtf1XAwZ9VDOBElSA"

# ─── WEATHER LABEL KEYS ───────────────────────────────────────────────────────
# Used by external/weather.py._label() to localise weather card labels.
# Single source of truth — do NOT duplicate these in weather.py or web_tools.py.
# Key contract: _i18n("weather_feels_like", lang) → native translation or "".
# weather.py falls back to the key string itself if result is "", so all
# languages not listed here will show the English key — add them here instead.

WEATHER_FEELS_LIKE: dict[str, str] = {
    "en": "feels like",         "ru": "ощущается как",      "de": "gefühlt",
    "fr": "ressenti",           "es": "sensación",           "pt": "sensação",
    "it": "percepito",          "tr": "hissedilen",          "ar": "يبدو كأنه",
    "zh": "体感",                "ja": "体感",                "ko": "체감",
    "pl": "odczuwalna",         "uk": "відчувається як",     "fa": "احساس می‌شود",
    "nl": "voelt als",          "sv": "känns som",           "no": "føles som",
    "da": "føles som",          "fi": "tuntuu kuin",         "he": "מורגש כ",
    "ka": "შეგრძნება",          "hy": "զգացվում է",          "az": "hiss edilir",
    "kk": "сезіледі",           "uz": "his qilinadi",        "mn": "мэдрэмж",
    "sw": "hisi",               "am": "ይሰማዋል",              "hi": "महसूस होता है",
    "bn": "অনুভূত হয়",         "ur": "محسوس ہوتا ہے",       "id": "terasa",
    "ms": "terasa",             "th": "รู้สึกเหมือน",         "vi": "cảm giác như",
    "bg": "усеща се",           "hr": "osjeća se",           "sr": "осећа се",
    "cs": "pocitová",           "sk": "pocitová",            "ro": "simțită",
    "hu": "hőérzet",            "ha": "yana ji kamar",       "yo": "ó dàbí",
    "so": "dareemaysa",         "el": "αίσθηση",             "lv": "jūtas kā",
    "lt": "jaučiasi kaip",      "et": "tundub",              "sl": "zdi se",
    "mk": "се чувствува",
}

WEATHER_HUMIDITY: dict[str, str] = {
    "en": "Humidity",           "ru": "Влажность",           "de": "Luftfeuchtigkeit",
    "fr": "Humidité",           "es": "Humedad",             "pt": "Umidade",
    "it": "Umidità",            "tr": "Nem",                 "ar": "الرطوبة",
    "zh": "湿度",                "ja": "湿度",                "ko": "습도",
    "pl": "Wilgotność",         "uk": "Вологість",           "fa": "رطوبت",
    "nl": "Vochtigheid",        "sv": "Luftfuktighet",       "no": "Luftfuktighet",
    "da": "Luftfugtighed",      "fi": "Kosteus",             "he": "לחות",
    "ka": "ტენიანობა",          "hy": "խոնավություն",        "az": "rütubət",
    "kk": "ылғалдылық",         "uz": "namlik",              "mn": "чийгшил",
    "sw": "unyevu",             "am": "እርጥበት",              "hi": "आर्द्रता",
    "bn": "আর্দ্রতা",           "ur": "نمی",                 "id": "Kelembapan",
    "ms": "Kelembapan",         "th": "ความชื้น",             "vi": "Độ ẩm",
    "bg": "Влажност",           "hr": "Vlažnost",            "sr": "Влажност",
    "cs": "Vlhkost",            "sk": "Vlhkosť",             "ro": "Umiditate",
    "hu": "Páratartalom",       "ha": "Danshi",              "yo": "Ọrọ omi",
    "so": "Qoyaanka",           "el": "Υγρασία",             "lv": "Mitrums",
    "lt": "Drėgnumas",          "et": "Niiskus",             "sl": "Vlažnost",
    "mk": "Влажност",
}

WEATHER_WIND: dict[str, str] = {
    "en": "Wind",        "ru": "Ветер",    "de": "Wind",     "fr": "Vent",
    "es": "Viento",      "pt": "Vento",    "it": "Vento",    "tr": "Rüzgar",
    "ar": "الرياح",      "zh": "风速",      "ja": "風速",     "ko": "바람",
    "pl": "Wiatr",       "uk": "Вітер",    "fa": "باد",      "nl": "Wind",
    "sv": "Vind",        "no": "Vind",     "da": "Vind",     "fi": "Tuuli",
    "he": "רוח",         "ka": "ქარი",    "hy": "քամի",     "az": "külək",
    "kk": "жел",         "uz": "shamol",   "mn": "салхи",    "sw": "upepo",
    "am": "ነፋስ",        "hi": "हवा",      "bn": "বাতাস",    "ur": "ہوا",
    "id": "Angin",       "ms": "Angin",    "th": "ลม",        "vi": "Gió",
    "bg": "Вятър",       "hr": "Vjetar",   "sr": "Ветар",    "cs": "Vítr",
    "sk": "Vietor",      "ro": "Vânt",     "hu": "Szél",     "ha": "Iska",
    "yo": "Afẹfẹ",       "so": "Dabaysha", "el": "Άνεμος",   "lv": "Vējš",
    "lt": "Vėjas",       "et": "Tuul",     "sl": "Veter",    "mk": "Ветер",
}

# ─── ALL STRINGS ──────────────────────────────────────────────────────────────
# Ported directly from cognition/response_synthesizer._MESSAGES
# with full Unicode preserved.

_STRINGS: dict[str, dict[str, str]] = {

    # ── weather labels ────────────────────────────────────────────────────────
    # Populated from the module-level dicts above so there is a single source
    # of truth. _i18n("weather_feels_like", lang) resolves through _STRINGS.
    "weather_feels_like": WEATHER_FEELS_LIKE,
    "weather_humidity":   WEATHER_HUMIDITY,
    "weather_wind":       WEATHER_WIND,

    # ── balance ───────────────────────────────────────────────────────────────
    "insufficient_balance": {
        # ⚠️ CRITICAL: Do NOT put wallet address here — user_id is unavailable at
        # string-definition time. The wallet address + user_id are shown together
        # in the callback handler (webhook.py CallbackAction.TOPUP) where user_id
        # is guaranteed. Without user_id in the TON memo, payments cannot be credited.
        # These strings direct the user to tap the button below — that is the only
        # safe path to send payment details.
        "en": "⚠️ *Insufficient balance.*\n\nTap the button below to top up — you'll see the wallet address and your personal payment ID.",
        "ru": "⚠️ *Недостаточно средств.*\n\nНажми кнопку ниже для пополнения — там будет адрес кошелька и твой личный ID платежа.",
        "de": "⚠️ *Unzureichendes Guthaben.*\n\nTippe unten auf die Schaltfläche — du siehst die Wallet-Adresse und deine persönliche Zahlungs-ID.",
        "fr": "⚠️ *Solde insuffisant.*\n\nAppuie sur le bouton ci-dessous — tu verras l'adresse du portefeuille et ton identifiant de paiement personnel.",
        "es": "⚠️ *Saldo insuficiente.*\n\nPulsa el botón de abajo — verás la dirección de la cartera y tu ID de pago personal.",
        "pt": "⚠️ *Saldo insuficiente.*\n\nToca no botão abaixo — verás o endereço da carteira e o teu ID de pagamento pessoal.",
        "it": "⚠️ *Saldo insufficiente.*\n\nPremi il pulsante in basso — vedrai l'indirizzo del wallet e il tuo ID di pagamento personale.",
        "tr": "⚠️ *Yetersiz bakiye.*\n\nAşağıdaki düğmeye dokun — cüzdan adresini ve kişisel ödeme kimliğini göreceksin.",
        "ar": "⚠️ *رصيد غير كافٍ.*\n\naاضغط على الزر أدناه — ستجد عنوان المحفظة ومعرّف الدفع الخاص بك.",
        "zh": "⚠️ *余额不足。*\n\n点击下方按钮充值——你将看到钱包地址和你的个人支付ID。",
        "ja": "⚠️ *残高不足です。*\n\n下のボタンをタップしてください — ウォレットアドレスとあなた専用の支払いIDが表示されます。",
        "ko": "⚠️ *잔액이 부족합니다.*\n\n아래 버튼을 탭하세요 — 지갑 주소와 개인 결제 ID가 표시됩니다.",
        "pl": "⚠️ *Niewystarczające środki.*\n\nKliknij przycisk poniżej — zobaczysz adres portfela i swoje osobiste ID płatności.",
        "uk": "⚠️ *Недостатньо коштів.*\n\nНатисни кнопку нижче — там буде адреса гаманця та твій особистий ID платежу.",
        "fa": "⚠️ *موجودی کافی نیست.*\n\nروی دکمه زیر ضربه بزن — آدرس کیف پول و شناسه پرداخت شخصی‌ات را خواهی دید.",
        "nl": "⚠️ *Onvoldoende saldo.*\n\nTik op de knop hieronder — je ziet het walletadres en je persoonlijke betalings-ID.",
        "sv": "⚠️ *Otillräckligt saldo.*\n\nTryck på knappen nedan — du ser plånboksadressen och ditt personliga betalnings-ID.",
        "no": "⚠️ *Utilstrekkelig saldo.*\n\nTrykk på knappen nedenfor — du vil se lommebokadresse og din personlige betalings-ID.",
        "da": "⚠️ *Utilstrækkelig saldo.*\n\nTryk på knappen nedenfor — du vil se wallet-adressen og dit personlige betalings-ID.",
        "fi": "⚠️ *Saldo ei riitä.*\n\nNapauta alla olevaa painiketta — näet lompakko-osoitteen ja henkilökohtaisen maksu-ID:si.",
        "he": "⚠️ *יתרה לא מספיקה.*\n\nלחץ על הכפתור למטה — תראה את כתובת הארנק ואת מזהה התשלום האישי שלך.",
        "hi": "⚠️ *अपर्याप्त शेष।*\n\nनीचे बटन दबाएं — आपको वॉलेट पता और अपना व्यक्तिगत भुगतान ID दिखाई देगा।",
        "id": "⚠️ *Saldo tidak mencukupi.*\n\nKetuk tombol di bawah — Anda akan melihat alamat dompet dan ID pembayaran pribadi Anda.",
        "az": "⚠️ *Balans kifayət deyil.*\n\nAşağıdakı düyməyə toxunun — cüzdan ünvanını və şəxsi ödəniş ID-nizi görəcəksiniz.",
        "kk": "⚠️ *Баланс жеткіліксіз.*\n\nТөмендегі түймені басыңыз — әмиян мекенжайын және жеке төлем ID-іңізді көресіз.",
        "uz": "⚠️ *Balans yetarli emas.*\n\nQuyidagi tugmani bosing — hamyon manzili va shaxsiy to'lov ID'ingizni ko'rasiz.",
        "ka": "⚠️ *არასაკმარისი ბალანსი.*\n\nდააჭირე ქვემოთ ღილაკს — დაინახავ საფულის მისამართს და შენს პირად გადახდის ID-ს.",
        "hy": "⚠️ *Անբավարար մնացորդ։*\n\nՍեղմեք ստորև բերված կոճակը — կտեսնեք դրամապանակի հասցեն և ձեր անձնական վճարային ID-ն:",
        "cs": "⚠️ *Nedostatečný zůstatek.*\n\nKlikněte na tlačítko níže — uvidíte adresu peněženky a své osobní platební ID.",
        "ro": "⚠️ *Sold insuficient.*\n\nApasă butonul de mai jos — vei vedea adresa portofelului și ID-ul tău personal de plată.",
        "hu": "⚠️ *Elégtelen egyenleg.*\n\nKoppintson az alábbi gombra — látni fogja a pénztárca címét és személyes fizetési azonosítóját.",
        "th": "⚠️ *ยอดเงินไม่เพียงพอ*\n\nแตะปุ่มด้านล่าง — คุณจะเห็นที่อยู่กระเป๋าเงินและ ID การชำระเงินส่วนตัวของคุณ",
        "vi": "⚠️ *Số dư không đủ.*\n\nNhấn nút bên dưới — bạn sẽ thấy địa chỉ ví và ID thanh toán cá nhân của bạn.",
        "ms": "⚠️ *Baki tidak mencukupi.*\n\nKetik butang di bawah — anda akan melihat alamat dompet dan ID pembayaran peribadi anda.",
        "bn": "⚠️ *অপর্যাপ্ত ব্যালেন্স।*\n\nনিচের বোতামটি ট্যাপ করুন — আপনি ওয়ালেটের ঠিকানা এবং আপনার ব্যক্তিগত পেমেন্ট ID দেখতে পাবেন।",
        "ur": "⚠️ *ناکافی بیلنس۔*\n\nنیچے بٹن دبائیں — آپ کو والیٹ ایڈریس اور اپنا ذاتی پیمنٹ ID نظر آئے گا۔",
        "bg": "⚠️ *Недостатъчен баланс.*\n\nНатиснете бутона по-долу — ще видите адреса на портфейла и личния си ID за плащане.",
        "hr": "⚠️ *Nedovoljan saldo.*\n\nPritisnite gumb ispod — vidjet ćete adresu novčanika i svoj osobni ID plaćanja.",
        "sr": "⚠️ *Недовољан салдо.*\n\nПритисните дугме испод — видећете адресу новчаника и свој лични ID за плаћање.",
        "sk": "⚠️ *Nedostatočný zostatok.*\n\nKliknite na tlačidlo nižšie — uvidíte adresu peňaženky a svoje osobné platobné ID.",
        "mn": "⚠️ *Үлдэгдэл хүрэлцэхгүй байна.*\n\nДоорх товчийг дарна уу — хэтэвчний хаяг болон таны хувийн төлбөрийн ID-г харах болно.",
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
    # Static fallback shown by /start and /help. Two languages hardcoded;
    # all others fall back to English (acceptable — this is a rare edge,
    # and the bot already replies in the user's language for everything else).
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
            "• Wetter oder Websuchen anfragen\n"
            "• Dein Guthaben mit /balance prüfen\n\n"
            "Ich antworte automatisch in deiner Sprache."
        ),
        "fr": (
            "ℹ️ *Aide*\n\n"
            "Je suis ton assistant IA. Tu peux :\n"
            "• Me poser n'importe quelle question\n"
            "• Demander du code, des analyses ou de l'écriture créative\n"
            "• Demander la météo ou des recherches web\n"
            "• Vérifier ton solde avec /balance\n\n"
            "Je réponds automatiquement dans ta langue."
        ),
        "es": (
            "ℹ️ *Ayuda*\n\n"
            "Soy tu asistente de IA. Puedes:\n"
            "• Preguntarme cualquier cosa\n"
            "• Pedir código, análisis o escritura creativa\n"
            "• Preguntar por el tiempo o hacer búsquedas web\n"
            "• Consultar tu saldo con /balance\n\n"
            "Respondo automáticamente en tu idioma."
        ),
        "pt": (
            "ℹ️ *Ajuda*\n\n"
            "Sou o teu assistente de IA. Podes:\n"
            "• Perguntar qualquer coisa\n"
            "• Pedir código, análises ou escrita criativa\n"
            "• Perguntar sobre o tempo ou fazer pesquisas web\n"
            "• Verificar o teu saldo com /balance\n\n"
            "Respondo automaticamente no teu idioma."
        ),
        "it": (
            "ℹ️ *Guida*\n\n"
            "Sono il tuo assistente IA. Puoi:\n"
            "• Chiedermi qualsiasi cosa\n"
            "• Richiedere codice, analisi o testi creativi\n"
            "• Chiedere il meteo o fare ricerche web\n"
            "• Controllare il saldo con /balance\n\n"
            "Rispondo automaticamente nella tua lingua."
        ),
        "tr": (
            "ℹ️ *Yardım*\n\n"
            "Ben senin yapay zeka asistanınım. Yapabileceklerin:\n"
            "• Her şeyi sorabilirsin\n"
            "• Kod, analiz veya yaratıcı yazı isteyebilirsin\n"
            "• Hava durumu veya web araması yapabilirsin\n"
            "• /balance ile bakiyeni kontrol edebilirsin\n\n"
            "Otomatik olarak senin dilinde yanıt veririm."
        ),
        "ar": (
            "ℹ️ *المساعدة*\n\n"
            "أنا مساعدك الذكي. يمكنك:\n"
            "• سؤالي عن أي شيء\n"
            "• طلب كود أو تحليل أو كتابة إبداعية\n"
            "• الاستفسار عن الطقس أو البحث على الويب\n"
            "• التحقق من رصيدك بـ /balance\n\n"
            "أرد تلقائياً بلغتك."
        ),
        "zh": (
            "ℹ️ *帮助*\n\n"
            "我是你的 AI 助手。你可以：\n"
            "• 问我任何问题\n"
            "• 请求代码、分析或创意写作\n"
            "• 询问天气或进行网络搜索\n"
            "• 用 /balance 查询余额\n\n"
            "我会自动用你的语言回复。"
        ),
        "uk": (
            "ℹ️ *Допомога*\n\n"
            "Я твій ШІ-асистент. Ти можеш:\n"
            "• Запитати будь-що\n"
            "• Попросити код, аналіз або творчий текст\n"
            "• Дізнатися погоду або зробити пошук\n"
            "• Перевірити баланс через /balance\n\n"
            "Я відповідаю твоєю мовою автоматично."
        ),
        "ka": (
            "ℹ️ *დახმარება*\n\n"
            "მე შენი AI ასისტენტი ვარ. შეგიძლია:\n"
            "• ნებისმიერი კითხვა დასვა\n"
            "• კოდი, ანალიზი ან კრეატიული ტექსტი მოითხოვო\n"
            "• ამინდი ან ვებ-ძიება გამოიყენო\n"
            "• ბალანსი შეამოწმო /balance-ით\n\n"
            "ავტომატურად ვპასუხობ შენს ენაზე."
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
        "en": "🔍 I couldn't find up-to-date information for this request right now — the search service may be temporarily unavailable. You can try again in a moment, or check Google Maps / Google directly for the most accurate result.",
        "ru": "🔍 Не удалось получить актуальную информацию прямо сейчас — сервис поиска временно недоступен. Попробуйте повторить чуть позже или проверьте напрямую в Google, Яндекс или 2ГИС.",
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
        "ka": "🔍 ამ მომენტში ვერ მოვიპოვე განახლებული ინფორმაცია — საძიებო სერვისი დროებით მიუწვდომელია. გთხოვთ, სცადოთ ოდნავ მოგვიანებით.",
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


    "too_many_images": {
        "en": "⚠️ I can process up to 6 images at a time. Please send them in smaller groups.",
        "ru": "⚠️ Я могу обработать до 6 изображений за раз. Пожалуйста, отправляйте меньшими группами.",
        "de": "⚠️ Ich kann bis zu 6 Bilder auf einmal verarbeiten. Bitte in kleineren Gruppen senden.",
        "fr": "⚠️ Je peux traiter jusqu'à 6 images à la fois. Veuillez les envoyer en petits groupes.",
        "es": "⚠️ Puedo procesar hasta 6 imágenes a la vez. Por favor, envíalas en grupos más pequeños.",
        "pt": "⚠️ Posso processar até 6 imagens de cada vez. Por favor, envie em grupos menores.",
        "it": "⚠️ Posso elaborare fino a 6 immagini alla volta. Invia in gruppi più piccoli.",
        "tr": "⚠️ Aynı anda en fazla 6 görsel işleyebilirim. Lütfen daha küçük gruplar halinde gönderin.",
        "ar": "⚠️ يمكنني معالجة حتى 6 صور في المرة الواحدة. يرجى إرسالها في مجموعات أصغر.",
        "zh": "⚠️ 我一次最多处理 6 张图片，请分批发送。",
        "ja": "⚠️ 一度に処理できる画像は最大6枚です。小さいグループに分けて送ってください。",
        "ko": "⚠️ 한 번에 최대 6개의 이미지를 처리할 수 있습니다. 더 작은 그룹으로 보내주세요.",
        "pl": "⚠️ Mogę przetworzyć do 6 obrazów na raz. Proszę wysyłać w mniejszych grupach.",
        "uk": "⚠️ Я можу обробити до 6 зображень за раз. Будь ласка, надсилайте меншими групами.",
        "fa": "⚠️ می‌توانم تا ۶ تصویر را در یک بار پردازش کنم. لطفاً در گروه‌های کوچک‌تر ارسال کنید.",
        "nl": "⚠️ Ik kan maximaal 6 afbeeldingen tegelijk verwerken. Stuur ze in kleinere groepen.",
        "sv": "⚠️ Jag kan behandla upp till 6 bilder åt gången. Skicka dem i mindre grupper.",
        "no": "⚠️ Jeg kan behandle opptil 6 bilder om gangen. Send dem i mindre grupper.",
        "da": "⚠️ Jeg kan behandle op til 6 billeder ad gangen. Send dem i mindre grupper.",
        "fi": "⚠️ Voin käsitellä enintään 6 kuvaa kerrallaan. Lähetä ne pienemmissä ryhmissä.",
        "he": "⚠️ אני יכול לעבד עד 6 תמונות בכל פעם. אנא שלח בקבוצות קטנות יותר.",
        "hi": "⚠️ मैं एक बार में अधिकतम 6 छवियाँ प्रोसेस कर सकता हूँ। कृपया छोटे समूहों में भेजें।",
        "id": "⚠️ Saya dapat memproses hingga 6 gambar sekaligus. Kirim dalam kelompok lebih kecil.",
        "az": "⚠️ Bir dəfədə maksimum 6 şəkil emal edə bilərəm. Zəhmət olmasa kiçik qruplarla göndərin.",
        "kk": "⚠️ Мен бір жолы ең көп 6 сурет өңдей аламын. Кішірек топтармен жіберіңіз.",
        "uz": "⚠️ Men bir vaqtda maksimal 6 ta rasmni qayta ishlay olaman. Iltimos kichikroq guruhlar bilan yuboring.",
        "ka": "⚠️ ერთდროულად მაქსიმუმ 6 სურათის დამუშავება შემიძლია. გთხოვთ, გამოგზავნოთ პატარა ჯგუფებად.",
        "hy": "⚠️ Կարող եմ մշակել մինչև 6 նկար միաժամանակ: Խնդրում ենք ուղարկել ավելի փոքր խմբերով:",
        "mn": "⚠️ Нэг удаад хамгийн ихдээ 6 зураг боловсруулж чадна. Жижиг бүлгүүдээр илгээнэ үү.",
    },

    # ── silent keys ───────────────────────────────────────────────────────────
    # ── weather labels ────────────────────────────────────────────────────────
    "weather_feels_like": {
        "en": "feels like", "ru": "ощущается как", "de": "gefühlt",
        "fr": "ressenti",   "es": "sensación",      "pt": "sensação",
        "it": "percepito",  "tr": "hissedilen",     "ar": "يبدو كأنه",
        "zh": "体感",        "ja": "体感",            "ko": "체감",
        "pl": "odczuwalna", "uk": "відчувається як", "fa": "احساس می‌شود",
        "nl": "voelt als",  "sv": "känns som",      "no": "føles som",
        "da": "føles som",  "fi": "tuntuu kuin",    "he": "מורגש כ",
        "ka": "ისეთივეა, როგორც", "hy": "ինչպես",    "az": "hiss olunur",
        "kk": "сезіледі",   "uz": "seziladi",       "hi": "जैसा लगता है",
        "id": "terasa",     "ms": "terasa",         "th": "รู้สึกเหมือน",
        "vi": "cảm giác",   "mn": "мэдрэмж",        "sw": "inajisikia kama",
        "bg": "усеща се",   "hr": "osjeća se",      "sr": "осећа се",
        "cs": "pocitově",   "sk": "cíti sa",        "ro": "se simte ca",
        "hu": "érzetben",
    },
    "weather_humidity": {
        "en": "Humidity",      "ru": "Влажность",    "de": "Luftfeuchtigkeit",
        "fr": "Humidité",      "es": "Humedad",       "pt": "Umidade",
        "it": "Umidità",       "tr": "Nem",           "ar": "الرطوبة",
        "zh": "湿度",           "ja": "湿度",           "ko": "습도",
        "pl": "Wilgotność",    "uk": "Вологість",     "fa": "رطوبت",
        "nl": "Vochtigheid",   "sv": "Luftfuktighet", "no": "Luftfuktighet",
        "da": "Luftfugtighed", "fi": "Kosteus",       "he": "לחות",
        "ka": "ტენიანობა",     "hy": "Խոնավություն",  "az": "Rütubət",
        "kk": "Ылғалдылық",    "uz": "Namlik",        "hi": "आर्द्रता",
        "id": "Kelembaban",    "ms": "Kelembapan",    "th": "ความชื้น",
        "vi": "Độ ẩm",         "mn": "Чийглэг",       "sw": "Unyevu",
        "bg": "Влажност",      "hr": "Vlažnost",      "sr": "Влажност",
        "cs": "Vlhkost",       "sk": "Vlhkosť",       "ro": "Umiditate",
        "hu": "Páratartalom",
    },
    "weather_wind": {
        "en": "Wind",   "ru": "Ветер",   "de": "Wind",   "fr": "Vent",
        "es": "Viento", "pt": "Vento",   "it": "Vento",  "tr": "Rüzgar",
        "ar": "الرياح", "zh": "风速",    "ja": "風速",    "ko": "바람",
        "pl": "Wiatr",  "uk": "Вітер",   "fa": "باد",    "nl": "Wind",
        "sv": "Vind",   "no": "Vind",    "da": "Vind",   "fi": "Tuuli",
        "he": "רוח",    "ka": "ქარი",    "hy": "Քամի",   "az": "Külək",
        "kk": "Жел",    "uz": "Shamol",  "hi": "हवा",    "id": "Angin",
        "ms": "Angin",  "th": "ลม",      "vi": "Gió",    "mn": "Салхи",
        "sw": "Upepo",  "bg": "Вятър",  "hr": "Vjetar",  "sr": "Ветар",
        "cs": "Vítr",   "sk": "Vietor",  "ro": "Vânt",   "hu": "Szél",
    },
    # ── search ────────────────────────────────────────────────────────────────
    "no_search_results": {
        "en": "🔍 No results found.",
        "ru": "🔍 Результаты не найдены.",
        "de": "🔍 Keine Ergebnisse gefunden.",
        "fr": "🔍 Aucun résultat trouvé.",
        "es": "🔍 No se encontraron resultados.",
        "pt": "🔍 Nenhum resultado encontrado.",
        "it": "🔍 Nessun risultato trovato.",
        "tr": "🔍 Sonuç bulunamadı.",
        "ar": "🔍 لم يتم العثور على نتائج.",
        "zh": "🔍 未找到结果。",
        "ja": "🔍 結果が見つかりませんでした。",
        "ko": "🔍 결과를 찾을 수 없습니다.",
        "pl": "🔍 Nie znaleziono wyników.",
        "uk": "🔍 Результати не знайдено.",
        "fa": "🔍 نتیجه‌ای یافت نشد.",
        "nl": "🔍 Geen resultaten gevonden.",
        "sv": "🔍 Inga resultat hittades.",
        "no": "🔍 Ingen resultater funnet.",
        "da": "🔍 Ingen resultater fundet.",
        "fi": "🔍 Tuloksia ei löydy.",
        "he": "🔍 לא נמצאו תוצאות.",
        "hi": "🔍 कोई परिणाम नहीं मिला।",
        "id": "🔍 Tidak ada hasil ditemukan.",
        "ms": "🔍 Tiada keputusan ditemui.",
        "th": "🔍 ไม่พบผลลัพธ์",
        "vi": "🔍 Không tìm thấy kết quả.",
        "ka": "🔍 შედეგები ვერ მოიძებნა.",
        "hy": "🔍 Արդյունքներ չեն գտնվել:",
        "az": "🔍 Nəticə tapılmadı.",
        "kk": "🔍 Нәтиже табылмады.",
        "uz": "🔍 Natija topilmadi.",
        "mn": "🔍 Үр дүн олдсонгүй.",
        "sw": "🔍 Hakuna matokeo yaliyopatikana.",
        "bg": "🔍 Не са намерени резултати.",
        "hr": "🔍 Nisu pronađeni rezultati.",
        "sr": "🔍 Нису пронађени резултати.",
        "cs": "🔍 Žádné výsledky nenalezeny.",
        "sk": "🔍 Žiadne výsledky sa nenašli.",
        "ro": "🔍 Nu s-au găsit rezultate.",
        "hu": "🔍 Nem találhatók eredmények.",
        "bn": "🔍 কোনো ফলাফল পাওয়া যায়নি।",
        "ur": "🔍 کوئی نتیجہ نہیں ملا۔",
        "ha": "🔍 Ba a sami sakamakon ba.",
        "yo": "🔍 Ko si abajade ti a ri.",
        "so": "🔍 Natiijooyin lama helin.",
    },


    # ── emotional fallback — last-resort when LLM is completely unavailable ────
    # NOT a conversational reply — a neutral system message.
    # Warm enough to not feel broken; short enough to not feel like LLM output.
    "emotional_fallback": {
        "en": "Couldn't get a response right now. You can try again 🔄",
        "ru": "Сейчас не получилось ответить. Попробуй ещё раз 🔄",
        "de": "Gerade keine Antwort möglich. Versuch es nochmal 🔄",
        "fr": "Impossible de répondre pour l'instant. Réessaie 🔄",
        "es": "No pude responder ahora. Puedes intentarlo de nuevo 🔄",
        "pt": "Não foi possível responder agora. Tenta novamente 🔄",
        "it": "Non è stato possibile rispondere ora. Riprova 🔄",
        "tr": "Şu an yanıt veremedim. Tekrar deneyebilirsin 🔄",
        "ar": "لم أتمكن من الرد الآن. يمكنك المحاولة مرة أخرى 🔄",
        "zh": "暂时无法回复，请再试一次 🔄",
        "uk": "Зараз не вдалося відповісти. Спробуй ще раз 🔄",
        "ka": "ახლა პასუხის გაცემა ვერ მოხერხდა. სცადეთ თავიდან 🔄",
    },

    # ── CoT loop fallback — shown when model produced a reasoning loop instead of answer ──
    # Used by response_synthesizer._strip_cot_artifacts() when loop_signal_count >= 2.
    # Language-correct via inp.lang — no script detection heuristic.
    # Minimal set: LLM handles remaining languages natively via lang_instruction.
    "cot_fallback": {
        "en": "I'm not sure — could you give me a hint or more context?",
        "ru": "Не могу точно определить — попробуй дать подсказку или уточнить вопрос.",
        "de": "Ich bin nicht sicher — kannst du mir einen Hinweis oder mehr Kontext geben?",
        "fr": "Je ne suis pas sûr — pourrais-tu me donner un indice ou plus de contexte ?",
        "es": "No estoy seguro — ¿puedes darme una pista o más contexto?",
        "pt": "Não tenho certeza — podes dar-me uma dica ou mais contexto?",
        "it": "Non sono sicuro — potresti darmi un indizio o più contesto?",
        "ar": "لست متأكدًا — هل يمكنك إعطائي تلميحًا أو مزيدًا من السياق؟",
        "zh": "我不确定——能给我一个提示或更多背景吗？",
        "tr": "Emin değilim — bana bir ipucu veya daha fazla bağlam verebilir misin?",
        "uk": "Не можу точно визначити — спробуй дати підказку або уточни запитання.",
        "ka": "დარწმუნებული არ ვარ — შეგიძლია მომცე მინიშნება ან დამატებითი კონტექსტი?",
    },

    # ── top-up inline keyboard button label ──────────────────────────────────
    "top_up_button": {
        "en": "💵 Top Up Balance",
        "ru": "💵 Пополнить баланс",
        "de": "💵 Guthaben aufladen",
        "fr": "💵 Recharger le solde",
        "es": "💵 Recargar saldo",
        "pt": "💵 Recarregar saldo",
        "it": "💵 Ricarica il saldo",
        "tr": "💵 Bakiye yükle",
        "ar": "💵 شحن الرصيد",
        "zh": "💵 充值余额",
        "ja": "💵 残高をチャージ",
        "ko": "💵 잔액 충전",
        "pl": "💵 Doładuj konto",
        "uk": "💵 Поповнити баланс",
        "fa": "💵 شارژ موجودی",
        "nl": "💵 Saldo opladen",
        "sv": "💵 Fyll på saldo",
        "no": "💵 Fyll på saldo",
        "da": "💵 Opfyld saldo",
        "fi": "💵 Lataa saldo",
        "he": "💵 טעינת יתרה",
        "ka": "💵 ბალანსის შევსება",
        "hy": "💵 Համալրել մնացորդը",
        "az": "💵 Balansı artır",
        "kk": "💵 Балансты толтыру",
        "uz": "💵 Balansi to'ldirish",
        "mn": "💵 Үлдэгдэл нэмэх",
        "sw": "💵 Ongeza salio",
        "am": "💵 ሒሳብ ይሙሉ",
        "hi": "💵 बैलेंस रिचार्ज करें",
        "bn": "💵 ব্যালেন্স রিচার্জ করুন",
        "ur": "💵 بیلنس بڑھائیں",
        "id": "💵 Isi saldo",
        "ms": "💵 Tambah baki",
        "th": "💵 เติมเงินคงเหลือ",
        "vi": "💵 Nạp số dư",
        "bg": "💵 Зареди баланс",
        "hr": "💵 Napuni saldo",
        "sr": "💵 Напуни стање",
        "cs": "💵 Dobít kredit",
        "sk": "💵 Dobiť kredit",
        "ro": "💵 Reîncarcă soldul",
        "hu": "💵 Egyenleg feltöltése",
        "ha": "💵 Ƙara ma'auni",
    },

    # ── balance callback popup ────────────────────────────────────────────────
    "balance_callback": {
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
        "nl": "💰 Saldo: ${amount}",
        "sv": "💰 Saldo: ${amount}",
        "no": "💰 Saldo: ${amount}",
        "da": "💰 Saldo: ${amount}",
        "fi": "💰 Saldo: ${amount}",
        "he": "💰 יתרה: ${amount}",
        "ka": "💰 ბალანსი: ${amount}",
        "hy": "💰 Մնացորդ: ${amount}",
        "az": "💰 Balans: ${amount}",
        "kk": "💰 Баланс: ${amount}",
        "uz": "💰 Balans: ${amount}",
        "mn": "💰 Үлдэгдэл: ${amount}",
        "sw": "💰 Salio: ${amount}",
        "am": "💰 ሒሳብ: ${amount}",
        "hi": "💰 बैलेंस: ${amount}",
        "bn": "💰 ব্যালেন্স: ${amount}",
        "ur": "💰 بیلنس: ${amount}",
        "id": "💰 Saldo: ${amount}",
        "ms": "💰 Baki: ${amount}",
        "th": "💰 ยอดคงเหลือ: ${amount}",
        "vi": "💰 Số dư: ${amount}",
        "bg": "💰 Баланс: ${amount}",
        "hr": "💰 Saldo: ${amount}",
        "sr": "💰 Стање: ${amount}",
        "cs": "💰 Zůstatek: ${amount}",
        "sk": "💰 Zostatok: ${amount}",
        "ro": "💰 Sold: ${amount}",
        "hu": "💰 Egyenleg: ${amount}",
        "ha": "💰 Ma'auni: ${amount}",
    },

    # ── Maps: geocode coordinate label ────────────────────────────────────────
    "maps_coord_label": {
        "en": "📍 *${name}*\nCoordinates: ${lat}, ${lon}",
        "ru": "📍 *${name}*\nКоординаты: ${lat}, ${lon}",
        "de": "📍 *${name}*\nKoordinaten: ${lat}, ${lon}",
        "fr": "📍 *${name}*\nCoordonnées : ${lat}, ${lon}",
        "es": "📍 *${name}*\nCoordenadas: ${lat}, ${lon}",
        "pt": "📍 *${name}*\nCoordenadas: ${lat}, ${lon}",
        "it": "📍 *${name}*\nCoordinate: ${lat}, ${lon}",
        "tr": "📍 *${name}*\nKoordinatlar: ${lat}, ${lon}",
        "ar": "📍 *${name}*\nالإحداثيات: ${lat}, ${lon}",
        "zh": "📍 *${name}*\n坐标：${lat}, ${lon}",
        "ja": "📍 *${name}*\n座標：${lat}, ${lon}",
        "ko": "📍 *${name}*\n좌표: ${lat}, ${lon}",
        "pl": "📍 *${name}*\nWspółrzędne: ${lat}, ${lon}",
        "uk": "📍 *${name}*\nКоординати: ${lat}, ${lon}",
        "nl": "📍 *${name}*\nCoördinaten: ${lat}, ${lon}",
        "sv": "📍 *${name}*\nKoordinater: ${lat}, ${lon}",
        "da": "📍 *${name}*\nKoordinater: ${lat}, ${lon}",
        "fi": "📍 *${name}*\nKoordinaatit: ${lat}, ${lon}",
        "cs": "📍 *${name}*\nSouřadnice: ${lat}, ${lon}",
        "ro": "📍 *${name}*\nCoordonate: ${lat}, ${lon}",
        "hu": "📍 *${name}*\nKoordináták: ${lat}, ${lon}",
        "he": "📍 *${name}*\nקואורדינטות: ${lat}, ${lon}",
        "vi": "📍 *${name}*\nTọa độ: ${lat}, ${lon}",
        "th": "📍 *${name}*\nพิกัด: ${lat}, ${lon}",
        "id": "📍 *${name}*\nKoordinat: ${lat}, ${lon}",
        "ms": "📍 *${name}*\nKoordinat: ${lat}, ${lon}",
        "ka": "📍 *${name}*\nკოორდინატები: ${lat}, ${lon}",
        "hy": "📍 *${name}*\nՀամակարգային կոորդինատներ: ${lat}, ${lon}",
        "az": "📍 *${name}*\nKoordinatlar: ${lat}, ${lon}",
        "kk": "📍 *${name}*\nКоординаттар: ${lat}, ${lon}",
        "uz": "📍 *${name}*\nKoordinatalar: ${lat}, ${lon}",
        "hi": "📍 *${name}*\nनिर्देशांक: ${lat}, ${lon}",
        "bn": "📍 *${name}*\nনির্দেশাঙ্ক: ${lat}, ${lon}",
        "ur": "📍 *${name}*\nنقاط: ${lat}, ${lon}",
        "fa": "📍 *${name}*\nمختصات: ${lat}, ${lon}",
        "mn": "📍 *${name}*\nКоординат: ${lat}, ${lon}",
        "sw": "📍 *${name}*\nUratibu: ${lat}, ${lon}",
    },

    # ── Maps: location not found ───────────────────────────────────────────────
    "maps_not_found": {
        "en": "📍 Location not found. Try a more specific name.",
        "ru": "📍 Место не найдено. Попробуйте уточнить название.",
        "de": "📍 Ort nicht gefunden. Versuche einen genaueren Namen.",
        "fr": "📍 Lieu introuvable. Essayez un nom plus précis.",
        "es": "📍 Lugar no encontrado. Intenta con un nombre más específico.",
        "pt": "📍 Local não encontrado. Tente um nome mais específico.",
        "it": "📍 Luogo non trovato. Prova con un nome più specifico.",
        "tr": "📍 Konum bulunamadı. Daha spesifik bir isim deneyin.",
        "ar": "📍 الموقع غير موجود. جرّب اسماً أكثر تحديداً.",
        "zh": "📍 未找到该位置。请尝试更具体的名称。",
        "ja": "📍 場所が見つかりませんでした。より具体的な名前を試してください。",
        "ko": "📍 위치를 찾을 수 없습니다. 더 구체적인 이름을 시도해보세요.",
        "pl": "📍 Nie znaleziono miejsca. Spróbuj bardziej precyzyjnej nazwy.",
        "uk": "📍 Місце не знайдено. Спробуйте уточнити назву.",
        "nl": "📍 Locatie niet gevonden. Probeer een specifiekere naam.",
        "sv": "📍 Platsen hittades inte. Försök med ett mer specifikt namn.",
        "da": "📍 Stedet ikke fundet. Prøv et mere specifikt navn.",
        "fi": "📍 Paikkaa ei löydy. Kokeile tarkempaa nimeä.",
        "cs": "📍 Místo nenalezeno. Zkuste konkrétnější název.",
        "ro": "📍 Locul nu a fost găsit. Încercați un nume mai specific.",
        "hu": "📍 A hely nem található. Próbáljon pontosabb nevet.",
        "he": "📍 המיקום לא נמצא. נסה שם ספציפי יותר.",
        "vi": "📍 Không tìm thấy địa điểm. Thử tên cụ thể hơn.",
        "th": "📍 ไม่พบสถานที่ ลองใช้ชื่อที่เจาะจงกว่านี้",
        "id": "📍 Lokasi tidak ditemukan. Coba nama yang lebih spesifik.",
        "ms": "📍 Lokasi tidak dijumpai. Cuba nama yang lebih spesifik.",
        "ka": "📍 ადგილი ვერ მოიძებნა. სცადეთ უფრო კონკრეტული სახელი.",
        "hy": "📍 Վայрը չի գտնвел: Փорձеք ավелی կоնкреտ անун:",
        "az": "📍 Yer tapılmadı. Daha konkret ad sınayın.",
        "kk": "📍 Орын табылмады. Нақтырақ атауды қолданып көріңіз.",
        "uz": "📍 Joy topilmadi. Aniqroq nom bilan sinab ko'ring.",
        "hi": "📍 स्थान नहीं मिला। अधिक विशिष्ट नाम आज़माएं।",
        "fa": "📍 مکان پیدا نشد. نام دقیق‌تری امتحان کنید.",
        "mn": "📍 Байршил олдсонгүй. Илүү тодорхой нэр ашиглана уу.",
    },

    # ── Maps: POI not found ────────────────────────────────────────────────────
    "maps_poi_not_found": {
        "en": "📍 No ${category} found near ${location}. Try a different area or category.",
        "ru": "📍 Рядом с ${location} не найдено: ${category}. Попробуйте другой район или категорию.",
        "de": "📍 Kein ${category} in der Nähe von ${location} gefunden.",
        "fr": "📍 Aucun ${category} trouvé près de ${location}.",
        "es": "📍 No se encontró ${category} cerca de ${location}.",
        "pt": "📍 Nenhum ${category} encontrado perto de ${location}.",
        "it": "📍 Nessun ${category} trovato vicino a ${location}.",
        "tr": "📍 ${location} yakınında ${category} bulunamadı.",
        "ar": "📍 لا يوجد ${category} بالقرب من ${location}.",
        "zh": "📍 在${location}附近未找到${category}。",
        "ja": "📍 ${location}の近くに${category}が見つかりませんでした。",
        "ko": "📍 ${location} 근처에서 ${category}을(를) 찾을 수 없습니다.",
        "pl": "📍 Nie znaleziono ${category} w pobliżu ${location}.",
        "uk": "📍 Поряд з ${location} не знайдено: ${category}.",
        "ka": "📍 ${location}-ის მახლობლად ${category} ვერ მოიძებნა.",
        "hy": "📍 ${location}-ի մоտ ${category} չи гտнвел:",
        "nl": "📍 Geen ${category} gevonden bij ${location}.",
        "sv": "📍 Ingen ${category} hittades nära ${location}.",
        "fi": "📍 Ei ${category} löytynyt läheltä ${location}.",
        "he": "📍 לא נמצא ${category} ליד ${location}.",
        "hi": "📍 ${location} के पास ${category} नहीं मिला।",
        "fa": "📍 هیچ ${category} نزدیک ${location} یافت نشد.",
        "az": "📍 ${location} yaxınlığında ${category} tapılmadı.",
        "kk": "📍 ${location} маңында ${category} табылмады.",
        "uz": "📍 ${location} yaqinida ${category} topilmadi.",
        "id": "📍 Tidak ada ${category} ditemukan di dekat ${location}.",
        "ms": "📍 Tiada ${category} dijumpai berhampiran ${location}.",
        "th": "📍 ไม่พบ ${category} ใกล้ ${location}",
    },

    # ── Maps: POI result ───────────────────────────────────────────────────────
    "maps_poi_result": {
        "en": "📍 *${name}*\n${address}\nCoordinates: ${lat}, ${lon}",
        "ru": "📍 *${name}*\n${address}\nКоординаты: ${lat}, ${lon}",
        "de": "📍 *${name}*\n${address}\nKoordinaten: ${lat}, ${lon}",
        "fr": "📍 *${name}*\n${address}\nCoordonnées : ${lat}, ${lon}",
        "es": "📍 *${name}*\n${address}\nCoordenadas: ${lat}, ${lon}",
        "pt": "📍 *${name}*\n${address}\nCoordenadas: ${lat}, ${lon}",
        "it": "📍 *${name}*\n${address}\nCoordinate: ${lat}, ${lon}",
        "tr": "📍 *${name}*\n${address}\nKoordinatlar: ${lat}, ${lon}",
        "ar": "📍 *${name}*\n${address}\nالإحداثيات: ${lat}, ${lon}",
        "zh": "📍 *${name}*\n${address}\n坐标：${lat}, ${lon}",
        "ja": "📍 *${name}*\n${address}\n座標：${lat}, ${lon}",
        "ko": "📍 *${name}*\n${address}\n좌표: ${lat}, ${lon}",
        "pl": "📍 *${name}*\n${address}\nWspółrzędne: ${lat}, ${lon}",
        "uk": "📍 *${name}*\n${address}\nКоординати: ${lat}, ${lon}",
        "nl": "📍 *${name}*\n${address}\nCoördinaten: ${lat}, ${lon}",
        "sv": "📍 *${name}*\n${address}\nKoordinater: ${lat}, ${lon}",
        "da": "📍 *${name}*\n${address}\nKoordinater: ${lat}, ${lon}",
        "fi": "📍 *${name}*\n${address}\nKoordinaatit: ${lat}, ${lon}",
        "cs": "📍 *${name}*\n${address}\nSouřadnice: ${lat}, ${lon}",
        "ro": "📍 *${name}*\n${address}\nCoordonate: ${lat}, ${lon}",
        "hu": "📍 *${name}*\n${address}\nKoordináták: ${lat}, ${lon}",
        "he": "📍 *${name}*\n${address}\nקואורדינטות: ${lat}, ${lon}",
        "vi": "📍 *${name}*\n${address}\nTọa độ: ${lat}, ${lon}",
        "th": "📍 *${name}*\n${address}\nพิกัด: ${lat}, ${lon}",
        "id": "📍 *${name}*\n${address}\nKoordinat: ${lat}, ${lon}",
        "ms": "📍 *${name}*\n${address}\nKoordinat: ${lat}, ${lon}",
        "ka": "📍 *${name}*\n${address}\nკოორდინატები: ${lat}, ${lon}",
        "hy": "📍 *${name}*\n${address}\nՀամакаргайин кооردинатнер: ${lat}, ${lon}",
        "az": "📍 *${name}*\n${address}\nKoordinatlar: ${lat}, ${lon}",
        "kk": "📍 *${name}*\n${address}\nКоординаттар: ${lat}, ${lon}",
        "uz": "📍 *${name}*\n${address}\nKoordinatalar: ${lat}, ${lon}",
        "hi": "📍 *${name}*\n${address}\nनिर्देशांक: ${lat}, ${lon}",
        "fa": "📍 *${name}*\n${address}\nمختصات: ${lat}, ${lon}",
        "mn": "📍 *${name}*\n${address}\nКоординат: ${lat}, ${lon}",
        "sw": "📍 *${name}*\n${address}\nUratibu: ${lat}, ${lon}",
    },

    # ── Maps: route result ─────────────────────────────────────────────────────
    "maps_route_result": {
        "en": "🗺 Route: ${origin} → ${destination}\n📏 Distance: ${dist} km\n⏱ Drive time: ~${dur} min",
        "ru": "🗺 Маршрут: ${origin} → ${destination}\n📏 Расстояние: ${dist} км\n⏱ Время в пути: ~${dur} мин",
        "de": "🗺 Route: ${origin} → ${destination}\n📏 Entfernung: ${dist} km\n⏱ Fahrzeit: ~${dur} Min.",
        "fr": "🗺 Itinéraire: ${origin} → ${destination}\n📏 Distance: ${dist} km\n⏱ Durée: ~${dur} min",
        "es": "🗺 Ruta: ${origin} → ${destination}\n📏 Distancia: ${dist} km\n⏱ Tiempo: ~${dur} min",
        "pt": "🗺 Rota: ${origin} → ${destination}\n📏 Distância: ${dist} km\n⏱ Tempo: ~${dur} min",
        "it": "🗺 Percorso: ${origin} → ${destination}\n📏 Distanza: ${dist} km\n⏱ Durata: ~${dur} min",
        "tr": "🗺 Güzergah: ${origin} → ${destination}\n📏 Mesafe: ${dist} km\n⏱ Süre: ~${dur} dak",
        "ar": "🗺 المسار: ${origin} → ${destination}\n📏 المسافة: ${dist} كم\n⏱ وقت القيادة: ~${dur} دقيقة",
        "zh": "🗺 路线：${origin} → ${destination}\n📏 距离：${dist} 公里\n⏱ 行驶时间：约 ${dur} 分钟",
        "ja": "🗺 ルート：${origin} → ${destination}\n📏 距離：${dist} km\n⏱ 所要時間：約 ${dur} 分",
        "ko": "🗺 경로: ${origin} → ${destination}\n📏 거리: ${dist} km\n⏱ 이동 시간: 약 ${dur}분",
        "pl": "🗺 Trasa: ${origin} → ${destination}\n📏 Odległość: ${dist} km\n⏱ Czas jazdy: ~${dur} min",
        "uk": "🗺 Маршрут: ${origin} → ${destination}\n📏 Відстань: ${dist} км\n⏱ Час у дорозі: ~${dur} хв",
        "nl": "🗺 Route: ${origin} → ${destination}\n📏 Afstand: ${dist} km\n⏱ Rijtijd: ~${dur} min",
        "sv": "🗺 Rutt: ${origin} → ${destination}\n📏 Avstånd: ${dist} km\n⏱ Körtid: ~${dur} min",
        "fi": "🗺 Reitti: ${origin} → ${destination}\n📏 Etäisyys: ${dist} km\n⏱ Ajoaika: ~${dur} min",
        "he": "🗺 מסלול: ${origin} → ${destination}\n📏 מרחק: ${dist} ק\"מ\n⏱ זמן נסיעה: ~${dur} דקות",
        "ka": "🗺 მარშრუტი: ${origin} → ${destination}\n📏 მანძილი: ${dist} კმ\n⏱ გზაში: ~${dur} წთ",
        "hy": "🗺 Երթուղի: ${origin} → ${destination}\n📏 Հեռավورություн: ${dist} կм\n⏱ Ճанапархازгайин ժаманак: ~${dur} рոп",
        "az": "🗺 Marşrut: ${origin} → ${destination}\n📏 Məsafə: ${dist} km\n⏱ Yol vaxtı: ~${dur} dəq",
        "kk": "🗺 Бағыт: ${origin} → ${destination}\n📏 Қашықтық: ${dist} км\n⏱ Жол уақыты: ~${dur} мин",
        "uz": "🗺 Marshrut: ${origin} → ${destination}\n📏 Masofa: ${dist} km\n⏱ Yo'l vaqti: ~${dur} daq",
        "fa": "🗺 مسیر: ${origin} → ${destination}\n📏 فاصله: ${dist} کیلومتر\n⏱ زمان رانندگی: ~${dur} دقیقه",
        "hi": "🗺 मार्ग: ${origin} → ${destination}\n📏 दूरी: ${dist} किमी\n⏱ ड्राइव समय: ~${dur} मिनट",
        "mn": "🗺 Чиглэл: ${origin} → ${destination}\n📏 Зай: ${dist} км\n⏱ Явах хугацаа: ~${dur} мин",
    },

    # ── Maps: route not found ──────────────────────────────────────────────────
    "maps_route_not_found": {
        "en": "🗺 Could not build a route. Check that both locations are correct.",
        "ru": "🗺 Не удалось построить маршрут. Уточните названия мест.",
        "de": "🗺 Route konnte nicht berechnet werden. Bitte Orte prüfen.",
        "fr": "🗺 Impossible de calculer l'itinéraire. Vérifiez les lieux.",
        "es": "🗺 No se pudo calcular la ruta. Comprueba los lugares.",
        "pt": "🗺 Não foi possível calcular a rota. Verifique os locais.",
        "it": "🗺 Impossibile calcolare il percorso. Controlla i luoghi.",
        "tr": "🗺 Güzergah oluşturulamadı. Lütfen yerleri kontrol edin.",
        "ar": "🗺 تعذّر بناء المسار. تحقق من صحة الموقعين.",
        "zh": "🗺 无法构建路线。请检查两个地点是否正确。",
        "ja": "🗺 ルートを構築できませんでした。両方の場所を確認してください。",
        "ko": "🗺 경로를 만들 수 없습니다. 두 위치를 확인해주세요.",
        "pl": "🗺 Nie udało się obliczyć trasy. Sprawdź nazwy miejsc.",
        "uk": "🗺 Не вдалося побудувати маршрут. Уточніть назви місць.",
        "nl": "🗺 Kon geen route berekenen. Controleer beide locaties.",
        "sv": "🗺 Kunde inte bygga rutten. Kontrollera båda platserna.",
        "fi": "🗺 Reittiä ei voitu rakentaa. Tarkista molemmat paikat.",
        "he": "🗺 לא ניתן לבנות מסלול. בדוק שני המיקומים.",
        "ka": "🗺 მარשრუტის აგება ვერ მოხერხდა. შეამოწმეთ ორივე ადგილი.",
        "az": "🗺 Marşrut qurula bilmədi. Hər iki yeri yoxlayın.",
        "kk": "🗺 Бағытты құру мүмкін болмады. Екі орынды да тексеріңіз.",
        "uz": "🗺 Marshrut qurib bo'lmadi. Ikkala joyni ham tekshiring.",
        "fa": "🗺 مسیر ساخته نشد. هر دو مکان را بررسی کنید.",
        "hi": "🗺 मार्ग नहीं बन सका। दोनों स्थान जाँचें।",
        "mn": "🗺 Чиглэл байгуулж чадсангүй. Хоёр байршлыг шалгана уу.",
    },

    # ── Payments: top-up button label ─────────────────────────────────────────
    "topup_button": {
        "en": "💳 Top Up Balance",
        "ru": "💳 Пополнить баланс",
        "de": "💳 Guthaben aufladen",
        "fr": "💳 Recharger le solde",
        "es": "💳 Recargar saldo",
        "pt": "💳 Recarregar saldo",
        "it": "💳 Ricarica saldo",
        "tr": "💳 Bakiye yükle",
        "ar": "💳 إعادة شحن الرصيد",
        "zh": "💳 充值",
        "ja": "💳 残高チャージ",
        "ko": "💳 잔액 충전",
        "pl": "💳 Doładuj saldo",
        "uk": "💳 Поповнити баланс",
        "ka": "💳 ბალანსის შევსება",
    },

    # ── Payments: low balance warning ─────────────────────────────────────────
    "low_balance_warning": {
        "en": "⚠️ Your balance is running low. Top up to keep chatting.",
        "ru": "⚠️ Баланс заканчивается. Пополните, чтобы продолжить.",
        "de": "⚠️ Dein Guthaben wird knapp. Lade es auf, um weiterzumachen.",
        "fr": "⚠️ Votre solde est faible. Rechargez pour continuer.",
        "es": "⚠️ Tu saldo es bajo. Recarga para seguir chateando.",
        "pt": "⚠️ Seu saldo está baixo. Recarregue para continuar.",
        "it": "⚠️ Il tuo saldo è basso. Ricarica per continuare.",
        "tr": "⚠️ Bakiyeniz azalıyor. Devam etmek için yükleyin.",
        "ar": "⚠️ رصيدك على وشك النفاد. أعد الشحن للمتابعة.",
        "zh": "⚠️ 余额不足，请充值以继续使用。",
        "ja": "⚠️ 残高が少なくなっています。チャットを続けるにはチャージしてください。",
        "ko": "⚠️ 잔액이 부족합니다. 계속하려면 충전하세요.",
        "pl": "⚠️ Twoje saldo jest niskie. Doładuj, aby kontynuować.",
        "uk": "⚠️ Баланс закінчується. Поповніть, щоб продовжити.",
        "ka": "⚠️ ბალანსი ამოიწურება. გასაგრძელებლად შეავსეთ.",
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
    lang = lang.lower().strip()
    name = _LANG_ALIASES.get(lang, lang)
    return f"Always answer in {name}. If unclear — default to English."


def ow_lang(lang: str) -> str:
    return OW_LANG_MAP.get(lang, "en")


def is_supported(lang: str) -> bool:
    return lang in SUPPORTED_LANGS


def normalize_lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"