import logging

logger = logging.getLogger(__name__)

_COMMANDS = {"/start", "/help", "/balance", "/clear"}


def is_command(text: str) -> bool:
    return text.startswith("/")


def extract_command(text: str) -> tuple[str, str]:
    """Returns (command, payload). E.g. '/start hello' → ('/start', 'hello')"""
    parts = text.strip().split(None, 1)
    cmd = parts[0].lower()
    payload = parts[1] if len(parts) > 1 else ""
    return cmd, payload


_START_MESSAGES: dict[str, str] = {
    "en": (
        "👋 *Welcome!*\n\n"
        "I'm your AI assistant. Just send me any message and I'll help you.\n\n"
        "*/help* — available commands\n"
        "*/balance* — check your balance\n"
        "*/clear* — clear conversation history"
    ),
    "ru": (
        "👋 *Добро пожаловать!*\n\n"
        "Я ваш ИИ-ассистент. Просто напишите мне — и я помогу.\n\n"
        "*/help* — доступные команды\n"
        "*/balance* — проверить баланс\n"
        "*/clear* — очистить историю"
    ),
    "de": (
        "👋 *Willkommen!*\n\n"
        "Ich bin Ihr KI-Assistent. Schreiben Sie einfach eine Nachricht.\n\n"
        "*/help* — verfügbare Befehle\n"
        "*/balance* — Guthaben prüfen\n"
        "*/clear* — Verlauf löschen"
    ),
    "fr": (
        "👋 *Bienvenue !*\n\n"
        "Je suis votre assistant IA. Envoyez-moi un message.\n\n"
        "*/help* — commandes disponibles\n"
        "*/balance* — vérifier le solde\n"
        "*/clear* — effacer l'historique"
    ),
    "es": (
        "👋 *¡Bienvenido!*\n\n"
        "Soy tu asistente de IA. Solo escríbeme.\n\n"
        "*/help* — comandos disponibles\n"
        "*/balance* — ver saldo\n"
        "*/clear* — borrar historial"
    ),
    "pt": (
        "👋 *Bem-vindo!*\n\n"
        "Sou seu assistente de IA. Só me mande uma mensagem.\n\n"
        "*/help* — comandos disponíveis\n"
        "*/balance* — verificar saldo\n"
        "*/clear* — limpar histórico"
    ),
    "it": (
        "👋 *Benvenuto!*\n\n"
        "Sono il tuo assistente IA. Scrivimi pure.\n\n"
        "*/help* — comandi disponibili\n"
        "*/balance* — controlla saldo\n"
        "*/clear* — cancella cronologia"
    ),
    "tr": (
        "👋 *Hoş geldiniz!*\n\n"
        "Ben yapay zeka asistanınızım. Bana yazın.\n\n"
        "*/help* — mevcut komutlar\n"
        "*/balance* — bakiye kontrolü\n"
        "*/clear* — geçmişi temizle"
    ),
    "ar": (
        "👋 *مرحباً!*\n\n"
        "أنا مساعدك الذكي. فقط أرسل لي رسالة.\n\n"
        "*/help* — الأوامر المتاحة\n"
        "*/balance* — التحقق من الرصيد\n"
        "*/clear* — مسح السجل"
    ),
    "zh": (
        "👋 *欢迎！*\n\n"
        "我是您的AI助手，直接发消息给我吧。\n\n"
        "*/help* — 可用命令\n"
        "*/balance* — 查看余额\n"
        "*/clear* — 清除对话历史"
    ),
    "ja": (
        "👋 *ようこそ！*\n\n"
        "AIアシスタントです。何でもメッセージを送ってください。\n\n"
        "*/help* — コマンド一覧\n"
        "*/balance* — 残高確認\n"
        "*/clear* — 履歴を削除"
    ),
    "ko": (
        "👋 *환영합니다!*\n\n"
        "AI 어시스턴트입니다. 메시지를 보내주세요.\n\n"
        "*/help* — 사용 가능한 명령어\n"
        "*/balance* — 잔액 확인\n"
        "*/clear* — 대화 기록 삭제"
    ),
    "pl": (
        "👋 *Witaj!*\n\n"
        "Jestem Twoim asystentem AI. Napisz do mnie.\n\n"
        "*/help* — dostępne komendy\n"
        "*/balance* — sprawdź saldo\n"
        "*/clear* — wyczyść historię"
    ),
    "uk": (
        "👋 *Ласкаво просимо!*\n\n"
        "Я ваш ШІ-асистент. Просто напишіть мені.\n\n"
        "*/help* — доступні команди\n"
        "*/balance* — перевірити баланс\n"
        "*/clear* — очистити історію"
    ),
    "fa": (
        "👋 *خوش آمدید!*\n\n"
        "من دستیار هوش مصنوعی شما هستم. فقط پیام بدهید.\n\n"
        "*/help* — دستورات موجود\n"
        "*/balance* — بررسی موجودی\n"
        "*/clear* — پاک کردن تاریخچه"
    ),
}

