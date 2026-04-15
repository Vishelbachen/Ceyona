import os
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes
)

from handler import handle_message

logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        user_id = update.effective_user.id

        response = await asyncio.wait_for(
            handle_message(user_id, text),
            timeout=45
        )

        await update.message.reply_text(response or "No response")

    except Exception as e:
        logger.exception(e)


def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    async def post_init(app):
        await app.bot.delete_webhook(drop_pending_updates=True)

        if settings.WEBHOOK_URL:
            await app.bot.set_webhook(
                url=settings.WEBHOOK_URL + "/webhook",
                drop_pending_updates=True
            )

    app.post_init = post_init

    # 🔥 PTB 21 SAFE WAY
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )