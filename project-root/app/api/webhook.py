from fastapi import APIRouter, Request
from aiogram import Bot, Dispatcher
from app.bot.handlers import Handlers
from app.engine.agent import Agent
from app.engine.llm import LLM
from app.memory.supabase_client import SupabaseClient
from app.tools.tool_router import ToolRouter

import os


router = APIRouter()


bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


llm = LLM()
memory = SupabaseClient()
tools = ToolRouter()

agent = Agent(
    llm=llm,
    memory=memory,
    tool_router=tools
)

handlers = Handlers(agent)
dp.include_router(handlers.register())


@router.post("/webhook")
async def telegram_webhook(request: Request):
    update = await request.json()

    from aiogram.types import Update

    tg_update = Update.model_validate(update)

    await dp.feed_update(bot, tg_update)

    return {"ok": True}