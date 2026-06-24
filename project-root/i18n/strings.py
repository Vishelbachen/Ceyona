# This script builds the new strings.py with Ceyona persona applied to all system messages.
# Rules per persona.md:
# - No "⚠️ noun. Please try again." template. Errors acknowledged briefly, without panic.
# - P3: short is correct. Don't fill silence.
# - P6: boundary without explanation.
# - P2: one soft offer, not repeated.
# - ⚠️ kept ONLY for hard blockers (insufficient_balance, safety_block, memory_reset_confirm).
#   Everything else: plain, direct, warm where warranted.
# - Russian/Ukrainian: feminine verb forms where applicable.
# - All languages get the same voice, not just ru.

content = from __future__ import annotations

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
    "pl": "odczuwalna",         "uk": "відчувається як",     "fa": "احساس می\\u200cشود",
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
# Persona note (persona.md §1):
# P3 — silence as tool: short answers are correct, not cold.
# P6 — boundary without explanation: one line, no apology.
# P2 — care shown once, gently.
# ⚠️ reserved for hard blockers only (balance, safety, irreversible actions).
# Russian/Ukrainian: feminine verb forms throughout.

_STRINGS: dict[str, dict[str, str]] = {

    # ── weather labels ────────────────────────────────────────────────────────
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
        "en": "⚠️ *Not enough balance.*\\n\\nTap the button below — you\'ll see the wallet address and your payment ID.",
        "ru": "⚠️ *Недостаточно средств.*\\n\\nНажми кнопку ниже — там адрес кошелька и твой личный ID платежа.",
        "de": "⚠️ *Guthaben reicht nicht aus.*\\n\\nTippe auf die Schaltfläche unten — du siehst die Wallet-Adresse und deine Zahlungs-ID.",
        "fr": "⚠️ *Solde insuffisant.*\\n\\nAppuie sur le bouton ci-dessous — tu verras l\'adresse du portefeuille et ton ID de paiement.",
        "es": "⚠️ *Saldo insuficiente.*\\n\\nPulsa el botón — verás la dirección de la cartera y tu ID de pago.",
        "pt": "⚠️ *Saldo insuficiente.*\\n\\nToca no botão abaixo — verás o endereço da carteira e o teu ID de pagamento.",
        "it": "⚠️ *Saldo insufficiente.*\\n\\nPremi il pulsante in basso — vedrai l\'indirizzo del wallet e il tuo ID di pagamento.",
        "tr": "⚠️ *Bakiye yetersiz.*\\n\\nAşağıdaki düğmeye dokun — cüzdan adresini ve ödeme kimliğini göreceksin.",
        "ar": "⚠️ *رصيد غير كافٍ.*\\n\\nاضغط على الزر أدناه — ستجد عنوان المحفظة ومعرّف الدفع.",
        "zh": "⚠️ *余额不足。*\\n\\n点击下方按钮——你将看到钱包地址和支付ID。",
        "ja": "⚠️ *残高不足です。*\\n\\n下のボタンをタップ — ウォレットアドレスと支払いIDが表示されます。",
        "ko": "⚠️ *잔액이 부족합니다.*\\n\\n아래 버튼을 탭하세요 — 지갑 주소와 결제 ID가 표시됩니다.",
        "pl": "⚠️ *Niewystarczające środki.*\\n\\nKliknij przycisk poniżej — zobaczysz adres portfela i swoje ID płatności.",
        "uk": "⚠️ *Недостатньо коштів.*\\n\\nНатисни кнопку нижче — там буде адреса гаманця та твій ID платежу.",
        "fa": "⚠️ *موجودی کافی نیست.*\\n\\nروی دکمه زیر ضربه بزن — آدرس کیف پول و شناسه پرداختت را خواهی دید.",
        "nl": "⚠️ *Saldo onvoldoende.*\\n\\nTik op de knop hieronder — je ziet het walletadres en je betalings-ID.",
        "sv": "⚠️ *Saldot räcker inte.*\\n\\nTryck på knappen nedan — du ser plånboksadressen och ditt betalnings-ID.",
        "no": "⚠️ *Saldoen er ikke nok.*\\n\\nTrykk på knappen nedenfor — du vil se lommebokadresse og betalings-ID.",
        "da": "⚠️ *Saldoen er ikke nok.*\\n\\nTryk på knappen nedenfor — du vil se wallet-adressen og dit betalings-ID.",
        "fi": "⚠️ *Saldo ei riitä.*\\n\\nNapauta alla olevaa painiketta — näet lompakko-osoitteen ja maksu-ID:si.",
        "he": "⚠️ *יתרה לא מספיקה.*\\n\\nלחץ על הכפתור למטה — תראה את כתובת הארנק ומזהה התשלום.",
        "hi": "⚠️ *बैलेंस कम है।*\\n\\nनीचे बटन दबाएं — वॉलेट पता और भुगतान ID दिखाई देगा।",
        "id": "⚠️ *Saldo tidak cukup.*\\n\\nKetuk tombol di bawah — kamu akan melihat alamat dompet dan ID pembayaran.",
        "az": "⚠️ *Balans kifayət deyil.*\\n\\nAşağıdakı düyməyə toxunun — cüzdan ünvanını və ödəniş ID-nizi görəcəksiniz.",
        "kk": "⚠️ *Баланс жеткіліксіз.*\\n\\nТөмендегі түймені басыңыз — әмиян мекенжайын және төлем ID-іңізді көресіз.",
        "uz": "⚠️ *Balans yetarli emas.*\\n\\nQuyidagi tugmani bosing — hamyon manzili va to\'lov ID'ingizni ko\'rasiz.",
        "ka": "⚠️ *ბალანსი არ კმარა.*\\n\\nდააჭირე ქვემოთ ღილაკს — დაინახავ საფულის მისამართს და გადახდის ID-ს.",
        "hy": "⚠️ *Բավարար մնacорд չka.*\\n\\nՍеղмеք ստорев կոճакը — կтесնеք драмапанакի хасцен у ձер վчарайин ID-ն:",
        "cs": "⚠️ *Nedostatečný zůstatek.*\\n\\nKlikněte na tlačítko níže — uvidíte adresu peněženky a své platební ID.",
        "ro": "⚠️ *Sold insuficient.*\\n\\nApasă butonul de mai jos — vei vedea adresa portofelului și ID-ul de plată.",
        "hu": "⚠️ *Nem elég az egyenleg.*\\n\\nKoppintson az alábbi gombra — látni fogja a pénztárca-címet és a fizetési azonosítóját.",
        "th": "⚠️ *ยอดคงเหลือไม่พอ*\\n\\nแตะปุ่มด้านล่าง — จะเห็นที่อยู่กระเป๋าเงินและ ID ชำระเงิน",
        "vi": "⚠️ *Số dư không đủ.*\\n\\nNhấn nút bên dưới — bạn sẽ thấy địa chỉ ví và ID thanh toán.",
        "ms": "⚠️ *Baki tidak mencukupi.*\\n\\nKetik butang di bawah — anda akan melihat alamat dompet dan ID pembayaran.",
        "bn": "⚠️ *ব্যালেন্স যথেষ্ট নয়।*\\n\\nনিচের বোতামটি ট্যাপ করুন — ওয়ালেটের ঠিকানা এবং পেমেন্ট ID দেখতে পাবেন।",
        "ur": "⚠️ *بیلنس ناکافی ہے۔*\\n\\nنیچے بٹن دبائیں — والیٹ ایڈریس اور پیمنٹ ID نظر آئے گا۔",
        "bg": "⚠️ *Балансът не е достатъчен.*\\n\\nНатиснете бутона по-долу — ще видите адреса на портфейла и ID за плащане.",
        "hr": "⚠️ *Saldo nije dovoljan.*\\n\\nPritisnite gumb ispod — vidjet ćete adresu novčanika i ID plaćanja.",
        "sr": "⚠️ *Сaldо није довољно.*\\n\\nПритисните дугме испод — видећете адресу новчаника и ID за плаћање.",
        "sk": "⚠️ *Zostatok nestačí.*\\n\\nKliknite na tlačidlo nižšie — uvidíte adresu peňaženky a platobné ID.",
        "mn": "⚠️ *Үлдэгдэл хүрэлцэхгүй.*\\n\\nДоорх товчийг дарна уу — хэтэвчний хаяг болон төлбөрийн ID-г харах болно.",
    },

    # ── no LLM response received ──────────────────────────────────────────────
    # P3: short. P6: no apology. Just one try-again nudge.
    "no_response": {
        "en": "Something went wrong on my end. Try again?",
        "ru": "Что-то пошло не так. Попробуешь ещё раз?",
        "de": "Etwas ist schiefgelaufen. Nochmal versuchen?",
        "fr": "Quelque chose a mal tourné. Réessaie ?",
        "es": "Algo salió mal. ¿Intentas de nuevo?",
        "pt": "Algo correu mal. Tentas outra vez?",
        "it": "Qualcosa è andato storto. Riprovi?",
        "tr": "Bir şeyler ters gitti. Tekrar dener misin?",
        "ar": "حدث خطأ ما. هل تحاول مرة أخرى؟",
        "zh": "出了点问题，再试一次？",
        "ja": "うまくいかなかった。もう一度試してみて。",
        "ko": "뭔가 잘못됐어요. 다시 시도해볼까요?",
        "pl": "Coś poszło nie tak. Spróbujesz jeszcze raz?",
        "uk": "Щось пішло не так. Спробуєш ще раз?",
        "fa": "مشکلی پیش آمد. دوباره امتحان می‌کنی؟",
        "nl": "Er ging iets mis. Nog een keer proberen?",
        "sv": "Något gick fel. Försök igen?",
        "no": "Noe gikk galt. Prøv igjen?",
        "da": "Noget gik galt. Prøv igen?",
        "fi": "Jokin meni pieleen. Kokeile uudelleen?",
        "he": "משהו השתבש. לנסות שוב?",
        "hi": "कुछ गड़बड़ हो गई। फिर कोशिश करें?",
        "id": "Terjadi kesalahan. Coba lagi?",
        "az": "Bir şey düzgün getmədi. Yenidən cəhd edərsiniz?",
        "kk": "Бірдеңе дұрыс болмады. Қайталап көресіз бе?",
        "uz": "Nimadir noto\'g\'ri ketdi. Qayta urinib ko\'rasizmi?",
        "ka": "რაღაც არ გამოვიდა. კვლავ სცდი?",
        "hy": "Ինчор stvats sxal: Կрկин փоргел?",
        "mn": "Ямар нэг зүйл буруу боллоо. Дахин оролдох уу?",
    },

    # ── VAD: audio was silent — user pressed PTT without speaking ─────────────
    # P3: silence as tool — she asks once, simply. No ⚠️.
    # P2: soft, one beat. Russian/Ukrainian: feminine forms.
    "vad_silence": {
        "en": "Didn\'t catch that — was it silent? 🎤",
        "ru": "Не расслышала — кажется, ничего не записалось. Попробуешь ещё раз?",
        "de": "Ich habe nichts gehört — war das leer? 🎤",
        "fr": "Je n\'ai rien capté — c\'était silencieux ? 🎤",
        "es": "No capté nada — ¿el mensaje estaba vacío? 🎤",
        "pt": "Não captei nada — estava silencioso? 🎤",
        "it": "Non ho sentito niente — era silenzioso? 🎤",
        "tr": "Hiçbir şey duymadım — sessiz miydi? 🎤",
        "ar": "لم أسمع شيئاً — هل كان صامتاً؟ 🎤",
        "zh": "没听到 — 录音是空的吗？🎤",
        "ja": "聞こえなかった — 録音が空だったかな。🎤",
        "ko": "아무것도 안 들렸어 — 녹음이 비어 있었나요? 🎤",
        "pl": "Nic nie usłyszałam — wiadomość była cicha? 🎤",
        "uk": "Не розчула — здається, нічого не записалось. Спробуєш ще раз?",
        "fa": "چیزی نشنیدم — آیا پیام خالی بود؟ 🎤",
        "nl": "Heb niets gehoord — was het stil? 🎤",
        "sv": "Hörde inget — var det tyst? 🎤",
        "no": "Hørte ingenting — var det stille? 🎤",
        "da": "Hørte intet — var det stille? 🎤",
        "fi": "En kuullut mitään — oliko se hiljainen? 🎤",
        "he": "לא שמעתי כלום — האם הייתה שקט? 🎤",
        "hi": "कुछ सुनाई नहीं दिया — क्या रिकॉर्डिंग खाली थी? 🎤",
        "id": "Tidak terdengar — apakah pesannya kosong? 🎤",
        "az": "Heç nə eşitmədim — mesaj boş idi? 🎤",
        "kk": "Ештеңе естімедім — жазба бос болды ма? 🎤",
        "uz": "Hech narsa eshitmadim — xabar bo\'shmi edi? 🎤",
        "ka": "ვერაფერი გავიგე — ჩანაწერი ცარიელი იყო? 🎤",
        "hy": "Vocinch chvm lsel — dzaynagrutyan datark er? 🎤",
        "mn": "Юу ч сонсогдсонгүй — бичлэг хоосон байсан уу? 🎤",
    },

    # ── No unsolicited code ───────────────────────────────────────────────────
    # P6: boundary, one line, no apology.
    "no_unsolicited_code": {
        "en": "I shouldn\'t show code here. Ask for code explicitly if you want an example.",
        "ru": "Здесь не должен быть код. Если нужен пример, попроси код явно.",
    },

    # ── clarification / missing-details prompts ───────────────────────────────
    # P5a: one question. P1: specific detail, not a form.
    "need_more_clues": {
        "en": "I need one or two more clues to identify this reliably. Tell me a scene, character, year, place, or feature you remember.",
        "ru": "Мне нужно ещё 1–2 зацепки, чтобы понять это надёжно. Назови сцену, персонажа, год, место или любую деталь, которую помнишь.",
    },
    "need_route_origin": {
        "en": "Which airport or starting point should I use? Tell me the airport name or code, and I\'ll build the route.",
        "ru": "Из какого аэропорта или точки старта строить маршрут? Напиши название или код аэропорта, и я соберу маршрут.",
    },
    "need_city_or_area": {
        "en": "Which city or area should I search in?",
        "ru": "В каком городе или районе искать?",
    },

    # ── generic deny ──────────────────────────────────────────────────────────
    # P3 + P6: short, no fuss, one nudge.
    "default_deny": {
        "en": "Couldn\'t process that one. Want to try rephrasing?",
        "ru": "Не получилось обработать запрос. Попробуешь переформулировать?",
        "de": "Konnte das nicht verarbeiten. Möchtest du es umformulieren?",
        "fr": "Je n\'ai pas pu traiter ça. Veux-tu reformuler ?",
        "es": "No pude procesar eso. ¿Quieres intentarlo de otra forma?",
        "pt": "Não consegui processar isso. Queres tentar de outra forma?",
        "it": "Non sono riuscita a elaborarlo. Vuoi riformulare?",
        "tr": "Bunu işleyemedim. Yeniden ifade etmek ister misin?",
        "ar": "لم أتمكن من معالجة ذلك. هل تريد إعادة الصياغة؟",
        "zh": "处理不了这个。换个说法试试？",
        "ja": "うまく処理できなかった。言い方を変えてみて。",
        "ko": "처리할 수 없었어요. 다르게 표현해볼까요?",
        "pl": "Nie mogłam przetworzyć tego. Chcesz spróbować inaczej?",
        "uk": "Не вдалось обробити запит. Спробуєш переформулювати?",
        "fa": "نتوانستم این را پردازش کنم. می‌خواهی دوباره بیان کنی؟",
        "nl": "Kon dat niet verwerken. Wil je het anders formuleren?",
        "sv": "Kunde inte behandla det. Vill du försöka omformulera?",
        "no": "Klarte ikke behandle det. Vil du prøve å omformulere?",
        "da": "Kunne ikke behandle det. Vil du prøve at omformulere?",
        "fi": "En pystynyt käsittelemään sitä. Haluatko yrittää toisin sanoin?",
        "he": "לא הצלחתי לעבד את זה. רוצה לנסח מחדש?",
        "hi": "इसे प्रोसेस नहीं कर पाई। दोबारा लिखकर देखें?",
        "id": "Tidak bisa memproses itu. Mau mencoba dengan kata-kata lain?",
        "az": "Bunu emal edə bilmədim. Yenidən ifadə etmək istərsiniz?",
        "kk": "Мұны өңдей алмадым. Қайта тұжырымдап көргіңіз келе ме?",
        "uz": "Buni qayta ishlolmadim. Boshqacha ifodalab ko\'rib ko\'rasizmi?",
        "ka": "ვერ დავამუშავე. გინდა სხვაგვარად ჩამოაყალიბო?",
        "hy": "Chkarhtsay sksel: Urish barov grel?",
        "mn": "Энийг боловсруулж чадсангүй. Өөрөөр найруулж үзэх үү?",
    },

    # ── safety block ──────────────────────────────────────────────────────────
    # P6: one line, no explanation, no apology. 🚫 kept — it is a hard stop.
    "safety_block": {
        "en": "🚫 That one I can\'t help with.",
        "ru": "🚫 Это не в моих силах.",
        "de": "🚫 Dabei kann ich nicht helfen.",
        "fr": "🚫 Je ne peux pas aider avec ça.",
        "es": "🚫 Eso no puedo hacerlo.",
        "pt": "🚫 Isso não consigo fazer.",
        "it": "🚫 Questo non posso farlo.",
        "tr": "🚫 Buna yardım edemem.",
        "ar": "🚫 هذا لا أستطيع المساعدة فيه.",
        "zh": "🚫 这个我帮不上。",
        "ja": "🚫 それはお手伝いできません。",
        "ko": "🚫 그건 도와드릴 수 없어요.",
        "pl": "🚫 Przy tym nie mogę pomóc.",
        "uk": "🚫 З цим не можу допомогти.",
        "fa": "🚫 با این نمی‌توانم کمک کنم.",
        "nl": "🚫 Daarmee kan ik niet helpen.",
        "sv": "🚫 Det kan jag inte hjälpa med.",
        "no": "🚫 Det kan jeg ikke hjelpe med.",
        "da": "🚫 Det kan jeg ikke hjælpe med.",
        "fi": "🚫 Siihen en pysty auttamaan.",
        "he": "🚫 עם זה אני לא יכולה לעזור.",
        "hi": "🚫 इसमें मदद नहीं कर सकती।",
        "id": "🚫 Itu tidak bisa saya bantu.",
        "az": "🚫 Buna kömək edə bilmərəm.",
        "kk": "🚫 Бұған көмектесе алмаймын.",
        "uz": "🚫 Bunga yordam bera olmayman.",
        "ka": "🚫 ამაში ვერ დავეხმარები.",
        "hy": "🚫 Dran chem karox ognel.",
        "mn": "🚫 Үүнд туслах боломжгүй.",
    },

    # ── rate limiting ─────────────────────────────────────────────────────────
    # P3: very short. No lecture.
    "rate_limited": {
        "en": "A little fast — give me a moment. ⏳",
        "ru": "Чуть помедленнее — дай мне секунду. ⏳",
        "de": "Etwas schnell — einen Moment. ⏳",
        "fr": "Un peu vite — une seconde. ⏳",
        "es": "Un poco rápido — dame un momento. ⏳",
        "pt": "Um pouco depressa — um momento. ⏳",
        "it": "Troppo veloce — un attimo. ⏳",
        "tr": "Biraz hızlı — bir saniye. ⏳",
        "ar": "سريع قليلاً — لحظة. ⏳",
        "zh": "稍快了一点，等一下。⏳",
        "ja": "少し速い — ちょっと待って。⏳",
        "ko": "조금 빠르네요 — 잠깐요. ⏳",
        "pl": "Trochę szybko — chwilkę. ⏳",
        "uk": "Трохи швидко — дай секунду. ⏳",
        "fa": "کمی سریع — یک لحظه. ⏳",
        "nl": "Iets te snel — even geduld. ⏳",
        "sv": "Lite fort — en sekund. ⏳",
        "no": "Litt raskt — et øyeblikk. ⏳",
        "da": "Lidt hurtigt — et øjeblik. ⏳",
        "fi": "Hiukan nopeaa — hetki. ⏳",
        "he": "קצת מהר — רגע. ⏳",
        "hi": "थोड़ा तेज़ — एक पल दो। ⏳",
        "id": "Agak cepat — sebentar. ⏳",
        "az": "Biraz sürətli — bir an. ⏳",
        "kk": "Сәл тез — бір секунд. ⏳",
        "uz": "Biroz tez — bir soniya. ⏳",
        "ka": "ცოტა სწრაფი — ერთი წამი. ⏳",
        "hy": "Mot arags — akh karag: ⏳",
        "mn": "Арай хурдан — нэг мөч. ⏳",
    },

    # ── truncation suffix ─────────────────────────────────────────────────────
    "truncation_suffix": {
        "en": "\\n\\n_…response truncated_",
        "ru": "\\n\\n_…ответ сокращён_",
        "de": "\\n\\n_…Antwort gekürzt_",
        "fr": "\\n\\n_…réponse tronquée_",
        "es": "\\n\\n_…respuesta truncada_",
        "pt": "\\n\\n_…resposta truncada_",
        "it": "\\n\\n_…risposta troncata_",
        "tr": "\\n\\n_…yanıt kısaltıldı_",
        "ar": "\\n\\n_…تم اقتصاص الرد_",
        "zh": "\\n\\n_…回复已截断_",
        "ja": "\\n\\n_…返答が省略されました_",
        "ko": "\\n\\n_…응답이 잘렸습니다_",
        "pl": "\\n\\n_…odpowiedź skrócona_",
        "uk": "\\n\\n_…відповідь скорочено_",
        "fa": "\\n\\n_…پاسخ کوتاه شد_",
        "nl": "\\n\\n_…antwoord afgekapt_",
        "sv": "\\n\\n_…svar avkortat_",
        "no": "\\n\\n_…svar avkortet_",
        "da": "\\n\\n_…svar afkortet_",
        "fi": "\\n\\n_…vastaus katkaistu_",
        "he": "\\n\\n_…התגובה קוצרה_",
        "hi": "\\n\\n_…प्रतिक्रिया काटी गई_",
        "id": "\\n\\n_…respons dipotong_",
        "az": "\\n\\n_…cavab qısaldıldı_",
        "kk": "\\n\\n_…жауап қысқартылды_",
        "uz": "\\n\\n_…javob qisqartirildi_",
        "ka": "\\n\\n_…პასუხი შეკვეცილია_",
        "hy": "\\n\\n_…pataskhanë krchatatvats e_",
        "mn": "\\n\\n_…хариу таслагдсан_",
    },

    # ── help text ─────────────────────────────────────────────────────────────
    # P7: functional context, functional tone. No "I am your AI assistant."
    "help_display": {
        "en": (
            "ℹ️ *Help*\\n\\n"
            "Ask me anything, send a voice message, or share a photo.\\n"
            "• /balance — check your balance\\n"
            "• /clear — clear conversation history\\n"
            "• /reset_memory — forget everything\\n\\n"
            "I reply in your language automatically."
        ),
        "ru": (
            "ℹ️ *Помощь*\\n\\n"
            "Можешь написать, отправить голосовое или фото.\\n"
            "• /balance — проверить баланс\\n"
            "• /clear — очистить историю диалога\\n"
            "• /reset_memory — удалить всю память\\n\\n"
            "Отвечаю на твоём языке автоматически."
        ),
        "de": (
            "ℹ️ *Hilfe*\\n\\n"
            "Stell mir Fragen, schick eine Sprachnachricht oder ein Foto.\\n"
            "• /balance — Guthaben prüfen\\n"
            "• /clear — Verlauf löschen\\n"
            "• /reset_memory — alles vergessen\\n\\n"
            "Ich antworte automatisch in deiner Sprache."
        ),
        "fr": (
            "ℹ️ *Aide*\\n\\n"
            "Pose-moi des questions, envoie un message vocal ou une photo.\\n"
            "• /balance — vérifier le solde\\n"
            "• /clear — effacer l\'historique\\n"
            "• /reset_memory — tout oublier\\n\\n"
            "Je réponds automatiquement dans ta langue."
        ),
        "es": (
            "ℹ️ *Ayuda*\\n\\n"
            "Pregúntame, envía un mensaje de voz o una foto.\\n"
            "• /balance — ver saldo\\n"
            "• /clear — borrar historial\\n"
            "• /reset_memory — olvidar todo\\n\\n"
            "Respondo en tu idioma automáticamente."
        ),
        "pt": (
            "ℹ️ *Ajuda*\\n\\n"
            "Pergunta-me, envia uma mensagem de voz ou uma foto.\\n"
            "• /balance — ver saldo\\n"
            "• /clear — limpar histórico\\n"
            "• /reset_memory — esquecer tudo\\n\\n"
            "Respondo no teu idioma automaticamente."
        ),
        "it": (
            "ℹ️ *Guida*\\n\\n"
            "Chiedimi qualsiasi cosa, invia un vocale o una foto.\\n"
            "• /balance — controlla il saldo\\n"
            "• /clear — cancella la cronologia\\n"
            "• /reset_memory — dimentica tutto\\n\\n"
            "Rispondo automaticamente nella tua lingua."
        ),
        "tr": (
            "ℹ️ *Yardım*\\n\\n"
            "Bana sor, sesli mesaj ya da fotoğraf gönder.\\n"
            "• /balance — bakiye görüntüle\\n"
            "• /clear — geçmişi sil\\n"
            "• /reset_memory — her şeyi unut\\n\\n"
            "Otomatik olarak dilinde yanıt veririm."
        ),
        "ar": (
            "ℹ️ *المساعدة*\\n\\n"
            "اسألني أي شيء، أرسل رسالة صوتية أو صورة.\\n"
            "• /balance — الاطلاع على الرصيد\\n"
            "• /clear — مسح المحادثة\\n"
            "• /reset_memory — نسيان كل شيء\\n\\n"
            "أرد تلقائياً بلغتك."
        ),
        "zh": (
            "ℹ️ *帮助*\\n\\n"
            "向我提问、发送语音或照片。\\n"
            "• /balance — 查看余额\\n"
            "• /clear — 清除对话记录\\n"
            "• /reset_memory — 忘记一切\\n\\n"
            "我会自动用你的语言回复。"
        ),
        "uk": (
            "ℹ️ *Допомога*\\n\\n"
            "Питай, надсилай голосові або фото.\\n"
            "• /balance — перевірити баланс\\n"
            "• /clear — очистити історію\\n"
            "• /reset_memory — видалити всю пам\'ять\\n\\n"
            "Відповідаю твоєю мовою автоматично."
        ),
        "ka": (
            "ℹ️ *დახმარება*\\n\\n"
            "დამისვი კითხვა, გამოგზავნე ხმოვანი ან ფოტო.\\n"
            "• /balance — ბალანსის შემოწმება\\n"
            "• /clear — ისტორიის გასუფთავება\\n"
            "• /reset_memory — ყველაფრის წაშლა\\n\\n"
            "ავტომატურად ვპასუხობ შენს ენაზე."
        ),
    },

    # ── /clear ────────────────────────────────────────────────────────────────
    # P3: short confirmation.
    "session_cleared": {
        "en": "🧹 Conversation cleared. Memory intact — /reset_memory to forget everything.",
        "ru": "🧹 История очищена. Память сохранена — /reset_memory, чтобы забыть всё.",
        "de": "🧹 Gespräch gelöscht. Erinnerungen bleiben — /reset_memory löscht alles.",
        "fr": "🧹 Conversation effacée. Mémoire intacte — /reset_memory pour tout oublier.",
        "es": "🧹 Conversación borrada. Memoria intacta — /reset_memory para olvidar todo.",
        "pt": "🧹 Conversa apagada. Memória intacta — /reset_memory para esquecer tudo.",
        "it": "🧹 Conversazione cancellata. Memoria intatta — /reset_memory per dimenticare tutto.",
        "tr": "🧹 Sohbet temizlendi. Hafıza korundu — her şeyi unutmak için /reset_memory.",
        "ar": "🧹 المحادثة مسحت. الذاكرة سليمة — /reset_memory لنسيان كل شيء.",
        "zh": "🧹 对话已清除。记忆完好 — /reset_memory 可忘记一切。",
        "uk": "🧹 Історію очищено. Пам\'ять збережена — /reset_memory, щоб забути все.",
        "ka": "🧹 საუბარი გასუფთავდა. მეხსიერება შენახულია — /reset_memory ყველაფრის დასავიწყებლად.",
    },

    # ── /reset_memory ─────────────────────────────────────────────────────────
    # ⚠️ kept — this is an irreversible destructive action.
    "memory_reset_confirm": {
        "en": "⚠️ This will permanently delete your memory and conversation history. Send /reset_memory confirm to proceed.",
        "ru": "⚠️ Это навсегда удалит память и историю диалогов. Отправь /reset_memory confirm для подтверждения.",
        "de": "⚠️ Dadurch werden Erinnerungen und Gesprächsverlauf dauerhaft gelöscht. Sende /reset_memory confirm.",
        "fr": "⚠️ Cela supprimera définitivement ta mémoire et l\'historique. Envoie /reset_memory confirm.",
        "es": "⚠️ Esto eliminará permanentemente tu memoria e historial. Envía /reset_memory confirm.",
        "pt": "⚠️ Isto eliminará permanentemente a memória e o histórico. Envia /reset_memory confirm.",
        "it": "⚠️ Questo eliminerà definitivamente la memoria e la cronologia. Invia /reset_memory confirm.",
        "tr": "⚠️ Bu, hafızayı ve sohbet geçmişini kalıcı olarak siler. /reset_memory confirm gönder.",
        "ar": "⚠️ سيؤدي هذا إلى حذف الذاكرة وسجل المحادثة نهائياً. أرسل /reset_memory confirm.",
        "zh": "⚠️ 这将永久删除记忆和对话历史。发送 /reset_memory confirm 以确认。",
        "uk": "⚠️ Це назавжди видалить пам\'ять та історію. Надішли /reset_memory confirm для підтвердження.",
        "ka": "⚠️ ეს სამუდამოდ წაშლის მეხსიერებას და ისტორიას. გამოგზავნე /reset_memory confirm.",
    },

    "memory_reset_done": {
        "en": "🗑️ Memory and conversation history permanently deleted.",
        "ru": "🗑️ Память и история диалогов удалены навсегда.",
        "de": "🗑️ Erinnerungen und Gesprächsverlauf dauerhaft gelöscht.",
        "fr": "🗑️ Mémoire et historique supprimés définitivement.",
        "es": "🗑️ Memoria e historial eliminados permanentemente.",
        "pt": "🗑️ Memória e histórico eliminados permanentemente.",
        "it": "🗑️ Memoria e cronologia eliminate definitivamente.",
        "tr": "🗑️ Hafıza ve sohbet geçmişi kalıcı olarak silindi.",
        "ar": "🗑️ تم حذف الذاكرة وسجل المحادثة نهائياً.",
        "zh": "🗑️ 记忆和对话历史已永久删除。",
        "uk": "🗑️ Пам\'ять та історія видалені назавжди.",
        "ka": "🗑️ მეხსიერება და ისტორია სამუდამოდ წაიშალა.",
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
        "hy": "💰 Mnacord: ${amount}",
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
        "hy": "✅ Chegharkavats e:",
        "mn": "✅ Цуцлагдсан.",
    },

    # ── no grounded data (Truth Enforcement — STRICT mode) ───────────────────
    # P5a: one question nudge.
    "no_grounded_data": {
        "en": "🔍 Couldn\'t ground this reliably right now. One more clue or a narrower query, and I\'ll try again.",
        "ru": "🔍 Не удалось надёжно подтвердить запрос. Дай ещё одну подсказку или уточни — попробую снова.",
        "de": "🔍 Konnte das gerade nicht zuverlässig verifizieren. Noch ein Hinweis?",
        "fr": "🔍 Impossible de confirmer ça fiablement maintenant. Un indice de plus ?",
        "es": "🔍 No pude verificar esto ahora. ¿Un dato más y lo intento de nuevo?",
        "pt": "🔍 Não consegui verificar isso agora. Mais uma pista?",
        "it": "🔍 Non riesco a verificarlo ora. Ancora un indizio?",
        "tr": "🔍 Şu an bunu güvenilir şekilde doğrulayamadım. Bir ipucu daha?",
        "ar": "🔍 لم أستطع التحقق من ذلك الآن. تلميح إضافي؟",
        "zh": "🔍 现在无法可靠地确认这个。再给一个线索？",
        "ja": "🔍 今はこれを確認できなかった。もう一つヒントをくれる？",
        "ko": "🔍 지금은 이걸 확실히 확인하지 못했어요. 단서 하나 더 주시겠어요?",
        "pl": "🔍 Nie udało mi się tego teraz wiarygodnie sprawdzić. Jeden trop więcej?",
        "uk": "🔍 Не вдалось підтвердити надійно. Ще одна підказка?",
        "fa": "🔍 الان نتوانستم این را به‌درستی تأیید کنم. یک سرنخ دیگر؟",
        "nl": "🔍 Kon dit nu niet betrouwbaar verifiëren. Nog een aanwijzing?",
        "sv": "🔍 Kunde inte bekräfta detta pålitligt nu. Ledtråd till?",
        "no": "🔍 Klarte ikke bekrefte dette nå. En ledetråd til?",
        "da": "🔍 Kunne ikke bekræfte det pålideligt nu. Et spor mere?",
        "fi": "🔍 En pystynyt nyt vahvistamaan tätä luotettavasti. Vihje lisää?",
        "he": "🔍 לא הצלחתי לאמת את זה עכשיו. עוד רמז?",
        "hi": "🔍 अभी इसे विश्वसनीय रूप से सत्यापित नहीं कर पाई। एक और सुराग?",
        "id": "🔍 Tidak bisa memverifikasi ini sekarang. Satu petunjuk lagi?",
        "az": "🔍 İndi bunu etibarlı şəkildə təsdiqləyə bilmədim. Bir ipucu daha?",
        "kk": "🔍 Қазір мұны сенімді түрде тексере алмадым. Тағы бір нұсқау?",
        "uz": "🔍 Hozir buni ishonchli tarzda tekshira olmadim. Yana bir ko\'rsatma?",
        "ka": "🔍 ახლა ეს საიმედოდ ვერ შევამოწმე. კიდევ ერთი მინიშნება?",
        "hy": "🔍 Hima sranits verifitsnel chem karox. Mek hint ev?",
        "mn": "🔍 Одоо энийг найдвартай баталж чадсангүй. Нэг илүү дохио?",
        "cs": "🔍 Teď to nešlo spolehlivě ověřit. Ještě jeden tip?",
        "ro": "🔍 Nu am putut verifica asta acum. Încă un indiciu?",
        "hu": "🔍 Most nem sikerült megbízhatóan megerősíteni. Még egy tipp?",
        "th": "🔍 ตอนนี้ไม่สามารถยืนยันได้อย่างน่าเชื่อถือ มีเบาะแสเพิ่มเติมไหม?",
        "vi": "🔍 Không thể xác minh điều này ngay bây giờ. Thêm một gợi ý nữa?",
        "ms": "🔍 Tidak dapat mengesahkan ini sekarang. Satu petunjuk lagi?",
        "bn": "🔍 এখন এটি নির্ভরযোগ্যভাবে যাচাই করতে পারিনি। আরেকটি সূত্র?",
        "ur": "🔍 ابھی اسے قابل اعتماد طریقے سے تصدیق نہیں کر سکی۔ ایک اشارہ اور؟",
        "bg": "🔍 Не успях да го проверя надеждно сега. Още един намек?",
        "hr": "🔍 Sad to nisam mogla pouzdano provjeriti. Još jedan trag?",
        "sr": "🔍 Нисам могла сада то поуздано да проверим. Још један траг?",
        "sk": "🔍 Teraz sa mi to nepodarilo spoľahlivo overiť. Ešte jeden tip?",
    },

    # ── vision error ──────────────────────────────────────────────────────────
    # P3 + P6: short, no panic.
    "vision_error": {
        "en": "Couldn\'t read the image. Try sending it again?",
        "ru": "Не получилось прочитать изображение. Попробуешь отправить ещё раз?",
        "de": "Konnte das Bild nicht lesen. Nochmal senden?",
        "fr": "Je n\'ai pas pu lire l\'image. Tu veux réessayer ?",
        "es": "No pude leer la imagen. ¿La enviás de nuevo?",
        "pt": "Não consegui ler a imagem. Tentas enviar de novo?",
        "it": "Non ho potuto leggere l\'immagine. Provi a reinviarla?",
        "tr": "Görseli okuyamadım. Tekrar gönderir misin?",
        "ar": "لم أستطع قراءة الصورة. هل تحاول إرسالها مرة أخرى؟",
        "zh": "没能读取图片，再发一次试试？",
        "ja": "画像を読み取れなかった。もう一度送ってみて。",
        "ko": "이미지를 읽지 못했어요. 다시 보내볼래요?",
        "pl": "Nie udało mi się odczytać obrazu. Spróbujesz wysłać ponownie?",
        "uk": "Не вдалось прочитати зображення. Спробуєш відправити ще раз?",
        "fa": "نتوانستم تصویر را بخوانم. دوباره ارسال می‌کنی؟",
        "nl": "Kon de afbeelding niet lezen. Nog een keer sturen?",
        "sv": "Kunde inte läsa bilden. Skicka igen?",
        "no": "Klarte ikke lese bildet. Prøv å sende det igjen?",
        "da": "Kunne ikke læse billedet. Prøv at sende det igen?",
        "fi": "En pystynyt lukemaan kuvaa. Kokeile lähettää uudelleen?",
        "he": "לא הצלחתי לקרוא את התמונה. שולח שוב?",
        "hi": "छवि नहीं पढ़ पाई। दोबारा भेजकर देखें?",
        "id": "Tidak bisa membaca gambar. Coba kirim lagi?",
        "az": "Şəkli oxuya bilmədim. Yenidən göndərərsiniz?",
        "kk": "Суретті оқи алмадым. Қайта жіберіп көресіз бе?",
        "uz": "Rasmni o\'qiy olmadim. Qayta yuborib ko\'rasizmi?",
        "ka": "სურათის წაკითხვა ვერ მოხერხდა. კვლავ გამოგზავნი?",
        "hy": "Petke chenk karox karchakel: Krkn ugarkek?",
        "mn": "Зургийг уншиж чадсангүй. Дахин илгээж үзэх үү?",
    },

    "too_many_images": {
        "en": "I can take up to 6 images at a time — send them in smaller groups.",
        "ru": "Я могу обработать до 6 изображений за раз — отправь меньшими группами.",
        "de": "Ich kann bis zu 6 Bilder auf einmal verarbeiten — in kleineren Gruppen senden.",
        "fr": "Je peux traiter jusqu\'à 6 images à la fois — envoie-les en petits groupes.",
        "es": "Puedo procesar hasta 6 imágenes a la vez — envíalas en grupos más pequeños.",
        "pt": "Consigo processar até 6 imagens de cada vez — envia em grupos menores.",
        "it": "Posso elaborare fino a 6 immagini alla volta — invia in gruppi più piccoli.",
        "tr": "Aynı anda 6 görsele kadar işleyebilirim — daha küçük gruplar halinde gönder.",
        "ar": "يمكنني معالجة حتى 6 صور في المرة الواحدة — أرسلها في مجموعات أصغر.",
        "zh": "我一次最多处理6张图片 — 请分批发送。",
        "ja": "一度に6枚まで処理できます — 小さいグループに分けて送って。",
        "ko": "한 번에 최대 6개 이미지까지 처리할 수 있어요 — 더 작은 그룹으로 보내주세요.",
        "pl": "Mogę przetworzyć do 6 obrazów na raz — wyślij w mniejszych grupach.",
        "uk": "Можу обробити до 6 зображень за раз — надсилай меншими групами.",
        "fa": "می‌توانم تا ۶ تصویر را در یک بار پردازش کنم — در گروه‌های کوچک‌تر ارسال کن.",
        "nl": "Ik kan maximaal 6 afbeeldingen tegelijk verwerken — stuur ze in kleinere groepen.",
        "sv": "Jag kan behandla upp till 6 bilder åt gången — skicka i mindre grupper.",
        "no": "Jeg kan behandle opptil 6 bilder om gangen — send i mindre grupper.",
        "da": "Jeg kan behandle op til 6 billeder ad gangen — send i mindre grupper.",
        "fi": "Voin käsitellä enintään 6 kuvaa kerrallaan — lähetä pienemmissä ryhmissä.",
        "he": "אני יכולה לעבד עד 6 תמונות בכל פעם — שלח בקבוצות קטנות יותר.",
        "hi": "एक बार में 6 तस्वीरें प्रोसेस कर सकती हूँ — छोटे समूहों में भेजें।",
        "id": "Saya bisa memproses hingga 6 gambar sekaligus — kirim dalam kelompok lebih kecil.",
        "az": "Bir dəfədə 6 şəkil işləyə bilirəm — kiçik qruplarla göndərin.",
        "kk": "Бір жолы 6 суретке дейін өңдей аламын — кішірек топтармен жіберіңіз.",
        "uz": "Bir vaqtda 6 tagacha rasmni qayta ishlay olaman — kichikroq guruhlar bilan yuboring.",
        "ka": "ერთდროულად 6 სურათამდე შემიძლია — პატარა ჯგუფებად გამოგზავნე.",
        "hy": "Mek anghamenum minchdzhev 6 nkaratak em karox skselakel — aveli patara khmberov ugarkek:",
        "mn": "Нэг удаад хамгийн ихдээ 6 зураг боловсруулж чадна — жижиг бүлгүүдээр илгээ.",
    },

    # ── silent keys ───────────────────────────────────────────────────────────
    "weather_feels_like": {
        "en": "feels like",   "ru": "ощущается как",   "de": "gefühlt",
        "fr": "ressenti",     "es": "sensación",        "pt": "sensação",
        "it": "percepito",    "tr": "hissedilen",       "ar": "يبدو كأنه",
        "zh": "体感",          "ja": "体感",              "ko": "체감",
        "pl": "odczuwalna",   "uk": "відчувається як",  "fa": "احساس می‌شود",
        "nl": "voelt als",    "sv": "känns som",        "no": "føles som",
        "da": "føles som",    "fi": "tuntuu kuin",      "he": "מורגש כ",
        "ka": "ისეთივეა, როგორც", "hy": "ինչպես",      "az": "hiss olunur",
        "kk": "сезіледі",     "uz": "seziladi",         "hi": "जैसा लगता है",
        "id": "terasa",       "ms": "terasa",            "th": "รู้สึกเหมือน",
        "vi": "cảm giác",     "mn": "мэдрэмж",          "sw": "inajisikia kama",
        "bg": "усеща се",     "hr": "osjeća se",        "sr": "осећа се",
        "cs": "pocitově",     "sk": "cíti sa",          "ro": "se simte ca",
        "hu": "érzetben",
    },
    "weather_humidity": {
        "en": "Humidity",       "ru": "Влажность",     "de": "Luftfeuchtigkeit",
        "fr": "Humidité",       "es": "Humedad",        "pt": "Umidade",
        "it": "Umidità",        "tr": "Nem",            "ar": "الرطوبة",
        "zh": "湿度",            "ja": "湿度",            "ko": "습도",
        "pl": "Wilgotność",     "uk": "Вологість",      "fa": "رطوبت",
        "nl": "Vochtigheid",    "sv": "Luftfuktighet",  "no": "Luftfuktighet",
        "da": "Luftfugtighed",  "fi": "Kosteus",        "he": "לחות",
        "ka": "ტენიანობა",      "hy": "Խոնавություн",   "az": "Rütubət",
        "kk": "Ылғалдылық",     "uz": "Namlik",         "hi": "आर्द्रता",
        "id": "Kelembaban",     "ms": "Kelembapan",     "th": "ความชื้น",
        "vi": "Độ ẩm",          "mn": "Чийглэг",        "sw": "Unyevu",
        "bg": "Влажност",       "hr": "Vlažnost",       "sr": "Влажност",
        "cs": "Vlhkost",        "sk": "Vlhkosť",        "ro": "Umiditate",
        "hu": "Páratartalom",
    },
    "weather_wind": {
        "en": "Wind",    "ru": "Ветер",    "de": "Wind",   "fr": "Vent",
        "es": "Viento",  "pt": "Vento",    "it": "Vento",  "tr": "Rüzgar",
        "ar": "الرياح",  "zh": "风速",     "ja": "風速",   "ko": "바람",
        "pl": "Wiatr",   "uk": "Вітер",    "fa": "باد",    "nl": "Wind",
        "sv": "Vind",    "no": "Vind",     "da": "Vind",   "fi": "Tuuli",
        "he": "רוח",     "ka": "ქარი",    "hy": "Qamiw",  "az": "Külək",
        "kk": "Жел",     "uz": "Shamol",   "hi": "हवा",   "id": "Angin",
        "ms": "Angin",   "th": "ลม",       "vi": "Gió",   "mn": "Салхи",
        "sw": "Upepo",   "bg": "Вятър",   "hr": "Vjetar", "sr": "Ветар",
        "cs": "Vítr",    "sk": "Vietor",   "ro": "Vânt",  "hu": "Szél",
    },

    # ── search ────────────────────────────────────────────────────────────────
    "no_search_results": {
        "en": "🔍 Nothing found.",
        "ru": "🔍 Ничего не нашлось.",
        "de": "🔍 Nichts gefunden.",
        "fr": "🔍 Aucun résultat.",
        "es": "🔍 Sin resultados.",
        "pt": "🔍 Nenhum resultado.",
        "it": "🔍 Nessun risultato.",
        "tr": "🔍 Sonuç yok.",
        "ar": "🔍 لا نتائج.",
        "zh": "🔍 没有找到。",
        "ja": "🔍 見つかりません。",
        "ko": "🔍 결과 없음.",
        "pl": "🔍 Brak wyników.",
        "uk": "🔍 Нічого не знайшлося.",
        "fa": "🔍 نتیجه‌ای نیست.",
        "nl": "🔍 Niets gevonden.",
        "sv": "🔍 Inga resultat.",
        "no": "🔍 Ingen resultater.",
        "da": "🔍 Ingen resultater.",
        "fi": "🔍 Ei tuloksia.",
        "he": "🔍 אין תוצאות.",
        "hi": "🔍 कोई नतीजा नहीं।",
        "id": "🔍 Tidak ada hasil.",
        "ms": "🔍 Tiada hasil.",
        "th": "🔍 ไม่พบผลลัพธ์",
        "vi": "🔍 Không có kết quả.",
        "ka": "🔍 ვერაფერი მოიძებნა.",
        "hy": "🔍 Ardinqner chgtvetskin:",
        "az": "🔍 Nəticə yoxdur.",
        "kk": "🔍 Нәтиже жоқ.",
        "uz": "🔍 Natija topilmadi.",
        "mn": "🔍 Үр дүн алга.",
        "sw": "🔍 Hakuna matokeo.",
        "bg": "🔍 Нищо не е намерено.",
        "hr": "🔍 Nema rezultata.",
        "sr": "🔍 Нема резултата.",
        "cs": "🔍 Nic nenalezeno.",
        "sk": "🔍 Žiadne výsledky.",
        "ro": "🔍 Niciun rezultat.",
        "hu": "🔍 Nincs találat.",
        "bn": "🔍 কোনো ফলাফল নেই।",
        "ur": "🔍 کوئی نتیجہ نہیں۔",
        "ha": "🔍 Babu sakamakon.",
        "yo": "🔍 Ko si abajade.",
        "so": "🔍 Ma jiraan natiijooyin.",
    },

    # ── search / live-data fallbacks ───────────────────────────────────────────
    "search_need_more_clues": {
        "en": "🔍 Couldn\'t pin this down from the clues so far. One or two more details?",
        "ru": "🔍 Пока не получается уверенно определить. Ещё 1–2 детали?",
    },
    "live_data_unavailable": {
        "en": "🔍 Couldn\'t fetch live data right now. Give me the city, airport, or place again and I\'ll try.",
        "ru": "🔍 Сейчас не удалось получить данные. Назови город, аэропорт или место ещё раз — попробую снова.",
    },

    # ── emotional fallback ────────────────────────────────────────────────────
    # P3: very short. The 🔄 is enough.
    "emotional_fallback": {
        "en": "Couldn\'t get a response right now. You can try again 🔄",
        "ru": "Сейчас не получилось ответить. Попробуй ещё раз 🔄",
        "de": "Gerade keine Antwort möglich. Versuch es nochmal 🔄",
        "fr": "Impossible de répondre pour l\'instant. Réessaie 🔄",
        "es": "No pude responder ahora. Puedes intentarlo de nuevo 🔄",
        "pt": "Não foi possível responder agora. Tenta novamente 🔄",
        "it": "Non è stato possibile rispondere ora. Riprova 🔄",
        "tr": "Şu an yanıt veremedim. Tekrar deneyebilirsin 🔄",
        "ar": "لم أتمكن من الرد الآن. يمكنك المحاولة مرة أخرى 🔄",
        "zh": "暂时无法回复，再试一次 🔄",
        "uk": "Зараз не вдалося відповісти. Спробуй ще раз 🔄",
        "ka": "ახლა პასუხის გაცემა ვერ მოხერხდა. სცადეთ თავიდან 🔄",
    },

    # ── CoT loop fallback ─────────────────────────────────────────────────────
    # P5a: one question. P1: specific, not generic.
    "cot_fallback": {
        "en": "I\'m not sure — could you give me a hint or more context?",
        "ru": "Не могу точно определить — попробуй дать подсказку или уточнить вопрос.",
        "de": "Nicht sicher — kannst du mir einen Hinweis oder mehr Kontext geben?",
        "fr": "Pas sûre — tu peux me donner un indice ou plus de contexte ?",
        "es": "No estoy segura — ¿puedes darme una pista o más contexto?",
        "pt": "Não tenho certeza — podes dar-me uma dica ou mais contexto?",
        "it": "Non sono sicura — potresti darmi un indizio o più contesto?",
        "ar": "لست متأكدة — هل يمكنك إعطائي تلميحاً أو مزيداً من السياق؟",
        "zh": "不确定——能给我一个提示或更多背景吗？",
        "tr": "Emin değilim — bir ipucu veya daha fazla bağlam verebilir misin?",
        "uk": "Не можу точно визначити — спробуй підказати або уточни питання.",
        "ka": "დარწმუნებული არ ვარ — მომეცი მინიშნება ან დამატებითი კონტექსტი?",
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
        "hy": "💵 Lratsnel mnacordn",
        "az": "💵 Balansı artır",
        "kk": "💵 Балансты толтыру",
        "uz": "💵 Balansi to\'ldirish",
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
        "ha": "💵 Ƙara ma\'auni",
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
        "hy": "💰 Mnacord: ${amount}",
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
        "ha": "💰 Ma\'auni: ${amount}",
    },

    # ── Maps: geocode coordinate label ────────────────────────────────────────
    "maps_coord_label": {
        "en": "📍 *${name}*\\nCoordinates: ${lat}, ${lon}",
        "ru": "📍 *${name}*\\nКоординаты: ${lat}, ${lon}",
        "de": "📍 *${name}*\\nKoordinaten: ${lat}, ${lon}",
        "fr": "📍 *${name}*\\nCoordonnées : ${lat}, ${lon}",
        "es": "📍 *${name}*\\nCoordenadas: ${lat}, ${lon}",
        "pt": "📍 *${name}*\\nCoordenadas: ${lat}, ${lon}",
        "it": "📍 *${name}*\\nCoordinate: ${lat}, ${lon}",
        "tr": "📍 *${name}*\\nKoordinatlar: ${lat}, ${lon}",
        "ar": "📍 *${name}*\\nالإحداثيات: ${lat}, ${lon}",
        "zh": "📍 *${name}*\\n坐标：${lat}, ${lon}",
        "ja": "📍 *${name}*\\n座標：${lat}, ${lon}",
        "ko": "📍 *${name}*\\n좌표: ${lat}, ${lon}",
        "pl": "📍 *${name}*\\nWspółrzędne: ${lat}, ${lon}",
        "uk": "📍 *${name}*\\nКоординати: ${lat}, ${lon}",
        "nl": "📍 *${name}*\\nCoördinaten: ${lat}, ${lon}",
        "sv": "📍 *${name}*\\nKoordinater: ${lat}, ${lon}",
        "da": "📍 *${name}*\\nKoordinater: ${lat}, ${lon}",
        "fi": "📍 *${name}*\\nKoordinaatit: ${lat}, ${lon}",
        "cs": "📍 *${name}*\\nSouřadnice: ${lat}, ${lon}",
        "ro": "📍 *${name}*\\nCoordonate: ${lat}, ${lon}",
        "hu": "📍 *${name}*\\nKoordináták: ${lat}, ${lon}",
        "he": "📍 *${name}*\\nקואורדינטות: ${lat}, ${lon}",
        "vi": "📍 *${name}*\\nTọa độ: ${lat}, ${lon}",
        "th": "📍 *${name}*\\nพิกัด: ${lat}, ${lon}",
        "id": "📍 *${name}*\\nKoordinat: ${lat}, ${lon}",
        "ms": "📍 *${name}*\\nKoordinat: ${lat}, ${lon}",
        "ka": "📍 *${name}*\\nკოორდინატები: ${lat}, ${lon}",
        "hy": "📍 *${name}*\\nKoordinatner: ${lat}, ${lon}",
        "az": "📍 *${name}*\\nKoordinatlar: ${lat}, ${lon}",
        "kk": "📍 *${name}*\\nКоординаттар: ${lat}, ${lon}",
        "uz": "📍 *${name}*\\nKoordinatalar: ${lat}, ${lon}",
        "hi": "📍 *${name}*\\nनिर्देशांक: ${lat}, ${lon}",
        "bn": "📍 *${name}*\\nনির্দেশাঙ্ক: ${lat}, ${lon}",
        "ur": "📍 *${name}*\\nنقاط: ${lat}, ${lon}",
        "fa": "📍 *${name}*\\nمختصات: ${lat}, ${lon}",
        "mn": "📍 *${name}*\\nКоординат: ${lat}, ${lon}",
        "sw": "📍 *${name}*\\nUratibu: ${lat}, ${lon}",
    },

    # ── Maps: location not found ───────────────────────────────────────────────
    "maps_not_found": {
        "en": "📍 Location not found. Try a more specific name.",
        "ru": "📍 Место не найдено. Попробуй уточнить название.",
        "de": "📍 Ort nicht gefunden. Versuch einen genaueren Namen.",
        "fr": "📍 Lieu introuvable. Essaie un nom plus précis.",
        "es": "📍 Lugar no encontrado. Prueba con un nombre más específico.",
        "pt": "📍 Local não encontrado. Tenta um nome mais específico.",
        "it": "📍 Luogo non trovato. Prova con un nome più specifico.",
        "tr": "📍 Konum bulunamadı. Daha spesifik bir isim dene.",
        "ar": "📍 الموقع غير موجود. جرّب اسماً أكثر تحديداً.",
        "zh": "📍 未找到该位置。试试更具体的名称。",
        "ja": "📍 場所が見つからなかった。もっと具体的な名前で試して。",
        "ko": "📍 위치를 찾지 못했어요. 더 구체적인 이름으로 해볼까요?",
        "pl": "📍 Nie znaleziono miejsca. Spróbuj dokładniejszej nazwy.",
        "uk": "📍 Місце не знайдено. Спробуй уточнити назву.",
        "nl": "📍 Locatie niet gevonden. Probeer een specifiekere naam.",
        "sv": "📍 Platsen hittades inte. Försök med ett mer specifikt namn.",
        "da": "📍 Stedet ikke fundet. Prøv et mere specifikt navn.",
        "fi": "📍 Paikkaa ei löydy. Kokeile tarkempaa nimeä.",
        "cs": "📍 Místo nenalezeno. Zkus konkrétnější název.",
        "ro": "📍 Locul nu a fost găsit. Încearcă un nume mai specific.",
        "hu": "📍 A hely nem található. Próbálj pontosabb nevet.",
        "he": "📍 המיקום לא נמצא. נסה שם ספציפי יותר.",
        "vi": "📍 Không tìm thấy địa điểm. Thử tên cụ thể hơn.",
        "th": "📍 ไม่พบสถานที่ ลองใช้ชื่อที่เจาะจงกว่านี้",
        "id": "📍 Lokasi tidak ditemukan. Coba nama yang lebih spesifik.",
        "ms": "📍 Lokasi tidak dijumpai. Cuba nama yang lebih spesifik.",
        "ka": "📍 ადგილი ვერ მოიძებნა. სცადე უფრო კონკრეტული სახელი.",
        "hy": "📍 Vayry chgtvets: Aveli konkret anun probela:",
        "az": "📍 Yer tapılmadı. Daha konkret ad sınayın.",
        "kk": "📍 Орын табылмады. Нақтырақ атауды қолданып көр.",
        "uz": "📍 Joy topilmadi. Aniqroq nom bilan sinab ko\'r.",
        "hi": "📍 स्थान नहीं मिला। अधिक विशिष्ट नाम आज़माएं।",
        "fa": "📍 مکان پیدا نشد. نام دقیق‌تری امتحان کن.",
        "mn": "📍 Байршил олдсонгүй. Илүү тодорхой нэр ашигла.",
    },

    # ── Maps: POI not found ────────────────────────────────────────────────────
    "maps_poi_not_found": {
        "en": "📍 No ${category} found near ${location}. Try a different area or category.",
        "ru": "📍 Рядом с ${location} не нашлось: ${category}. Попробуй другой район или категорию.",
        "de": "📍 Kein ${category} in der Nähe von ${location} gefunden.",
        "fr": "📍 Aucun ${category} trouvé près de ${location}.",
        "es": "📍 No se encontró ${category} cerca de ${location}.",
        "pt": "📍 Nenhum ${category} encontrado perto de ${location}.",
        "it": "📍 Nessun ${category} trovato vicino a ${location}.",
        "tr": "📍 ${location} yakınında ${category} bulunamadı.",
        "ar": "📍 لا يوجد ${category} بالقرب من ${location}.",
        "zh": "📍 在${location}附近未找到${category}。",
        "ja": "📍 ${location}の近くに${category}が見つからなかった。",
        "ko": "📍 ${location} 근처에서 ${category}을(를) 찾지 못했어요.",
        "pl": "📍 Nie znaleziono ${category} w pobliżu ${location}.",
        "uk": "📍 Поряд з ${location} не знайшлось: ${category}.",
        "ka": "📍 ${location}-ის მახლობლად ${category} ვერ მოიძებნა.",
        "hy": "📍 ${location}-i mot ${category} chgtvets:",
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
        "en": "📍 *${name}*\\n${address}\\nCoordinates: ${lat}, ${lon}",
        "ru": "📍 *${name}*\\n${address}\\nКоординаты: ${lat}, ${lon}",
        "de": "📍 *${name}*\\n${address}\\nKoordinaten: ${lat}, ${lon}",
        "fr": "📍 *${name}*\\n${address}\\nCoordonnées : ${lat}, ${lon}",
        "es": "📍 *${name}*\\n${address}\\nCoordenadas: ${lat}, ${lon}",
        "pt": "📍 *${name}*\\n${address}\\nCoordenadas: ${lat}, ${lon}",
        "it": "📍 *${name}*\\n${address}\\nCoordinate: ${lat}, ${lon}",
        "tr": "📍 *${name}*\\n${address}\\nKoordinatlar: ${lat}, ${lon}",
        "ar": "📍 *${name}*\\n${address}\\nالإحداثيات: ${lat}, ${lon}",
        "zh": "📍 *${name}*\\n${address}\\n坐标：${lat}, ${lon}",
        "ja": "📍 *${name}*\\n${address}\\n座標：${lat}, ${lon}",
        "ko": "📍 *${name}*\\n${address}\\n좌표: ${lat}, ${lon}",
        "pl": "📍 *${name}*\\n${address}\\nWspółrzędne: ${lat}, ${lon}",
        "uk": "📍 *${name}*\\n${address}\\nКоординати: ${lat}, ${lon}",
        "nl": "📍 *${name}*\\n${address}\\nCoördinaten: ${lat}, ${lon}",
        "sv": "📍 *${name}*\\n${address}\\nKoordinater: ${lat}, ${lon}",
        "da": "📍 *${name}*\\n${address}\\nKoordinater: ${lat}, ${lon}",
        "fi": "📍 *${name}*\\n${address}\\nKoordinaatit: ${lat}, ${lon}",
        "cs": "📍 *${name}*\\n${address}\\nSouřadnice: ${lat}, ${lon}",
        "ro": "📍 *${name}*\\n${address}\\nCoordonate: ${lat}, ${lon}",
        "hu": "📍 *${name}*\\n${address}\\nKoordináták: ${lat}, ${lon}",
        "he": "📍 *${name}*\\n${address}\\nקואורדינטות: ${lat}, ${lon}",
        "vi": "📍 *${name}*\\n${address}\\nTọa độ: ${lat}, ${lon}",
        "th": "📍 *${name}*\\n${address}\\nพิกัด: ${lat}, ${lon}",
        "id": "📍 *${name}*\\n${address}\\nKoordinat: ${lat}, ${lon}",
        "ms": "📍 *${name}*\\n${address}\\nKoordinat: ${lat}, ${lon}",
        "ka": "📍 *${name}*\\n${address}\\nკოორდინატები: ${lat}, ${lon}",
        "hy": "📍 *${name}*\\n${address}\\nKoordinatner: ${lat}, ${lon}",
        "az": "📍 *${name}*\\n${address}\\nKoordinatlar: ${lat}, ${lon}",
        "kk": "📍 *${name}*\\n${address}\\nКоординаттар: ${lat}, ${lon}",
        "uz": "📍 *${name}*\\n${address}\\nKoordinatalar: ${lat}, ${lon}",
        "hi": "📍 *${name}*\\n${address}\\nनिर्देशांक: ${lat}, ${lon}",
        "fa": "📍 *${name}*\\n${address}\\nمختصات: ${lat}, ${lon}",
        "mn": "📍 *${name}*\\n${address}\\nКоординат: ${lat}, ${lon}",
        "sw": "📍 *${name}*\\n${address}\\nUratibu: ${lat}, ${lon}",
    },

    # ── Maps: route result ─────────────────────────────────────────────────────
    "maps_route_result": {
        "en": "🗺 Route: ${origin} → ${destination}\\n📏 Distance: ${dist} km\\n⏱ Drive time: ~${dur} min",
        "ru": "🗺 Маршрут: ${origin} → ${destination}\\n📏 Расстояние: ${dist} км\\n⏱ Время в пути: ~${dur} мин",
        "de": "🗺 Route: ${origin} → ${destination}\\n📏 Entfernung: ${dist} km\\n⏱ Fahrzeit: ~${dur} Min.",
        "fr": "🗺 Itinéraire: ${origin} → ${destination}\\n📏 Distance: ${dist} km\\n⏱ Durée: ~${dur} min",
        "es": "🗺 Ruta: ${origin} → ${destination}\\n📏 Distancia: ${dist} km\\n⏱ Tiempo: ~${dur} min",
        "pt": "🗺 Rota: ${origin} → ${destination}\\n📏 Distância: ${dist} km\\n⏱ Tempo: ~${dur} min",
        "it": "🗺 Percorso: ${origin} → ${destination}\\n📏 Distanza: ${dist} km\\n⏱ Durata: ~${dur} min",
        "tr": "🗺 Güzergah: ${origin} → ${destination}\\n📏 Mesafe: ${dist} km\\n⏱ Süre: ~${dur} dak",
        "ar": "🗺 المسار: ${origin} → ${destination}\\n📏 المسافة: ${dist} كم\\n⏱ وقت القيادة: ~${dur} دقيقة",
        "zh": "🗺 路线：${origin} → ${destination}\\n📏 距离：${dist} 公里\\n⏱ 行驶时间：约 ${dur} 分钟",
        "ja": "🗺 ルート：${origin} → ${destination}\\n📏 距離：${dist} km\\n⏱ 所要時間：約 ${dur} 分",
        "ko": "🗺 경로: ${origin} → ${destination}\\n📏 거리: ${dist} km\\n⏱ 이동 시간: 약 ${dur}분",
        "pl": "🗺 Trasa: ${origin} → ${destination}\\n📏 Odległość: ${dist} km\\n⏱ Czas jazdy: ~${dur} min",
        "uk": "🗺 Маршрут: ${origin} → ${destination}\\n📏 Відстань: ${dist} км\\n⏱ Час у дорозі: ~${dur} хв",
        "nl": "🗺 Route: ${origin} → ${destination}\\n📏 Afstand: ${dist} km\\n⏱ Rijtijd: ~${dur} min",
        "sv": "🗺 Rutt: ${origin} → ${destination}\\n📏 Avstånd: ${dist} km\\n⏱ Körtid: ~${dur} min",
        "fi": "🗺 Reitti: ${origin} → ${destination}\\n📏 Etäisyys: ${dist} km\\n⏱ Ajoaika: ~${dur} min",
        "he": "🗺 מסלול: ${origin} → ${destination}\\n📏 מרחק: ${dist} ק\\"מ\\n⏱ זמן נסיעה: ~${dur} דקות",
        "ka": "🗺 მარშრუტი: ${origin} → ${destination}\\n📏 მანძილი: ${dist} კმ\\n⏱ გზაში: ~${dur} წთ",
        "hy": "🗺 Yertughi: ${origin} → ${destination}\\n📏 Heravonutyun: ${dist} km\\n⏱ Chamanaparh: ~${dur} rop",
        "az": "🗺 Marşrut: ${origin} → ${destination}\\n📏 Məsafə: ${dist} km\\n⏱ Yol vaxtı: ~${dur} dəq",
        "kk": "🗺 Бағыт: ${origin} → ${destination}\\n📏 Қашықтық: ${dist} км\\n⏱ Жол уақыты: ~${dur} мин",
        "uz": "🗺 Marshrut: ${origin} → ${destination}\\n📏 Masofa: ${dist} km\\n⏱ Yo\'l vaqti: ~${dur} daq",
        "fa": "🗺 مسیر: ${origin} → ${destination}\\n📏 فاصله: ${dist} کیلومتر\\n⏱ زمان رانندگی: ~${dur} دقیقه",
        "hi": "🗺 मार्ग: ${origin} → ${destination}\\n📏 दूरी: ${dist} किमी\\n⏱ ड्राइव समय: ~${dur} मिनट",
        "mn": "🗺 Чиглэл: ${origin} → ${destination}\\n📏 Зай: ${dist} км\\n⏱ Явах хугацаа: ~${dur} мин",
    },

    # ── Maps: route not found ──────────────────────────────────────────────────
    "maps_route_not_found": {
        "en": "🗺 Couldn\'t build a route. Check that both locations are correct.",
        "ru": "🗺 Не получилось построить маршрут. Проверь названия мест.",
        "de": "🗺 Route konnte nicht berechnet werden. Bitte Orte prüfen.",
        "fr": "🗺 Impossible de calculer l\'itinéraire. Vérifie les lieux.",
        "es": "🗺 No se pudo calcular la ruta. Comprueba los lugares.",
        "pt": "🗺 Não foi possível calcular a rota. Verifica os locais.",
        "it": "🗺 Impossibile calcolare il percorso. Controlla i luoghi.",
        "tr": "🗺 Güzergah oluşturulamadı. Lütfen yerleri kontrol et.",
        "ar": "🗺 تعذّر بناء المسار. تحقق من صحة الموقعين.",
        "zh": "🗺 无法构建路线。请检查两个地点。",
        "ja": "🗺 ルートを作れなかった。両方の場所を確認して。",
        "ko": "🗺 경로를 만들지 못했어요. 두 위치를 확인해주세요.",
        "pl": "🗺 Nie udało się obliczyć trasy. Sprawdź nazwy miejsc.",
        "uk": "🗺 Не вдалось побудувати маршрут. Перевір назви місць.",
        "nl": "🗺 Kon geen route berekenen. Controleer beide locaties.",
        "sv": "🗺 Kunde inte bygga rutten. Kontrollera båda platserna.",
        "fi": "🗺 Reittiä ei voitu rakentaa. Tarkista molemmat paikat.",
        "he": "🗺 לא הצלחתי לבנות מסלול. בדוק את שני המיקומים.",
        "ka": "🗺 მარშრუტი ვერ გაკეთდა. შეამოწმე ორივე ადგილი.",
        "az": "🗺 Marşrut qurula bilmədi. Hər iki yeri yoxla.",
        "kk": "🗺 Бағытты құру мүмкін болмады. Екі орынды да тексер.",
        "uz": "🗺 Marshrut qurib bo\'lmadi. Ikkala joyni ham tekshir.",
        "fa": "🗺 مسیر ساخته نشد. هر دو مکان را بررسی کن.",
        "hi": "🗺 मार्ग नहीं बन सका। दोनों जगह जाँचें।",
        "mn": "🗺 Чиглэл байгуулж чадсангүй. Хоёр байршлыг шалга.",
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
    # P2: one soft nudge, warm.
    "low_balance_warning": {
        "en": "Balance is getting low — top up when you can.",
        "ru": "Баланс заканчивается — пополни, когда будет удобно.",
        "de": "Guthaben wird knapp — lade auf, wenn du kannst.",
        "fr": "Le solde baisse — recharge quand tu peux.",
        "es": "El saldo está bajando — recarga cuando puedas.",
        "pt": "O saldo está a acabar — recarrega quando puderes.",
        "it": "Il saldo si sta esaurendo — ricarica quando puoi.",
        "tr": "Bakiye azalıyor — fırsat bulunca yükle.",
        "ar": "الرصيد يقترب من النفاد — اشحنه حين تستطيع.",
        "zh": "余额快用完了，有空充一下。",
        "ja": "残高が少なくなってきた — 余裕があるときにチャージして。",
        "ko": "잔액이 줄고 있어요 — 여유 될 때 충전해주세요.",
        "pl": "Saldo się kończy — doładuj kiedy możesz.",
        "uk": "Баланс закінчується — поповни, коли зможеш.",
        "ka": "ბალანსი ამოიწურება — შეავსე, როცა გამოგივა.",
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