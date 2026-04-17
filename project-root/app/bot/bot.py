from fastapi import APIRouter, Request
from aiogram import Bot, Dispatcher, types
import os

from app.engine.agent import Agent

router = APIRouter()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

agent = None


@router.on_event("startup")
async def startup():
    global agent

    from app.engine.planner import Planner
    from app.engine.router import Router
    from app.engine.formatter import Formatter
    from app.engine.llm import LLMEngine
    from app.engine.memory.service import MemoryService

    agent = Agent(
        planner=Planner(),
        router=Router(),
        formatter=Formatter(),
        llm=LLMEngine(),
        memory=MemoryService()
    )


@router.post("/webhook")
async def webhook(req: Request):

    data = await req.json()
    update = types.Update(**data)

    message = update.message.text
    user_id = str(update.message.from_user.id)

    result = await agent.run(message, user_id=user_id)

    await bot.send_message(user_id, result)

    return {"ok": True}