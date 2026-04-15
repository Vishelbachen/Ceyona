from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters
)

from handler import handle_message


async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text

    response = await handle_message(user_id, text)

    await update.message.reply_text(response)


async def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_entry)
    )

    await app.initialize()
    await app.start()

    # Railway-compatible polling
    await app.updater.start_polling()

    await app.updater.idle()