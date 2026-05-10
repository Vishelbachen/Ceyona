# Single source of truth for all user-facing strings and language config.
# Usage:
#   from i18n.strings import t, SUPPORTED_LANGS
#   t("vision_error", lang)          -> str
#   t("balance_display", lang, amount="1.23")  -> str (template substitution)
from __future__ import annotations

# ─── SUPPORTED LANGUAGES ──────────────────────────────────────────────────────

SUPPORTED_LANGS: frozenset[str] = frozenset({
    "en", "ru", "de", "fr", "es", "pt", "it", "tr", "ar",
    "zh", "ja", "ko", "pl", "uk", "fa", "nl", "sv", "no",
    "da", "fi", "cs", "sk", "ro", "hu", "bg", "hr", "sr",
    "he", "vi", "th", "id", "ms", "hi", "bn", "ur",
    "az", "kk", "uz", "ka", "hy", "mn", "sw", "am",
})

# Maps bot lang codes to OpenWeatherMap lang codes
OW_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh_cn", "ja": "ja", "ko": "kr",
    "pl": "pl", "uk": "ua", "fa": "fa", "nl": "nl",
    "sv": "sv", "no": "no", "da": "da", "fi": "fi",
    "he": "he", "vi": "vi", "th": "th", "id": "id",
    "ms": "en", "hi": "en", "bn": "en", "ur": "en",
    "az": "en", "kk": "en", "uz": "en", "ka": "en",
    "hy": "en", "mn": "en", "si": "en", "km": "en",
    "lo": "en", "my": "en", "am": "en", "sw": "en",
}

# Maps lang code to LLM instruction ("reply only in X")
LANG_INSTRUCTIONS: dict[str, str] = {
    "ru": "Отвечай ТОЛЬКО на русском языке.",
    "en": "Reply ONLY in English.",
    "de": "Antworte NUR auf Deutsch.",
    "fr": "Reponds UNIQUEMENT en francais.",
    "es": "Responde SOLO en espanol.",
    "uk": "Vidpovidaj TILKY ukrainskoyu.",
    "tr": "YALNIZCA Turkce yanitla.",
    "ar": "Ajib billughat alarabiyyah faqat.",
    "zh": "Zhi yong zhongwen huida.",
    "ja": "Nihongo nomi de kotaete kudasai.",
    "ko": "Hangugeo로만 daabhaseyo.",
    "pl": "Odpowiadaj TYLKO po polsku.",
    "it": "Rispondi SOLO in italiano.",
    "pt": "Responda APENAS em portugues.",
    "fa": "Faghat be farsi pasokh bede.",
    "nl": "Antwoord ALLEEN in het Nederlands.",
    "sv": "Svara BARA pa svenska.",
    "no": "Svar KUN pa norsk.",
    "da": "Svar KUN pa dansk.",
    "fi": "Vastaa VAIN suomeksi.",
    "he": "Ene rak be'ivrit.",
    "hi": "Sirf Hindi mein jawab do.",
    "id": "Jawab HANYA dalam bahasa Indonesia.",
    "az": "YALNIZ Azerbaycanca cavab ver.",
    "kk": "TYP'KI Qazaqsha zhauap ber.",
    "uz": "FAQAT o'zbekcha javob bering.",
    "ka": "Upasukhe MXOLOD kartulad.",
    "hy": "Pataskhane BATSARAPES hayeren.",
    "mn": "ZUKHUN mongoloor khariulna uu.",
    "bg": "Otgovaryay SAMO na balgarski.",
    "hr": "Odgovaraj SAMO na hrvatskom.",
    "sr": "Odgovaraj SAMO na srpskom.",
    "cs": "Odpovidades POUZE cesky.",
    "sk": "Odpovedaj IBA po slovensky.",
    "ro": "Raspunde DOAR in romana.",
    "hu": "Csak magyarul valaszolj.",
    "th": "Tob CHAPO pen phasa thai.",
    "vi": "Chi tra loi bang tieng Viet.",
    "ms": "Jawab HANYA dalam Bahasa Malaysia.",
    "bn": "Sudhu Bangla-te uttoor dao.",
    "ur": "Sirf Urdu mein jawab den.",
    "sw": "Jibu kwa Kiswahili tu.",
    "am": "Be'ityopya agerawi qwanqwa jibu.",
}