_HELP_MESSAGES: dict[str, str] = {
    "en": (
        "ℹ️ *Available commands:*\n\n"
        "*/start* — welcome message\n"
        "*/help* — this message\n"
        "*/balance* — your current balance\n"
        "*/clear* — clear conversation history\n\n"
        "Just send any message to chat with AI."
    ),
    "ru": (
        "ℹ️ *Доступные команды:*\n\n"
        "*/start* — приветствие\n"
        "*/help* — это сообщение\n"
        "*/balance* — ваш текущий баланс\n"
        "*/clear* — очистить историю диалога\n\n"
        "Просто напишите сообщение, чтобы общаться с ИИ."
    ),
    "de": (
        "ℹ️ *Verfügbare Befehle:*\n\n"
        "*/start* — Willkommensnachricht\n"
        "*/help* — diese Nachricht\n"
        "*/balance* — aktuelles Guthaben\n"
        "*/clear* — Verlauf löschen\n\n"
        "Schreib einfach eine Nachricht."
    ),
    "fr": (
        "ℹ️ *Commandes disponibles :*\n\n"
        "*/start* — message de bienvenue\n"
        "*/help* — ce message\n"
        "*/balance* — votre solde actuel\n"
        "*/clear* — effacer l'historique\n\n"
        "Envoyez simplement un message pour discuter avec l'IA."
    ),
    "es": (
        "ℹ️ *Comandos disponibles:*\n\n"
        "*/start* — mensaje de bienvenida\n"
        "*/help* — este mensaje\n"
        "*/balance* — tu saldo actual\n"
        "*/clear* — borrar historial\n\n"
        "Solo envía un mensaje para chatear con la IA."
    ),
    "pt": (
        "ℹ️ *Comandos disponíveis:*\n\n"
        "*/start* — mensagem de boas-vindas\n"
        "*/help* — esta mensagem\n"
        "*/balance* — seu saldo atual\n"
        "*/clear* — limpar histórico\n\n"
        "Envie qualquer mensagem para conversar com a IA."
    ),
    "it": (
        "ℹ️ *Comandi disponibili:*\n\n"
        "*/start* — messaggio di benvenuto\n"
        "*/help* — questo messaggio\n"
        "*/balance* — saldo attuale\n"
        "*/clear* — cancella cronologia\n\n"
        "Invia qualsiasi messaggio per chattare con l'IA."
    ),
    "tr": (
        "ℹ️ *Mevcut komutlar:*\n\n"
        "*/start* — karşılama mesajı\n"
        "*/help* — bu mesaj\n"
        "*/balance* — mevcut bakiye\n"
        "*/clear* — geçmişi temizle\n\n"
        "Yapay zeka ile sohbet için mesaj gönderin."
    ),
    "ar": (
        "ℹ️ *الأوامر المتاحة:*\n\n"
        "*/start* — رسالة ترحيب\n"
        "*/help* — هذه الرسالة\n"
        "*/balance* — رصيدك الحالي\n"
        "*/clear* — مسح السجل\n\n"
        "فقط أرسل رسالة للتحدث مع الذكاء الاصطناعي."
    ),
    "zh": (
        "ℹ️ *可用命令：*\n\n"
        "*/start* — 欢迎消息\n"
        "*/help* — 此消息\n"
        "*/balance* — 当前余额\n"
        "*/clear* — 清除对话历史\n\n"
        "直接发消息与AI对话。"
    ),
    "ja": (
        "ℹ️ *利用可能なコマンド：*\n\n"
        "*/start* — ウェルカムメッセージ\n"
        "*/help* — このメッセージ\n"
        "*/balance* — 現在の残高\n"
        "*/clear* — 履歴を削除\n\n"
        "メッセージを送るだけでAIと会話できます。"
    ),
    "ko": (
        "ℹ️ *사용 가능한 명령어:*\n\n"
        "*/start* — 환영 메시지\n"
        "*/help* — 이 메시지\n"
        "*/balance* — 현재 잔액\n"
        "*/clear* — 대화 기록 삭제\n\n"
        "AI와 대화하려면 메시지를 보내세요."
    ),
    "pl": (
        "ℹ️ *Dostępne komendy:*\n\n"
        "*/start* — wiadomość powitalna\n"
        "*/help* — ta wiadomość\n"
        "*/balance* — twoje saldo\n"
        "*/clear* — wyczyść historię\n\n"
        "Wyślij wiadomość, aby porozmawiać z AI."
    ),
    "uk": (
        "ℹ️ *Доступні команди:*\n\n"
        "*/start* — привітання\n"
        "*/help* — це повідомлення\n"
        "*/balance* — ваш поточний баланс\n"
        "*/clear* — очистити історію\n\n"
        "Просто напишіть повідомлення для спілкування з ШІ."
    ),
    "fa": (
        "ℹ️ *دستورات موجود:*\n\n"
        "*/start* — پیام خوش‌آمدگویی\n"
        "*/help* — این پیام\n"
        "*/balance* — موجودی فعلی\n"
        "*/clear* — پاک کردن تاریخچه\n\n"
        "برای صحبت با هوش مصنوعی فقط پیام بدهید."
    ),
}

