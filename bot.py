import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from handler import handle_message
from config.settings import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()