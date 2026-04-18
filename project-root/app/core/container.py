import os

from aiogram import Bot, Dispatcher

from app.engine.llm import LLM
from app.engine.agent import Agent
from app.memory.supabase_client import SupabaseClient
from app.tools.tool_router import ToolRouter
from app.bot.handlers import Handlers


class Container:
    def __init__(self):
        self.bot = Bot(token=os.getenv("BOT_TOKEN"))
        self.dp = Dispatcher()

        self.llm = LLM()
        self.memory = SupabaseClient()
        self.tools = ToolRouter()

        self.agent = Agent(
            llm=self.llm,
            memory=self.memory,
            tool_router=self.tools
        )

        self.handlers = Handlers(self.agent)

    def setup(self):
        self.dp.include_router(self.handlers.register())
        return self