_CLEAR_MESSAGES: dict[str, str] = {
    "en": "✅ Conversation history cleared.",
    "ru": "✅ История диалога очищена.",
    "de": "✅ Verlauf gelöscht.",
    "fr": "✅ Historique effacé.",
    "es": "✅ Historial borrado.",
    "pt": "✅ Histórico limpo.",
    "it": "✅ Cronologia cancellata.",
    "tr": "✅ Geçmiş temizlendi.",
    "ar": "✅ تم مسح السجل.",
    "zh": "✅ 对话历史已清除。",
    "ja": "✅ 会話履歴を削除しました。",
    "ko": "✅ 대화 기록이 삭제되었습니다.",
    "pl": "✅ Historia wyczyszczona.",
    "uk": "✅ Історію очищено.",
    "fa": "✅ تاریخچه پاک شد.",
}

_UNKNOWN_CMD_MESSAGES: dict[str, str] = {
    "en": "❓ Unknown command. Use */help* to see available commands.",
    "ru": "❓ Неизвестная команда. Используйте */help* для списка команд.",
    "de": "❓ Unbekannter Befehl. Nutze */help* für verfügbare Befehle.",
    "fr": "❓ Commande inconnue. Utilisez */help* pour voir les commandes.",
    "es": "❓ Comando desconocido. Usa */help* para ver los comandos.",
    "pt": "❓ Comando desconhecido. Use */help* para ver os comandos.",
    "it": "❓ Comando sconosciuto. Usa */help* per i comandi disponibili.",
    "tr": "❓ Bilinmeyen komut. Komutlar için */help* kullanın.",
    "ar": "❓ أمر غير معروف. استخدم */help* لرؤية الأوامر.",
    "zh": "❓ 未知命令，使用 */help* 查看可用命令。",
    "ja": "❓ 不明なコマンドです。*/help* で確認してください。",
    "ko": "❓ 알 수 없는 명령어입니다. */help*로 확인하세요.",
    "pl": "❓ Nieznana komenda. Użyj */help* aby zobaczyć komendy.",
    "uk": "❓ Невідома команда. Використайте */help* для перегляду команд.",
    "fa": "❓ دستور ناشناخته. از */help* برای دیدن دستورات استفاده کنید.",
}


def get_start_message(lang: str) -> str:
    return _START_MESSAGES.get(lang) or _START_MESSAGES["en"]


def get_help_message(lang: str) -> str:
    return _HELP_MESSAGES.get(lang) or _HELP_MESSAGES["en"]


def get_clear_message(lang: str) -> str:
    return _CLEAR_MESSAGES.get(lang) or _CLEAR_MESSAGES["en"]


def get_unknown_cmd_message(lang: str) -> str:
    return _UNKNOWN_CMD_MESSAGES.get(lang) or _UNKNOWN_CMD_MESSAGES["en"]