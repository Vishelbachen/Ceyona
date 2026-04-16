import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from handler import router

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(
    token=BOT_TOKEN,
    parse_mode=ParseMode.HTML
)

dp = Dispatcher()

dp.include_router(router)