_TON_WALLET = "UQA78muNWF-tW4bhePG8GMdXzj1RuByOtf1XAwZ9VDOBElSA"

# ─── ALL STRINGS ──────────────────────────────────────────────────────────────

_STRINGS: dict[str, dict[str, str]] = {

    # ── vision (screenshot/photo processing) ──────────────────────────────────
    "vision_error": {
        "en": "Failed to process the image. Please try again.",
        "ru": "Не удалось обработать изображение. Попробуйте ещё раз.",
        "de": "Bild konnte nicht verarbeitet werden. Bitte erneut versuchen.",
        "fr": "Impossible de traiter l'image. Veuillez reessayer.",
        "es": "No se pudo procesar la imagen. Intentelo de nuevo.",
        "pt": "Nao foi possivel processar a imagem. Tente novamente.",
        "it": "Impossibile elaborare l'immagine. Riprova.",
        "tr": "Goruntu islenemedi. Lutfen tekrar deneyin.",
        "ar": "Ta'adhdhara mu'aalajat al-sura. Yurja al-muhawala mujaddadan.",
        "zh": "无法处理图片，请重试。",
        "ja": "画像を処理できませんでした。もう一度お試しください。",
        "ko": "이미지를 처리할 수 없습니다. 다시 시도하세요.",
        "pl": "Nie udalo sie przetworzyc obrazu. Sprobuj ponownie.",
        "uk": "Ne vdalosia obrob. zobrazhennia. Sprobuite shche raz.",
        "fa": "Pardazesh tashvir namuvan bud. Lotfan dobare emtehan konid.",
        "nl": "Afbeelding kon niet worden verwerkt. Probeer het opnieuw.",
        "sv": "Kunde inte bearbeta bilden. Forsok igen.",
        "no": "Kunne ikke behandle bildet. Prøv igjen.",
        "da": "Kunne ikke behandle billedet. Prøv igen.",
        "fi": "Kuvaa ei voitu kasitella. Yrita uudelleen.",
        "he": "Lo nitan le'abed et hatamuna. Nase shuvit.",
        "hi": "Chitra process nahi ho saka. Kripya dobara koshish karein.",
        "id": "Gagal memproses gambar. Silakan coba lagi.",
        "az": "Sekil emal edilemedi. Zehmet olmasa yeniden cenid edin.",
        "kk": "Suretti ondeu mumkin bolmady. Qayta korinh.",
        "uz": "Rasmni qayta ishlash imkoni bolmadi. Iltimos qayta urining.",
        "ka": "Gamosaxulebis damuSaveba ver moxerkhda. Gtxovt scadot tkvidam.",
        "hy": "Nerkariti makabutyune cherec. Khndrume noric paymanaven.",
        "mn": "Zurgiig bolomjit bish. Dahin oroldon uu.",
        "bg": "Izobrazhenieto ne mozhe da bade obraboteno. Opitaite otnovo.",
        "hr": "Obrada slike nije uspjela. Pokusajte ponovo.",
        "sr": "Obrada slike nije uspela. Pokusajte ponovo.",
        "cs": "Obrazek nelze zpracovat. Zkuste to znovu.",
        "sk": "Obraz sa nepodarilo spracovat. Skuste znova.",
        "ro": "Nu s-a putut procesa imaginea. Incercati din nou.",
        "hu": "A kep feldolgozasa sikertelen. Kerem problja ujra.",
        "th": "Mai samart pramoet rup phap. Karunalong mai khrang.",
        "vi": "Khong xu ly duoc anh. Vui long thu lai.",
        "ms": "Gagal memproses imej. Sila cuba lagi.",
        "bn": "Chhobi process kora jay ni. Anugraha kore abar chesta korun.",
        "ur": "Tasveer process nahi ho saki. Meherbani karke dobara koshish karein.",
    },

    # ── weather labels ────────────────────────────────────────────────────────
    "weather_feels_like": {
        "en": "feels like", "ru": "ощущается как", "de": "gefühlt",
        "fr": "ressenti", "es": "sensacion", "pt": "sensacao",
        "it": "percepito", "tr": "hissedilen", "ar": "yahiss",
        "zh": "体感", "ja": "体感", "ko": "체감",
        "pl": "odczuwalnie", "uk": "vidchuvaietsia", "fa": "hess mishavad",
        "nl": "voelt als", "sv": "kanslas som", "no": "kjennes som",
        "da": "foles som", "fi": "tuntuu kuin",
        "hi": "feels like", "id": "terasa", "az": "hiss olunur",
        "kk": "seziledi", "uz": "seziladi", "ka": "feels like",
        "hy": "zganvum e", "mn": "medremj",
        "bg": "useshta se", "hr": "osjecaj", "sr": "osecaj",
        "he": "murgash ke", "vi": "cam giac", "th": "ruusuk",
        "ms": "terasa", "bn": "anubhav",
    },
    "weather_humidity": {
        "en": "Humidity", "ru": "Влажность", "de": "Luftfeuchtigkeit",
        "fr": "Humidite", "es": "Humedad", "pt": "Umidade",
        "it": "Umidita", "tr": "Nem", "ar": "Rutuba",
        "zh": "湿度", "ja": "湿度", "ko": "습도",
        "pl": "Wilgotnosc", "uk": "Vologysnist", "fa": "Rotubat",
        "nl": "Vochtigheid", "sv": "Luftfuktighet", "no": "Luftfuktighet",
        "da": "Luftfugtighed", "fi": "Kosteus",
        "hi": "Humidity", "id": "Kelembaban", "az": "Rutubet",
        "kk": "Ylgaldylyk", "uz": "Namlik", "ka": "Humidity",
        "hy": "Khartsrakhohunk", "mn": "Chiglelt",
        "bg": "Vlaga", "hr": "Vlaznost", "sr": "Vlaznost",
        "he": "Lachut", "vi": "Do am", "th": "Khwam chuen",
        "ms": "Kelembapan", "bn": "Aardrata",
    },
    "weather_wind": {
        "en": "Wind", "ru": "Ветер", "de": "Wind",
        "fr": "Vent", "es": "Viento", "pt": "Vento",
        "it": "Vento", "tr": "Ruzgar", "ar": "Riyah",
        "zh": "风速", "ja": "風速", "ko": "바람",
        "pl": "Wiatr", "uk": "Viter", "fa": "Bad",
        "nl": "Wind", "sv": "Vind", "no": "Vind",
        "da": "Vind", "fi": "Tuuli",
        "hi": "Wind", "id": "Angin", "az": "Kulek",
        "kk": "Zhel", "uz": "Shamol", "ka": "Wind",
        "hy": "Karavark", "mn": "Salkhi",
        "bg": "Vyatur", "hr": "Vjetar", "sr": "Vetar",
        "he": "Ruakh", "vi": "Gio", "th": "Lom",
        "ms": "Angin", "bn": "Batash",
    },

    # ── balance ───────────────────────────────────────────────────────────────
    "insufficient_balance": {
        "en": (
            "Insufficient balance.\n\n"
            "To continue, please top up your account via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "After sending, your balance will be updated automatically."
        ),
        "ru": (
            "Недостаточно средств.\n\n"
            "Для продолжения пополните счёт через TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "После перевода баланс обновится автоматически."
        ),
        "de": (
            "Unzureichendes Guthaben.\n\n"
            "Bitte lade dein Konto ueber TON auf:\n"
            f"`{_TON_WALLET}`\n\n"
            "Nach der Ueberweisung wird dein Guthaben automatisch aktualisiert."
        ),
        "fr": (
            "Solde insuffisant.\n\n"
            "Veuillez recharger votre compte via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Apres le virement, votre solde sera mis a jour automatiquement."
        ),
        "es": (
            "Saldo insuficiente.\n\n"
            "Por favor recarga tu cuenta via TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Tras el envio, tu saldo se actualizara automaticamente."
        ),
        "uk": (
            "Nedostatno koshtiv.\n\n"
            "Popovnit rakhunok cherez TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Pislia perekazu balans onovytsia avtomatychno."
        ),
        "tr": (
            "Yetersiz bakiye.\n\n"
            "Lutfen TON araciligiyla hesabinizi doldurun:\n"
            f"`{_TON_WALLET}`\n\n"
            "Gonderdikten sonra bakiyeniz otomatik olarak guncellenecektir."
        ),
        "ar": (
            "Rasid ghair kafi.\n\n"
            "Yurja shahn hisabak abr TON:\n"
            f"`{_TON_WALLET}`\n\n"
            "Ba'd al-irsal sayatim tahdith rasiidak taqai'yan."
        ),
        "zh": (
            "余额不足。\n\n"
            f"请通过 TON 充值：`{_TON_WALLET}`\n\n"
            "转账后余额将自动更新。"
        ),
        "ja": (
            "残高不足です。\n\n"
            f"TON でチャージしてください：`{_TON_WALLET}`\n\n"
            "送金後、残高は自動的に更新されます。"
        ),
        "ko": (
            "잔액이 부족합니다.\n\n"
            f"TON으로 충전하세요: `{_TON_WALLET}`\n\n"
            "전송 후 잔액이 자동으로 업데이트됩니다."
        ),
        "pl": (
            "Niewystarczajace srodki.\n\n"
            f"Doladuj konto przez TON: `{_TON_WALLET}`\n\n"
            "Po przelewie saldo zostanie automatycznie zaktualizowane."
        ),
        "fa": (
            "Mojudi kafi nist.\n\n"
            f"Lotfan hesab khod ra az tarigh TON sharzh konid: `{_TON_WALLET}`\n\n"
            "Pas az ersal, mojudi shoma be surat khodkar be ruz mi shavad."
        ),
    },
    "balance_display": {
        "en": "Balance: ${amount}", "ru": "Баланс: ${amount}",
        "de": "Guthaben: ${amount}", "fr": "Solde: ${amount}",
        "es": "Saldo: ${amount}", "pt": "Saldo: ${amount}",
        "it": "Saldo: ${amount}", "tr": "Bakiye: ${amount}",
        "ar": "Al-Rasid: ${amount}", "zh": "余额：${amount}",
        "ja": "残高：${amount}", "ko": "잔액: ${amount}",
        "pl": "Saldo: ${amount}", "uk": "Balans: ${amount}",
        "fa": "Mojudi: ${amount}", "ka": "Balansi: ${amount}",
        "hy": "Mnatsord: ${amount}", "mn": "Uldegdel: ${amount}",
    },

    # ── errors & system ───────────────────────────────────────────────────────
    "no_response": {
        "en": "No response received. Please try again.",
        "ru": "Не удалось получить ответ. Попробуйте ещё раз.",
        "de": "Keine Antwort erhalten. Bitte versuche es erneut.",
        "fr": "Aucune reponse recue. Veuillez reessayer.",
        "es": "No se recibio respuesta. Por favor intenta de nuevo.",
        "pt": "Nenhuma resposta recebida. Por favor tente novamente.",
        "it": "Nessuna risposta ricevuta. Per favore riprova.",
        "tr": "Yanit alinamadi. Lutfen tekrar deneyin.",
        "ar": "Lam yatim talaqqi ayyi radd. Yurja al-muhawala mujaddadan.",
        "zh": "未收到回复。请重试。",
        "ja": "返答がありませんでした。もう一度お試しください。",
        "ko": "응답을 받지 못했습니다. 다시 시도해 주세요.",
        "pl": "Nie otrzymano odpowiedzi. Prosze sprobowac ponownie.",
        "uk": "Ne vdalosia otrymaty vidpovid. Sprobuite shche raz.",
        "fa": "Paskhi daryaft nashod. Lotfan dobare emtehan konid.",
        "nl": "Geen antwoord ontvangen. Probeer het opnieuw.",
        "sv": "Inget svar mottaget. Forsok igen.",
        "no": "Ingen respons mottatt. Vennligst prov igjen.",
        "da": "Intet svar modtaget. Prov venligst igen.",
        "fi": "Vastausta ei saatu. Yrita uudelleen.",
        "he": "Lo התקבלה teguva. Ana nase shuvit.",
        "hi": "Koi pratikriya nahi mili. Kripya punah prayaas karein.",
        "id": "Tidak ada respons. Silakan coba lagi.",
        "az": "Cavab alinmadi. Zehmet olmasa yeniden cehd edin.",
        "kk": "Zhouap alinbady. Qayta korinh.",
        "uz": "Javob olinmadi. Iltimos qayta urining.",
        "ka": "Pasukhi ar miigebula. Gtxovt scadot.",
        "hy": "Pataskh chi stacvel. Khndrume noric paymanaven.",
        "mn": "Khariun irsen gui. Dakhin oroldon uu.",
    },
    "default_deny": {
        "en": "I couldn't process that request. Please rephrase or try again.",
        "ru": "Не удалось обработать запрос. Попробуйте переформулировать.",
        "de": "Die Anfrage konnte nicht verarbeitet werden. Bitte umformulieren.",
        "fr": "Impossible de traiter la demande. Veuillez reformuler.",
        "es": "No pude procesar esa solicitud. Por favor reformula.",
        "pt": "Nao consegui processar esse pedido. Por favor reformule.",
        "it": "Non riesco a elaborare la richiesta. Per favore riformula.",
        "tr": "Istek islenemedi. Lutfen yeniden ifade edin.",
        "ar": "Ta'adhdhara mu'aalajat al-talab. Hawil i'aadat as-siyagha.",
        "zh": "无法处理该请求。请换种说法再试。",
        "ja": "リクエストを処理できませんでした。言い方を変えてお試しください。",
        "ko": "요청을 처리할 수 없었습니다. 다르게 표현해 보세요.",
        "pl": "Nie moglem przetworzyc tego zadania. Prosze przeformulowac.",
        "uk": "Ne vdalosia obrob. zapyt. Sprobuite pereformuliyuvaty.",
        "fa": "In darkkhast ghabele pardazesh nist. Lotfan dobare bayan konid.",
        "nl": "Kon dat verzoek niet verwerken. Probeer anders te formuleren.",
        "sv": "Kunde inte behandla den begaran. Forsok omformulera.",
        "no": "Kunne ikke behandle den foresporsel. Prov a omformulere.",
        "da": "Kunne ikke behandle den forespoergsel. Prov at omformulere.",
        "fi": "Pyyntoa ei voitu kasitella. Yrita muotoilla uudelleen.",
        "he": "Lo nitan le'abed et habakasha. Nase lenasukh mחדש.",
        "hi": "Is anurodh ko process nahi kiya ja saka. Kripya dobara likhein.",
        "id": "Tidak dapat memproses permintaan itu. Coba ungkapkan kembali.",
        "az": "Bu sorgu islene bilmedi. Zehmet olmasa yeniden ifade edin.",
        "kk": "Suranysty ondeu mumkin bolmady. Qayta tuzjyrymdag koriniz.",
        "uz": "Bu so'rovni qayta ishlash imkoni bolmadi. Iltimos qayta ifodalang.",
        "ka": "Motkhovna damusaveba ver moxerkhda. Gtxovt skhvagvarad chamoayalibot.",
        "hy": "Hartsumi makabutyune cherec. Khndrume verazanakakerpit.",
        "mn": "Khuseltiyg bolomjit bish. Ogoor nayrullana uu.",
    },
    "safety_block": {
        "en": "That request goes against my guidelines. Please try something else.",
        "ru": "Этот запрос нарушает мои правила. Попробуйте другое.",
        "de": "Diese Anfrage verstoesst gegen meine Richtlinien. Bitte anderes versuchen.",
        "fr": "Cette demande enfreint mes directives. Essayez autre chose.",
        "es": "Esa solicitud va contra mis pautas. Por favor intenta otra cosa.",
        "pt": "Esse pedido vai contra as minhas diretrizes. Por favor tente outra coisa.",
        "it": "Questa richiesta va contro le mie linee guida. Prova qualcos'altro.",
        "tr": "Bu istek kurallarina aykirii. Lutfen baska bir sey deneyin.",
        "ar": "Hadha al-talab yukhalif qawa'idi. Yurja tajarrub shai' akhar.",
        "zh": "该请求违反了我的准则。请尝试其他内容。",
        "ja": "そのリクエストはガイドラインに違反しています。他のことをお試しください。",
        "ko": "해당 요청은 내 지침에 위배됩니다. 다른 것을 시도해 보세요.",
        "pl": "To zadanie narusza moje wytyczne. Prosze sprobowac czegos innego.",
        "uk": "Tsei zapyt porushuie moi pravyla. Sprobuite shchos inshe.",
        "fa": "In darkkhast ba dastoral'amaliha-ye man mughayerat darad. Chize dige-i emtehan konid.",
        "nl": "Dat verzoek gaat in tegen mijn richtlijnen. Probeer iets anders.",
        "sv": "Den begaran strider mot mina riktlinjer. Forsok med nagot annat.",
        "no": "Den forespoerselen er mot retningslinjene mine. Prov noe annet.",
        "da": "Den forespoergsel er imod mine retningslinjer. Prov noget andet.",
        "fi": "Pynto rikkoo ohjeistustani. Kokeile jotain muuta.",
        "he": "Habakasha hazot meferet et hahanakhot sheli. Ana nase mashehu akher.",
        "hi": "Vah anurodh mere disha-nirdeshon ke viruddh hai. Kripya kuch aur azmaen.",
        "id": "Permintaan itu bertentangan dengan pedoman saya. Silakan coba yang lain.",
        "az": "Bu sorgu qaydalarina ziddir. Zehmet olmasa baska sey sinayin.",
        "kk": "Bul suranys erezhelerymdi buzydy. Baska nerse synap korini.",
        "uz": "Bu so'rov qoidalarimga zid. Iltimos boshqa narsa sinab koring.",
        "ka": "Es motkhovna chemi wesebis sapirispirod aris. Gtxovt skhva ram scadot.",
        "hy": "Ays hartsume hakasum em imy kanonerun. Khndrume paymanaven ayl ban.",
        "mn": "Ene khuselt minii düremjiyg zurchij baina. Oor zuil turshina uu.",
    },
    "rate_limited": {
        "en": "You're sending messages too fast. Please wait a moment.",
        "ru": "Вы отправляете сообщения слишком быстро. Подождите немного.",
        "de": "Du sendest Nachrichten zu schnell. Bitte kurz warten.",
        "fr": "Vous envoyez des messages trop vite. Patientez un instant.",
        "es": "Estas enviando mensajes demasiado rapido. Espera un momento.",
        "pt": "Esta enviando mensagens rapido demais. Por favor aguarde.",
        "it": "Stai inviando messaggi troppo velocemente. Aspetta un momento.",
        "tr": "Cok hizli mesaj gonderiyor sunuz. Lutfen biraz bekleyin.",
        "ar": "Anta tursil rasa'il bisur'a kabira. Yurja al-intizar lihzha.",
        "zh": "您发送消息太快了。请稍等片刻。",
        "ja": "メッセージの送信が速すぎます。少々お待ちください。",
        "ko": "메시지를 너무 빨리 보내고 있습니다. 잠시 기다려 주세요.",
        "pl": "Wysylasz wiadomosci zbyt szybko. Poczekaj chwile.",
        "uk": "Vy nadsilaete povidomlennia zanyidko shvydko. Zachekate khvylynu.",
        "fa": "Payam ha ra kheili sari'a ersal mi konid. Lotfan kami sabr konid.",
        "nl": "U stuurt berichten te snel. Even wachten alstublieft.",
        "sv": "Du skickar meddelanden for snabbt. Vanta lite.",
        "no": "Du sender meldinger for raskt. Vent litt.",
        "da": "Du sender beskeder for hurtigt. Vent venligst lidt.",
        "fi": "Lahetat viesteja liian nopeasti. Odota hetki.",
        "he": "Ata sholeakh haodot mahir midai. Ana hamten rega.",
        "hi": "Aap bahut tezi se sandesh bhej rahe hain. Kripya thoda ruken.",
        "id": "Anda mengirim pesan terlalu cepat. Harap tunggu sebentar.",
        "az": "Siz mesajlari cox suretli gonderirsiniz. Zehmet olmasa bir az gozleyin.",
        "kk": "Siz khabarlardy tym zhyldym zhiberip zhatyrsynyz. Biraq kute turinyz.",
        "uz": "Xabarlarni juda tez yuboryapsiz. Iltimos bir oz kuting.",
        "ka": "Tkven dzalian swraphad agzavnit shetyobinebebs. Gtxovt daicadet.",
        "hy": "Duk shat aragi ek ugharkadum haghordagrutynner. Khndrume spasek.",
        "mn": "Ta khet khurdan message ilgeej baina. Tur khuleinee.",
    },
    "truncation_suffix": {
        "en": "\n\n_response truncated_", "ru": "\n\n_ответ сокращён_",
        "de": "\n\n_Antwort gekurzt_", "fr": "\n\n_reponse tronquee_",
        "es": "\n\n_respuesta truncada_", "pt": "\n\n_resposta truncada_",
        "it": "\n\n_risposta troncata_", "tr": "\n\n_yanit kisaltildi_",
        "ar": "\n\n_tamma iqtiSaS al-radd_", "zh": "\n\n_回复已截断_",
        "ja": "\n\n_返答が省略されました_", "ko": "\n\n_응답이 잘렸습니다_",
        "pl": "\n\n_odpowiedz skrocona_", "uk": "\n\n_vidpovid skorocheno_",
        "fa": "\n\n_pasokh kutah shod_", "nl": "\n\n_antwoord afgekapt_",
        "sv": "\n\n_svar avkortat_", "no": "\n\n_svar avkortet_",
        "da": "\n\n_svar afkortet_", "fi": "\n\n_vastaus katkaistu_",
        "he": "\n\n_hateguva kutzra_", "hi": "\n\n_pratikriya kati gayi_",
        "id": "\n\n_respons dipotong_", "az": "\n\n_cavab qisaldildi_",
        "kk": "\n\n_zhouap qysqartyldy_", "uz": "\n\n_javob qisqartirildi_",
        "ka": "\n\n_pasukhi shekvetsiliya_", "hy": "\n\n_pataskhe krchatatvad e_",
        "mn": "\n\n_khariun taslagdsan_",
    },
    "no_grounded_data": {
        "en": "I couldn't find reliable information to answer this. Please provide more context or try a different question.",
        "ru": "Не удалось найти достоверную информацию для ответа. Уточните запрос или попробуйте другой вопрос.",
        "de": "Ich konnte keine zuverlaessigen Informationen finden. Bitte praezisiere deine Frage.",
        "fr": "Je n'ai pas trouve d'informations fiables. Veuillez preciser votre question.",
        "es": "No encontre informacion confiable para responder. Por favor aclara tu pregunta.",
        "pt": "Nao encontrei informacoes confiaveis. Por favor, reformule sua pergunta.",
        "it": "Non ho trovato informazioni affidabili. Per favore chiarisci la domanda.",
        "tr": "Guvenilir bilgi bulunamadi. Lutfen sorunuzu netlestirin.",
        "ar": "Lam atamakkan min al-'uthur 'ala ma'lumat mawthuga. Yurja tawdih su'alak.",
        "zh": "未找到可靠信息来回答此问题。请提供更多背景或换一个问题。",
        "ja": "信頼できる情報が見つかりませんでした。質問を明確にしてみてください。",
        "ko": "신뢰할 수 있는 정보를 찾지 못했습니다. 질문을 구체화해 주세요。",
        "pl": "Nie znalazlem wiarygodnych informacji. Prosze doprecyzowac pytanie.",
        "uk": "Ne vdalosia znajty dostovirnu informaciyu. Utochnit zapyt.",
        "fa": "Etelaat ghabele e'timadi yaft nashod. Lotfan sual khod ra daqiq tar bayan konid.",
        "nl": "Geen betrouwbare informatie gevonden. Probeer uw vraag te verduidelijken.",
        "sv": "Hittade ingen tillforlitlig information. Forsok fortydliga din fraga.",
        "no": "Fant ingen palitelig informasjon. Prov a presisere sporsmaalet.",
        "da": "Fandt ingen palidelig information. Prov at praecisere spoergsmaalet.",
        "fi": "Luotettavia tietoja ei loydy. Yrita tarkentaa kysymystasi.",
        "he": "Lo nimtsa meida aman. Ana nasekh et hashela bevehirut raba yoter.",
        "hi": "Vishwasniy jaankari nahi mili. Kripya apna prashn spasht karein.",
        "id": "Tidak ditemukan informasi yang dapat dipercaya. Coba perjelas pertanyaan Anda.",
        "az": "Etibarly melumat tapilmadi. Zehmet olmasa sualinizi deqiqlesdirin.",
        "kk": "Senimdi aqparat tabylmady. Suranysty naqqtylap koriniz.",
        "uz": "Ishonchli malumot topilmadi. Iltimos savolingizni aniqlashtiring.",
        "ka": "Sando informacia ver moidzebna. Gtxovt daazustet kitkhva.",
        "hy": "Husali teghekutyun chi gtnvel. Khndrume hstaketsnet hartsume.",
        "mn": "Naydvartai medeelel oldsongui. Asuultaa toduruulna uu.",
    },
    "cancelled": {
        "en": "Cancelled.", "ru": "Отменено.", "de": "Abgebrochen.",
        "fr": "Annule.", "es": "Cancelado.", "pt": "Cancelado.",
        "it": "Annullato.", "tr": "Iptal edildi.", "ar": "Tamma al-ilgha'.",
        "zh": "已取消。", "ja": "キャンセルしました。", "ko": "취소됨.",
        "pl": "Anulowano.", "uk": "Skasoano.", "fa": "Laghv shod.",
        "ka": "Gaukmebuliya.", "hy": "Chegharkavad e.", "mn": "Tsutslагдсан.",
    },

    # ── help text ─────────────────────────────────────────────────────────────
    "help_display": {
        "en": (
            "I'm your AI assistant. You can:\n"
            "Ask me anything\n"
            "Request code, analysis, or creative writing\n"
            "Send photos or screenshots for analysis\n"
            "Ask for weather or web searches\n"
            "Check your balance with /balance\n\n"
            "I reply in your language automatically."
        ),
        "ru": (
            "Я ваш ИИ-ассистент. Вы можете:\n"
            "Задать любой вопрос\n"
            "Попросить код, анализ или текст\n"
            "Прислать фото или скриншот для анализа\n"
            "Узнать погоду или сделать поиск\n"
            "Проверить баланс через /balance\n\n"
            "Я отвечаю на вашем языке автоматически."
        ),
        "de": (
            "Ich bin dein KI-Assistent. Du kannst:\n"
            "Alles fragen\n"
            "Code, Analysen oder kreative Texte anfordern\n"
            "Fotos oder Screenshots zur Analyse senden\n"
            "Wetter oder Websuche anfragen\n"
            "Mit /balance dein Guthaben pruefen\n\n"
            "Ich antworte automatisch in deiner Sprache."
        ),
        "fr": (
            "Je suis votre assistant IA. Vous pouvez:\n"
            "Poser n'importe quelle question\n"
            "Demander du code, une analyse ou un texte creatif\n"
            "Envoyer des photos ou captures d'ecran pour analyse\n"
            "Demander la meteo ou une recherche web\n"
            "Verifier votre solde avec /balance\n\n"
            "Je reponds automatiquement dans votre langue."
        ),
        "es": (
            "Soy tu asistente de IA. Puedes:\n"
            "Preguntar lo que quieras\n"
            "Pedir codigo, analisis o escritura creativa\n"
            "Enviar fotos o capturas de pantalla para analisis\n"
            "Consultar el clima o buscar en la web\n"
            "Ver tu saldo con /balance\n\n"
            "Respondo automaticamente en tu idioma."
        ),
        "ar": (
            "Ana musa'iduk al-dhaki. Yumkinuk:\n"
            "Su'al 'an ayy shay'\n"
            "Talab kod aw tahlil aw kitaba ibda'iya\n"
            "Irsal suwar aw laqatat shasha lil-tahlil\n"
            "Al-istifsar 'an al-taqs aw al-bahth 'ala al-web\n"
            "Al-taqaqqug min rasiidak bi /balance\n\n"
            "Arud taqai'yan bilughatak."
        ),
        "zh": (
            "我是您的AI助手。您可以：\n"
            "问我任何问题\n"
            "请求代码、分析或创意写作\n"
            "发送照片或截图进行分析\n"
            "查询天气或搜索网页\n"
            "用 /balance 查看余额\n\n"
            "我会自动用您的语言回复。"
        ),
        "ka": (
            "Me var tkhhveni AI asistenti. Shegidzliat:\n"
            "Damisvaht nebismieri kitkhva\n"
            "Moitkhavot kodi, analizi an shemoqmedebiti cera\n"
            "Gagzavnot foto an ekranis surathebi analizistvis\n"
            "Hkitkhot aminidi an veb dzieba\n"
            "Sheamowmot balansi /balance-it\n\n"
            "Avtomarurad vpasukhobt tkhhvens enaze."
        ),
    },

    # ── silent (no reply needed) ──────────────────────────────────────────────
    "empty_message": {"_silent": "true"},
    "no_user_id":    {"_silent": "true"},
}

_SILENT_KEYS: frozenset[str] = frozenset({"empty_message", "no_user_id"})


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def t(key: str, lang: str, **kwargs: str) -> str:
    if key in _SILENT_KEYS:
        return ""
    bucket = _STRINGS.get(key, {})
    text = bucket.get(lang) or bucket.get("en", "")
    for k, v in kwargs.items():
        text = text.replace(f"${{{k}}}", v)
    return text


def lang_instruction(lang: str) -> str:
    return LANG_INSTRUCTIONS.get(lang, "Reply in the same language the user wrote in.")


def ow_lang(lang: str) -> str:
    return OW_LANG_MAP.get(lang, "en")


def is_supported(lang: str) -> bool:
    return lang in SUPPORTED_LANGS


def normalize_lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"